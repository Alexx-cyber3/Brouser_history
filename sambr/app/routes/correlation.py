from flask import Blueprint, render_template, session
from flask_login import login_required

from app.models.case import Case
from app.forensic.correlation_engine import CorrelationEngine

correlation_bp = Blueprint("correlation", __name__)

@correlation_bp.route("/cases/<int:case_id>/correlation")
@login_required
def index(case_id: int):
    case = Case.query.get_or_404(case_id)
    session["active_case_id"] = case.id

    correlations = CorrelationEngine.analyze_case_correlations(case.id)

    return render_template(
        "correlation/index.html",
        case=case,
        correlations=correlations
    )
