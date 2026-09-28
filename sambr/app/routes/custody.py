from flask import Blueprint, render_template, session
from flask_login import login_required

from app.models.case import Case
from app.models.custody import CustodyEvent
from app.models.audit import AuditLog

custody_bp = Blueprint("custody", __name__)

@custody_bp.route("/cases/<int:case_id>/custody")
@login_required
def index(case_id: int):
    case = Case.query.get_or_404(case_id)
    session["active_case_id"] = case.id

    events = CustodyEvent.query.filter_by(case_id=case.id).order_by(CustodyEvent.timestamp.asc()).all()
    return render_template("custody/index.html", case=case, events=events)

@custody_bp.route("/cases/<int:case_id>/audit")
@login_required
def audit_log(case_id: int):
    case = Case.query.get_or_404(case_id)
    session["active_case_id"] = case.id

    logs = AuditLog.query.filter_by(case_id=case.id).order_by(AuditLog.timestamp.desc()).all()
    return render_template("custody/audit.html", case=case, logs=logs)

@custody_bp.route("/audit/system")
@login_required
def system_audit():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(200).all()
    return render_template("custody/system_audit.html", logs=logs)
