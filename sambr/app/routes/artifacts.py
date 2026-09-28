from flask import Blueprint, render_template, request, session
from flask_login import login_required

from app.models.case import Case
from app.models.artifact import Artifact
from app.utils import api_response

artifacts_bp = Blueprint("artifacts", __name__)

@artifacts_bp.route("/cases/<int:case_id>/artifacts")
@login_required
def index(case_id: int):
    case = Case.query.get_or_404(case_id)
    session["active_case_id"] = case.id

    current_type = request.args.get("type", "ALL").upper()
    browser_filter = request.args.get("browser", "ALL").upper()
    search_q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Artifact.query.filter_by(case_id=case.id)
    if current_type != "ALL":
        query = query.filter_by(artifact_type=current_type)
    if browser_filter != "ALL":
        query = query.filter_by(browser=browser_filter)
    if search_q:
        kw = f"%{search_q}%"
        query = query.filter(
            (Artifact.title.ilike(kw)) |
            (Artifact.url.ilike(kw)) |
            (Artifact.domain.ilike(kw))
        )

    pagination = query.order_by(Artifact.timestamp_utc.desc()).paginate(page=page, per_page=40, error_out=False)

    # Category counts
    counts = {
        "ALL": Artifact.query.filter_by(case_id=case.id).count(),
        "HISTORY": Artifact.query.filter_by(case_id=case.id, artifact_type="HISTORY").count(),
        "COOKIE": Artifact.query.filter_by(case_id=case.id, artifact_type="COOKIE").count(),
        "DOWNLOAD": Artifact.query.filter_by(case_id=case.id, artifact_type="DOWNLOAD").count(),
        "BOOKMARK": Artifact.query.filter_by(case_id=case.id, artifact_type="BOOKMARK").count(),
        "SESSION": Artifact.query.filter_by(case_id=case.id, artifact_type="SESSION").count(),
        "CACHE": Artifact.query.filter_by(case_id=case.id, artifact_type="CACHE").count(),
    }

    return render_template(
        "artifacts/index.html",
        case=case,
        artifacts=pagination.items,
        pagination=pagination,
        current_type=current_type,
        browser_filter=browser_filter,
        search_q=search_q,
        counts=counts
    )

@artifacts_bp.route("/artifacts/<int:artifact_id>")
@login_required
def get_artifact(artifact_id: int):
    art = Artifact.query.get_or_404(artifact_id)
    return api_response(success=True, data=art.to_dict())
