from flask import Blueprint, render_template, request, session, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from pathlib import Path

from app.models.case import Case
from app.models.report import ReportRecord
from app.forensic.report_engine import ReportEngine
from app.utils import investigator_required, log_audit

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/cases/<int:case_id>/reports", methods=["GET", "POST"])
@login_required
def index(case_id: int):
    case = Case.query.get_or_404(case_id)
    session["active_case_id"] = case.id

    if request.method == "POST":
        fmt = request.form.get("format", "pdf").lower()
        notes = request.form.get("notes", "").strip()

        try:
            record = ReportEngine.generate_report(
                case=case,
                report_format=fmt,
                investigator_name=current_user.full_name,
                notes=notes
            )
            log_audit("REPORT_GENERATED", case_id=case.id, details={"format": fmt, "hash": record.file_hash})
            flash(f"Forensic {fmt.upper()} report generated successfully. Hash: {record.file_hash[:16]}...", "success")
        except Exception as e:
            flash(f"Report generation error: {str(e)}", "danger")

        return redirect(url_for("reports.index", case_id=case.id))

    existing_reports = ReportRecord.query.filter_by(case_id=case.id).order_by(ReportRecord.generated_at.desc()).all()
    return render_template("reports/index.html", case=case, reports=existing_reports)

@reports_bp.route("/reports/download/<int:report_id>")
@login_required
def download(report_id: int):
    rep = ReportRecord.query.get_or_404(report_id)
    p = Path(rep.file_path)
    if not p.exists():
        flash("Target report file no longer exists in repository.", "danger")
        return redirect(url_for("reports.index", case_id=rep.case_id))

    log_audit("REPORT_DOWNLOADED", case_id=rep.case_id, details={"report_id": rep.id, "filename": p.name})

    # MIME types
    mimes = {
        "PDF": "application/pdf",
        "HTML": "text/html",
        "JSON": "application/json",
        "CSV": "text/csv"
    }

    return send_file(
        str(p),
        as_attachment=True,
        download_name=p.name,
        mimetype=mimes.get(rep.report_format, "application/octet-stream")
    )
