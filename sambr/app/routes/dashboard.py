from flask import Blueprint, render_template, session, redirect, url_for
from flask_login import login_required
from collections import defaultdict
from datetime import datetime

from app.models.case import Case
from app.models.evidence import EvidenceSource, EvidenceFile
from app.models.artifact import Artifact
from app.models.timeline import TimelineEvent
from app.forensic.timeline_engine import TimelineEngine
from app.forensic.correlation_engine import CorrelationEngine

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
@login_required
def index():
    total_cases = Case.query.count()
    active_case_id = session.get("active_case_id")

    active_case = None
    if active_case_id:
        active_case = Case.query.get(active_case_id)

    # Fallback to the latest case if none selected in session
    if not active_case and total_cases > 0:
        active_case = Case.query.order_by(Case.created_at.desc()).first()
        if active_case:
            session["active_case_id"] = active_case.id

    if not active_case:
        return render_template("dashboard/index.html", has_data=False, total_cases=0)

    # Calculate real case statistics
    sources = EvidenceSource.query.filter_by(case_id=active_case.id).all()
    evidence_files = EvidenceFile.query.filter_by(case_id=active_case.id).all()
    artifacts = Artifact.query.filter_by(case_id=active_case.id).all()
    timeline_events = TimelineEvent.query.filter_by(case_id=active_case.id).all()

    total_sources = len(sources)
    total_files = len(evidence_files)
    total_artifacts = len(artifacts)
    total_timeline = len(timeline_events)

    # Hashes verified count
    verified_hashes_count = sum(1 for f in evidence_files if f.verification_status == "INTEGRITY VERIFIED")
    mismatch_hashes_count = sum(1 for f in evidence_files if f.verification_status == "INTEGRITY MISMATCH")

    # Distinct browsers in active case
    browser_set = sorted(list({s.browser_type for s in sources}))

    # Chart 1: Artifacts by Browser
    artifacts_by_browser = defaultdict(int)
    for a in artifacts:
        artifacts_by_browser[a.browser] += 1

    # Chart 2: Artifacts by Type
    artifacts_by_type = defaultdict(int)
    for a in artifacts:
        artifacts_by_type[a.artifact_type] += 1

    # Chart 3: Top Domains
    domain_counts = defaultdict(int)
    for a in artifacts:
        if a.domain:
            domain_counts[a.domain] += 1
    top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Chart 4: Hourly Activity Distribution
    timeline_stats = TimelineEngine.get_timeline_stats(active_case.id)

    # Correlation overview
    correlation_data = CorrelationEngine.analyze_case_correlations(active_case.id)

    has_data = total_artifacts > 0 or total_sources > 0

    return render_template(
        "dashboard/index.html",
        has_data=has_data,
        total_cases=total_cases,
        active_case=active_case,
        total_sources=total_sources,
        total_files=total_files,
        total_artifacts=total_artifacts,
        total_timeline=total_timeline,
        verified_hashes_count=verified_hashes_count,
        mismatch_hashes_count=mismatch_hashes_count,
        browsers=browser_set,
        chart_browser_labels=list(artifacts_by_browser.keys()),
        chart_browser_data=list(artifacts_by_browser.values()),
        chart_type_labels=list(artifacts_by_type.keys()),
        chart_type_data=list(artifacts_by_type.values()),
        top_domains=top_domains,
        hourly_distribution=timeline_stats["hourly_distribution"],
        correlation_summary=correlation_data
    )
