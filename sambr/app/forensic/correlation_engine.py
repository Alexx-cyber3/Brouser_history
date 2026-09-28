from datetime import timedelta
from typing import List, Dict, Any
from collections import defaultdict
from app.models.timeline import TimelineEvent
from app.models.artifact import Artifact

class CorrelationEngine:
    """
    Cross-Source Forensic Evidence Correlation Engine.
    Discovers relationships across heterogeneous browsers and profiles without speculating causation.
    Employs objective forensic terminology ("Temporally correlated", "Associated activity").
    """

    @classmethod
    def analyze_case_correlations(cls, case_id: int) -> Dict[str, Any]:
        """
        Runs comprehensive cross-source correlation analysis on the case.
        Returns:
          - cross_browser_domains: Domains accessed across 2 or more different browsers
          - cross_browser_urls: Identical URLs accessed across multiple browsers
          - visit_download_sequences: Temporal correlation: website visit followed by download within 10 minutes
          - activity_bursts: High-frequency action clusters (>10 events within 60 seconds)
          - summary_metrics: Aggregate correlation metrics
        """
        events = (
            TimelineEvent.query.filter_by(case_id=case_id)
            .order_by(TimelineEvent.timestamp_utc.asc())
            .all()
        )

        if not events:
            return {
                "total_correlations": 0,
                "cross_browser_domains": [],
                "cross_browser_urls": [],
                "visit_download_sequences": [],
                "activity_bursts": []
            }

        cross_browser_domains = cls._correlate_cross_browser_domains(events)
        cross_browser_urls = cls._correlate_cross_browser_urls(events)
        visit_download_sequences = cls._correlate_visit_downloads(events)
        activity_bursts = cls._detect_activity_bursts(events)

        total_correlations = (
            len(cross_browser_domains)
            + len(cross_browser_urls)
            + len(visit_download_sequences)
            + len(activity_bursts)
        )

        return {
            "total_correlations": total_correlations,
            "cross_browser_domains": cross_browser_domains,
            "cross_browser_urls": cross_browser_urls,
            "visit_download_sequences": visit_download_sequences,
            "activity_bursts": activity_bursts
        }

    @staticmethod
    def _correlate_cross_browser_domains(events: List[TimelineEvent]) -> List[Dict[str, Any]]:
        domain_browsers = defaultdict(lambda: {"browsers": set(), "profiles": set(), "events": []})

        for e in events:
            if e.domain and len(e.domain) > 2:
                domain_browsers[e.domain]["browsers"].add(e.browser)
                domain_browsers[e.domain]["profiles"].add(f"{e.browser} ({e.profile})")
                if len(domain_browsers[e.domain]["events"]) < 10:
                    domain_browsers[e.domain]["events"].append({
                        "event_id": e.id,
                        "browser": e.browser,
                        "type": e.event_type,
                        "timestamp": e.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "title": e.title
                    })

        results = []
        for domain, data in domain_browsers.items():
            if len(data["browsers"]) > 1:
                results.append({
                    "domain": domain,
                    "browser_count": len(data["browsers"]),
                    "browsers": sorted(list(data["browsers"])),
                    "profiles": sorted(list(data["profiles"])),
                    "sample_events": data["events"],
                    "relationship_type": "Multi-Browser Domain Convergence",
                    "note": f"Domain '{domain}' was accessed across {len(data['browsers'])} distinct browser platforms."
                })

        results.sort(key=lambda x: x["browser_count"], reverse=True)
        return results

    @staticmethod
    def _correlate_cross_browser_urls(events: List[TimelineEvent]) -> List[Dict[str, Any]]:
        url_browsers = defaultdict(lambda: {"browsers": set(), "titles": set(), "events": []})

        for e in events:
            if e.url and len(e.url) > 8:
                url_browsers[e.url]["browsers"].add(e.browser)
                if e.title:
                    url_browsers[e.url]["titles"].add(e.title)
                if len(url_browsers[e.url]["events"]) < 6:
                    url_browsers[e.url]["events"].append({
                        "event_id": e.id,
                        "browser": e.browser,
                        "timestamp": e.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
                    })

        results = []
        for url, data in url_browsers.items():
            if len(data["browsers"]) > 1:
                results.append({
                    "url": url,
                    "browser_count": len(data["browsers"]),
                    "browsers": sorted(list(data["browsers"])),
                    "sample_titles": list(data["titles"])[:3],
                    "sample_events": data["events"],
                    "relationship_type": "Cross-Platform URL Access",
                    "note": "Exact identical URL navigated or recorded in multiple browser environments."
                })

        return results[:30]

    @staticmethod
    def _correlate_visit_downloads(events: List[TimelineEvent]) -> List[Dict[str, Any]]:
        """
        Identifies temporal sequence: Domain visit followed by download from same domain within 10 minutes.
        Uses objective terminology: 'Temporally correlated'.
        """
        sequences = []
        time_window = timedelta(minutes=10)

        # Separate visits and downloads
        downloads = [e for e in events if e.event_type == "DOWNLOAD"]
        visits = [e for e in events if e.event_type in ("VISIT", "SESSION_OPENED")]

        for dl in downloads:
            if not dl.domain:
                continue
            # Look for visits to same domain preceding download within window
            matching_visits = [
                v for v in visits
                if v.domain == dl.domain
                and (dl.timestamp_utc - time_window) <= v.timestamp_utc <= dl.timestamp_utc
            ]

            if matching_visits:
                closest_visit = max(matching_visits, key=lambda x: x.timestamp_utc)
                delta_sec = int((dl.timestamp_utc - closest_visit.timestamp_utc).total_seconds())

                sequences.append({
                    "domain": dl.domain,
                    "visit_event_id": closest_visit.id,
                    "visit_browser": closest_visit.browser,
                    "visit_timestamp": closest_visit.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "visit_title": closest_visit.title,
                    "download_event_id": dl.id,
                    "download_browser": dl.browser,
                    "download_timestamp": dl.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "download_title": dl.title,
                    "time_delta_seconds": delta_sec,
                    "relationship_type": "Temporally Correlated Visit-to-Download",
                    "evidentiary_note": (
                        f"Visit to '{closest_visit.title or dl.domain}' on {closest_visit.browser} was followed "
                        f"{delta_sec} seconds later by download '{dl.title}' on {dl.browser}."
                    )
                })

        return sequences[:50]

    @staticmethod
    def _detect_activity_bursts(events: List[TimelineEvent]) -> List[Dict[str, Any]]:
        """
        Detect activity bursts: periods where >= 10 events occur within 60 seconds.
        """
        bursts = []
        burst_threshold = 10
        window = timedelta(seconds=60)

        n = len(events)
        i = 0
        while i < n:
            start_ev = events[i]
            window_end = start_ev.timestamp_utc + window
            cluster = [start_ev]
            j = i + 1
            while j < n and events[j].timestamp_utc <= window_end:
                cluster.append(events[j])
                j += 1

            if len(cluster) >= burst_threshold:
                browsers = list({e.browser for e in cluster})
                bursts.append({
                    "start_time": start_ev.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "end_time": cluster[-1].timestamp_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "event_count": len(cluster),
                    "browsers_involved": browsers,
                    "sample_domains": list({e.domain for e in cluster if e.domain})[:5],
                    "relationship_type": "High-Frequency Activity Burst",
                    "evidentiary_note": f"Rapid sequence of {len(cluster)} events recorded across {len(browsers)} browser(s) within {int((cluster[-1].timestamp_utc - start_ev.timestamp_utc).total_seconds())}s."
                })
                i = j # Move pointer past this burst
            else:
                i += 1

        return bursts[:20]
