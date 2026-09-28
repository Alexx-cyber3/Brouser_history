from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import or_, and_

from app.models.timeline import TimelineEvent
from app.models.case import Case

class TimelineEngine:
    """
    Forensic Timeline Engine.
    Provides chronological ordering, multi-attribute filtering,
    density analysis, and server-side pagination across heterogeneous browser events.
    """

    @staticmethod
    def query_timeline(
        case_id: int,
        page: int = 1,
        per_page: int = 50,
        sort_order: str = "desc", # "asc" or "desc"
        browser: Optional[str] = None,
        artifact_type: Optional[str] = None,
        domain: Optional[str] = None,
        keyword: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Query timeline events with efficient indexed filters and server-side pagination.
        """
        query = TimelineEvent.query.filter_by(case_id=case_id)

        if browser and browser != "ALL":
            query = query.filter(TimelineEvent.browser == browser.upper())

        if artifact_type and artifact_type != "ALL":
            query = query.filter(TimelineEvent.artifact_type == artifact_type.upper())

        if domain:
            query = query.filter(TimelineEvent.domain.ilike(f"%{domain.strip()}%"))

        if keyword:
            kw = f"%{keyword.strip()}%"
            query = query.filter(
                or_(
                    TimelineEvent.title.ilike(kw),
                    TimelineEvent.url.ilike(kw),
                    TimelineEvent.domain.ilike(kw),
                    TimelineEvent.summary.ilike(kw)
                )
            )

        if start_date:
            query = query.filter(TimelineEvent.timestamp_utc >= start_date)

        if end_date:
            query = query.filter(TimelineEvent.timestamp_utc <= end_date)

        # Ordering
        if sort_order.lower() == "asc":
            query = query.order_by(TimelineEvent.timestamp_utc.asc())
        else:
            query = query.order_by(TimelineEvent.timestamp_utc.desc())

        # Pagination
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "total_items": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
            "events": [event.to_dict() for event in pagination.items]
        }

    @staticmethod
    def get_timeline_stats(case_id: int) -> Dict[str, Any]:
        """
        Compute timeline density, browser distribution, and date bounds.
        """
        events = TimelineEvent.query.filter_by(case_id=case_id).all()
        if not events:
            return {
                "total_events": 0,
                "first_event": None,
                "last_event": None,
                "browser_distribution": {},
                "artifact_distribution": {},
                "hourly_distribution": {f"{h:02d}": 0 for h in range(24)}
            }

        browser_counts: Dict[str, int] = {}
        artifact_counts: Dict[str, int] = {}
        hourly_counts: Dict[str, int] = {f"{h:02d}": 0 for h in range(24)}

        timestamps = []
        for e in events:
            b = e.browser or "UNKNOWN"
            browser_counts[b] = browser_counts.get(b, 0) + 1

            a = e.artifact_type or "OTHER"
            artifact_counts[a] = artifact_counts.get(a, 0) + 1

            if e.timestamp_utc:
                timestamps.append(e.timestamp_utc)
                hour_key = f"{e.timestamp_utc.hour:02d}"
                hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1

        timestamps.sort()

        return {
            "total_events": len(events),
            "first_event": timestamps[0].strftime("%Y-%m-%d %H:%M:%S UTC") if timestamps else None,
            "last_event": timestamps[-1].strftime("%Y-%m-%d %H:%M:%S UTC") if timestamps else None,
            "browser_distribution": browser_counts,
            "artifact_distribution": artifact_counts,
            "hourly_distribution": hourly_counts
        }
