from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone
from pathlib import Path

from app.extensions import db
from app.models.case import Case
from app.models.evidence import EvidenceSource, EvidenceFile
from app.models.artifact import Artifact
from app.models.timeline import TimelineEvent
from app.models.custody import CustodyEvent
from app.models.audit import AuditLog
from app.forensic.browser_detector import BrowserDetector
from app.forensic.hash_engine import HashEngine
from app.forensic.timeline_engine import TimelineEngine
from app.forensic.correlation_engine import CorrelationEngine
from app.forensic.report_engine import ReportEngine
from app.utils import api_response, log_audit

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/cases", methods=["GET"])
@login_required
def list_cases():
    cases = Case.query.order_by(Case.created_at.desc()).all()
    return api_response(success=True, data=[c.to_dict() for c in cases])

@api_bp.route("/cases", methods=["POST"])
@login_required
def create_case():
    payload = request.get_json() or {}
    case_num = (payload.get("case_number") or "").strip().upper()
    title = (payload.get("title") or "").strip()
    if not case_num or not title:
        return api_response(success=False, message="case_number and title are required.", status_code=400)

    if Case.query.filter_by(case_number=case_num).first():
        return api_response(success=False, message=f"Case {case_num} already exists.", status_code=409)

    case = Case(
        case_number=case_num,
        title=title,
        investigator_name=payload.get("investigator_name") or current_user.full_name,
        organization=payload.get("organization") or current_user.organization,
        description=payload.get("description", ""),
        status="OPEN"
    )
    db.session.add(case)
    db.session.commit()
    log_audit("API_CASE_CREATED", case_id=case.id, details={"case_number": case.case_number})
    return api_response(success=True, data=case.to_dict(), status_code=201)

@api_bp.route("/cases/<int:case_id>", methods=["GET"])
@login_required
def get_case(case_id: int):
    case = Case.query.get_or_404(case_id)
    return api_response(success=True, data=case.to_dict())

@api_bp.route("/cases/<int:case_id>/timeline", methods=["GET"])
@login_required
def get_timeline(case_id: int):
    case = Case.query.get_or_404(case_id)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    sort_order = request.args.get("sort", "desc")
    browser = request.args.get("browser", "ALL")
    artifact_type = request.args.get("type", "ALL")
    domain = request.args.get("domain", "")
    keyword = request.args.get("q", "")

    data = TimelineEngine.query_timeline(
        case_id=case.id,
        page=page,
        per_page=per_page,
        sort_order=sort_order,
        browser=browser,
        artifact_type=artifact_type,
        domain=domain,
        keyword=keyword
    )
    return api_response(success=True, data=data)

@api_bp.route("/cases/<int:case_id>/artifacts", methods=["GET"])
@login_required
def get_artifacts(case_id: int):
    case = Case.query.get_or_404(case_id)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    atype = request.args.get("type", "ALL")

    q = Artifact.query.filter_by(case_id=case.id)
    if atype != "ALL":
        q = q.filter_by(artifact_type=atype.upper())

    pag = q.order_by(Artifact.timestamp_utc.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return api_response(success=True, data={
        "total": pag.total,
        "page": pag.page,
        "pages": pag.pages,
        "artifacts": [a.to_dict() for a in pag.items]
    })

@api_bp.route("/cases/<int:case_id>/correlations", methods=["GET"])
@login_required
def get_correlations(case_id: int):
    case = Case.query.get_or_404(case_id)
    corr = CorrelationEngine.analyze_case_correlations(case.id)
    return api_response(success=True, data=corr)

@api_bp.route("/evidence/file/<int:file_id>/verify", methods=["POST"])
@login_required
def verify_file(file_id: int):
    ef = EvidenceFile.query.get_or_404(file_id)
    res = HashEngine.verify_file_integrity(ef.source_full_path, ef.original_hash)
    ef.last_verified_hash = res.get("calculated_hash")
    ef.verification_status = res["status"]
    ef.verified_at = datetime.now(timezone.utc)
    db.session.commit()
    return api_response(success=True, data=res)

@api_bp.route("/cases/<int:case_id>/reports", methods=["POST"])
@login_required
def create_report(case_id: int):
    case = Case.query.get_or_404(case_id)
    payload = request.get_json() or {}
    fmt = payload.get("format", "pdf")
    notes = payload.get("notes", "")

    record = ReportEngine.generate_report(case, fmt, current_user.full_name, notes)
    return api_response(success=True, data=record.to_dict(), status_code=201)

@api_bp.route("/detect_path", methods=["POST"])
@login_required
def detect_path():
    payload = request.get_json() or {}
    raw_path = payload.get("path", "")
    if not raw_path:
        return api_response(success=False, message="Path is required", status_code=400)
    p = Path(raw_path)
    res = BrowserDetector.identify_evidence_source(p)
    return api_response(success=res["valid"], data=res, message=res["message"])
