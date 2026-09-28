from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from datetime import datetime, timezone
from pathlib import Path

from app.extensions import db
from app.config import Config
from app.models.case import Case
from app.models.custody import CustodyEvent
from app.models.note import InvestigatorNote
from app.forensic.synthetic_generator import SyntheticForensicEvidenceGenerator
from app.forensic.evidence_manager import EvidenceManager
from app.utils import investigator_required, log_audit

cases_bp = Blueprint("cases", __name__)

@cases_bp.route("/cases", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        case_number = request.form.get("case_number", "").strip().upper()
        title = request.form.get("title", "").strip()
        investigator_name = request.form.get("investigator_name", current_user.full_name).strip()
        organization = request.form.get("organization", current_user.organization).strip()
        description = request.form.get("description", "").strip()

        if not case_number or not title:
            flash("Case Number and Title are mandatory for legal traceability.", "danger")
            return redirect(url_for("cases.index"))

        existing = Case.query.filter_by(case_number=case_number).first()
        if existing:
            flash(f"Case with number '{case_number}' already exists in registry.", "warning")
            return redirect(url_for("cases.index"))

        case = Case(
            case_number=case_number,
            title=title,
            investigator_name=investigator_name,
            organization=organization,
            description=description,
            status="OPEN"
        )
        db.session.add(case)
        db.session.flush()

        # Log Custody & Audit
        db.session.add(CustodyEvent(
            case_id=case.id,
            action="IMPORTED",
            actor=current_user.full_name,
            description=f"Case registry docket created: {case.case_number} - {case.title}"
        ))
        log_audit("CASE_CREATED", case_id=case.id, details={"case_number": case.case_number, "title": title})
        db.session.commit()

        # Set as active case
        session["active_case_id"] = case.id
        flash(f"Case {case.case_number} created and set as active investigation.", "success")
        return redirect(url_for("cases.detail", case_id=case.id))

    all_cases = Case.query.order_by(Case.created_at.desc()).all()
    active_case_id = session.get("active_case_id")
    return render_template("cases/index.html", cases=all_cases, active_case_id=active_case_id)

@cases_bp.route("/cases/<int:case_id>")
@login_required
def detail(case_id: int):
    case = Case.query.get_or_404(case_id)
    session["active_case_id"] = case.id
    notes = case.notes.order_by(InvestigatorNote.created_at.desc()).all()
    return render_template("cases/detail.html", case=case, notes=notes)

@cases_bp.route("/cases/<int:case_id>/select", methods=["GET", "POST"])
@login_required
def select(case_id: int):
    case = Case.query.get_or_404(case_id)
    session["active_case_id"] = case.id
    flash(f"Active workspace switched to Case #{case.case_number}.", "info")

    referrer = request.referrer or ""
    import re
    match = re.search(r"/cases/(\d+)(/.*)?$", referrer)
    if match:
        subpath = match.group(2) or ""
        if any(x in subpath for x in ["select", "note", "demo_dataset", "wizard", "delete", "verify_all"]):
            return redirect(url_for("cases.detail", case_id=case.id))
        return redirect(f"/cases/{case.id}{subpath}")

    return redirect(referrer or url_for("dashboard.index"))

@cases_bp.route("/cases/<int:case_id>/note", methods=["POST"])
@login_required
@investigator_required
def add_note(case_id: int):
    case = Case.query.get_or_404(case_id)
    content = request.form.get("content", "").strip()
    target_type = request.form.get("target_type", "CASE")
    target_id = request.form.get("target_id", type=int)

    if content:
        note = InvestigatorNote(
            case_id=case.id,
            target_type=target_type,
            target_id=target_id,
            author=current_user.full_name,
            content=content
        )
        db.session.add(note)
        db.session.commit()
        log_audit("INVESTIGATOR_NOTE_ADDED", case_id=case.id, details={"author": current_user.full_name})
        flash("Investigator note appended to case ledger.", "success")

    return redirect(url_for("cases.detail", case_id=case.id))

@cases_bp.route("/cases/<int:case_id>/demo_dataset", methods=["POST"])
@login_required
@investigator_required
def load_demo_dataset(case_id: int):
    """
    Safely generates and imports synthetic browser profiles (Chrome, Edge, Firefox)
    directly into this case for testing and demonstration.
    """
    case = Case.query.get_or_404(case_id)
    try:
        demo_base = Config.EVIDENCE_DIR / f"demo_synthetic_{case.case_number}"
        profile_paths = SyntheticForensicEvidenceGenerator.generate_all(demo_base)

        results = []
        for browser, ppath in profile_paths.items():
            res = EvidenceManager.import_and_process_profile(
                case=case,
                source_path=ppath,
                browser_type=browser,
                profile_name="Synthetic Profile (DEMO)",
                actor=f"{current_user.full_name} (Synthetic Ingestion)",
                notes="Synthetically generated safe test evidence for verification and demonstration."
            )
            results.append(res)

        log_audit("DEMO_EVIDENCE_INGESTED", case_id=case.id, details={"profiles": len(results)})
        flash(f"Successfully generated and ingested 3 synthetic browser profiles (Chrome, Edge, Firefox) into Case {case.case_number}.", "success")
    except Exception as e:
        flash(f"Failed to ingest synthetic demo evidence: {str(e)}", "danger")

    return redirect(url_for("cases.detail", case_id=case.id))
