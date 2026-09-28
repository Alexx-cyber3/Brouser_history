from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from pathlib import Path
from datetime import datetime, timezone

from app.extensions import db
from app.models.case import Case
from app.models.evidence import EvidenceSource, EvidenceFile
from app.models.custody import CustodyEvent
from app.forensic.browser_detector import BrowserDetector
from app.forensic.evidence_manager import EvidenceManager
from app.forensic.hash_engine import HashEngine
from app.utils import investigator_required, log_audit, api_response

evidence_bp = Blueprint("evidence", __name__)

@evidence_bp.route("/cases/<int:case_id>/evidence")
@login_required
def index(case_id: int):
    case = Case.query.get_or_404(case_id)
    sources = case.evidence_sources.all()
    files = case.evidence_files.all()
    return render_template("evidence/index.html", case=case, sources=sources, files=files)

@evidence_bp.route("/cases/<int:case_id>/evidence/wizard", methods=["GET", "POST"])
@login_required
@investigator_required
def wizard(case_id: int):
    case = Case.query.get_or_404(case_id)

    # Detect installed browsers on the host system
    system_paths = BrowserDetector.get_system_browser_paths()
    detected_profiles = {}
    if system_paths.get("CHROME"):
        detected_profiles["CHROME"] = BrowserDetector.detect_chromium_profiles(system_paths["CHROME"])
    if system_paths.get("EDGE"):
        detected_profiles["EDGE"] = BrowserDetector.detect_chromium_profiles(system_paths["EDGE"])
    if system_paths.get("FIREFOX"):
        detected_profiles["FIREFOX"] = BrowserDetector.detect_firefox_profiles(system_paths["FIREFOX"])

    if request.method == "POST":
        source_mode = request.form.get("source_mode", "detected")
        browser_type = request.form.get("browser_type", "").upper()
        custom_path = request.form.get("custom_path", "").strip()
        selected_profile_path = request.form.get("profile_path", "").strip()
        profile_name = request.form.get("profile_name", "Default").strip()
        notes = request.form.get("notes", "").strip()

        target_path = None
        if source_mode == "manual":
            if not custom_path:
                flash("Please specify an absolute path to the browser evidence folder.", "danger")
                return redirect(url_for("evidence.wizard", case_id=case.id))

            target_p = Path(custom_path)
            if not target_p.exists():
                flash(f"Specified path does not exist on filesystem: {custom_path}", "danger")
                return redirect(url_for("evidence.wizard", case_id=case.id))

            # Auto-identify if browser type was generic
            ident = BrowserDetector.identify_evidence_source(target_p)
            if ident["valid"]:
                browser_type = ident["browser_type"]
                # If identified profiles exist, take the first or the path itself
                target_path = Path(ident["profiles"][0]["path"]) if ident["profiles"] else target_p
                profile_name = ident["profiles"][0]["profile_name"] if ident["profiles"] else target_p.name
            else:
                target_path = target_p
                if not browser_type:
                    browser_type = "CHROME"
        else:
            if not selected_profile_path:
                flash("Please select a detected profile to process.", "warning")
                return redirect(url_for("evidence.wizard", case_id=case.id))
            target_path = Path(selected_profile_path)

        # Process through EvidenceManager pipeline
        try:
            res = EvidenceManager.import_and_process_profile(
                case=case,
                source_path=target_path,
                browser_type=browser_type,
                profile_name=profile_name,
                actor=current_user.full_name,
                notes=notes
            )
            log_audit(
                "EVIDENCE_ACQUIRED",
                case_id=case.id,
                details={
                    "browser": browser_type,
                    "profile": profile_name,
                    "artifacts_count": res["artifacts_count"],
                    "files_count": res["files_count"]
                }
            )
            flash(
                f"Successfully acquired and parsed {res['artifacts_count']} artifacts and {res['files_count']} evidence files from {browser_type} ({profile_name}).",
                "success"
            )
            return redirect(url_for("evidence.index", case_id=case.id))
        except Exception as e:
            flash(f"Forensic acquisition failed: {str(e)}", "danger")
            return redirect(url_for("evidence.wizard", case_id=case.id))

    return render_template(
        "evidence/wizard.html",
        case=case,
        system_paths=system_paths,
        detected_profiles=detected_profiles
    )

@evidence_bp.route("/evidence/file/<int:file_id>/verify", methods=["POST"])
@login_required
@investigator_required
def verify_file(file_id: int):
    """
    Re-hashes source evidence file and compares with initial baseline SHA-256.
    """
    ef = EvidenceFile.query.get_or_404(file_id)
    verify_result = HashEngine.verify_file_integrity(ef.source_full_path, ef.original_hash)

    ef.last_verified_hash = verify_result.get("calculated_hash")
    ef.verification_status = verify_result["status"]
    ef.verified_at = datetime.now(timezone.utc)

    # Log Custody: VERIFIED
    db.session.add(CustodyEvent(
        case_id=ef.case_id,
        evidence_id=ef.source_id,
        evidence_file_id=ef.id,
        action="VERIFIED",
        actor=current_user.full_name,
        description=f"Cryptographic hash re-verification executed on {ef.file_name}. Outcome: {ef.verification_status}",
        hash_value=ef.last_verified_hash
    ))
    db.session.commit()

    log_audit("HASH_VERIFIED", case_id=ef.case_id, details={"file_id": ef.id, "status": ef.verification_status})

    return api_response(
        success=True,
        data={
            "file_id": ef.id,
            "status": ef.verification_status,
            "calculated_hash": ef.last_verified_hash,
            "is_valid": verify_result["is_valid"]
        },
        message=f"Integrity check complete: {ef.verification_status}"
    )

@evidence_bp.route("/cases/<int:case_id>/evidence/verify_all", methods=["POST"])
@login_required
@investigator_required
def verify_all(case_id: int):
    case = Case.query.get_or_404(case_id)
    files = case.evidence_files.all()

    verified_count = 0
    mismatch_count = 0

    for ef in files:
        res = HashEngine.verify_file_integrity(ef.source_full_path, ef.original_hash)
        ef.last_verified_hash = res.get("calculated_hash")
        ef.verification_status = res["status"]
        ef.verified_at = datetime.now(timezone.utc)
        if res["is_valid"]:
            verified_count += 1
        else:
            mismatch_count += 1

    db.session.add(CustodyEvent(
        case_id=case.id,
        action="VERIFIED",
        actor=current_user.full_name,
        description=f"Batch hash verification performed on {len(files)} files: {verified_count} verified, {mismatch_count} mismatches."
    ))
    db.session.commit()
    log_audit("BATCH_HASH_VERIFY", case_id=case.id, details={"verified": verified_count, "mismatches": mismatch_count})

    flash(f"Batch verification finished: {verified_count} files verified, {mismatch_count} mismatches.", "info" if mismatch_count == 0 else "warning")
    return redirect(url_for("evidence.index", case_id=case.id))
