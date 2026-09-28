from flask import Blueprint, render_template, request, session, jsonify
from flask_login import login_required
from datetime import datetime

from app.models.case import Case
from app.models.timeline import TimelineEvent
from app.forensic.timeline_engine import TimelineEngine
from app.utils import api_response

timeline_bp = Blueprint("timeline", __name__)

@timeline_bp.route("/cases/<int:case_id>/timeline")
@login_required
def index(case_id: int):
    case = Case.query.get_or_404(case_id)
    session["active_case_id"] = case.id

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    sort_order = request.args.get("sort", "desc")
    browser = request.args.get("browser", "ALL")
    artifact_type = request.args.get("type", "ALL")
    domain = request.args.get("domain", "")
    keyword = request.args.get("q", "")
    start_str = request.args.get("start", "")
    end_str = request.args.get("end", "")

    start_date = None
    end_date = None
    if start_str:
        try:
            start_date = datetime.fromisoformat(start_str)
        except Exception:
            pass
    if end_str:
        try:
            end_date = datetime.fromisoformat(end_str)
        except Exception:
            pass

    timeline_data = TimelineEngine.query_timeline(
        case_id=case.id,
        page=page,
        per_page=per_page,
        sort_order=sort_order,
        browser=browser,
        artifact_type=artifact_type,
        domain=domain,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date
    )

    stats = TimelineEngine.get_timeline_stats(case.id)

    # Get distinct domains for autocomplete / filtering
    top_domains = [d[0] for d in db_get_distinct_domains(case.id)]

    return render_template(
        "timeline/index.html",
        case=case,
        timeline_data=timeline_data,
        stats=stats,
        filters={
            "sort": sort_order,
            "browser": browser,
            "type": artifact_type,
            "domain": domain,
            "q": keyword,
            "start": start_str,
            "end": end_str,
            "page": page,
            "per_page": per_page
        },
        top_domains=top_domains
    )

@timeline_bp.route("/timeline/event/<int:event_id>")
@login_required
def get_event(event_id: int):
    event = TimelineEvent.query.get_or_404(event_id)
    return api_response(success=True, data=event.to_dict())

def db_get_distinct_domains(case_id: int):
    from app.extensions import db
    from sqlalchemy import func
    return (
        db.session.query(TimelineEvent.domain)
        .filter(TimelineEvent.case_id == case_id, TimelineEvent.domain.isnot(None))
        .distinct()
        .limit(30)
        .all()
    )
