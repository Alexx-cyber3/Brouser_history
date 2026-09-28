from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models.case import Case
from app.models.artifact import Artifact
from app.models.note import SavedSearch
from app.utils import log_audit

search_bp = Blueprint("search", __name__)

@search_bp.route("/cases/<int:case_id>/search", methods=["GET", "POST"])
@login_required
def index(case_id: int):
    case = Case.query.get_or_404(case_id)
    session["active_case_id"] = case.id

    q = request.args.get("q", "").strip()
    browser = request.args.get("browser", "ALL")
    artifact_type = request.args.get("type", "ALL")
    confidence = request.args.get("confidence", "ALL")
    page = request.args.get("page", 1, type=int)

    results = []
    total_found = 0
    pagination = None

    if q or browser != "ALL" or artifact_type != "ALL":
        query = Artifact.query.filter_by(case_id=case.id)

        if browser != "ALL":
            query = query.filter_by(browser=browser.upper())
        if artifact_type != "ALL":
            query = query.filter_by(artifact_type=artifact_type.upper())
        if confidence != "ALL":
            query = query.filter_by(confidence=confidence.upper())

        if q:
            kw = f"%{q}%"
            query = query.filter(
                or_(
                    Artifact.title.ilike(kw),
                    Artifact.url.ilike(kw),
                    Artifact.domain.ilike(kw),
                    Artifact.file_path.ilike(kw),
                    Artifact.record_identifier.ilike(kw)
                )
            )

        pagination = query.order_by(Artifact.timestamp_utc.desc()).paginate(page=page, per_page=40, error_out=False)
        results = pagination.items
        total_found = pagination.total

        log_audit("EVIDENCE_SEARCH", case_id=case.id, details={"query": q, "browser": browser, "results": total_found})

    saved_searches = SavedSearch.query.filter_by(case_id=case.id).all()

    return render_template(
        "search/index.html",
        case=case,
        query_text=q,
        browser=browser,
        artifact_type=artifact_type,
        confidence=confidence,
        results=results,
        total_found=total_found,
        pagination=pagination,
        saved_searches=saved_searches
    )

@search_bp.route("/cases/<int:case_id>/search/save", methods=["POST"])
@login_required
def save_search(case_id: int):
    case = Case.query.get_or_404(case_id)
    name = request.form.get("name", "").strip()
    query_text = request.form.get("query_text", "").strip()
    browser = request.form.get("browser", "ALL")
    artifact_type = request.form.get("type", "ALL")

    if name:
        ss = SavedSearch(
            case_id=case.id,
            name=name,
            query_text=query_text,
            created_by=current_user.full_name
        )
        ss.set_filters({"browser": browser, "type": artifact_type})
        db.session.add(ss)
        db.session.commit()
        flash(f"Search '{name}' saved to case workbench.", "success")

    return redirect(url_for("search.index", case_id=case.id, q=query_text, browser=browser, type=artifact_type))
