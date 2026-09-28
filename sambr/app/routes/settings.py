import sys
import shutil
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from pathlib import Path

from app.config import Config
from app.models.case import Case
from app.models.artifact import Artifact
from app.browser_adapters import ChromeBrowserAdapter, EdgeBrowserAdapter, FirefoxBrowserAdapter

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/settings")
@login_required
def index():
    # Disk usage
    total, used, free = shutil.disk_usage(Config.BASE_DIR)

    health_info = {
        "app_name": Config.APPLICATION_NAME,
        "app_version": Config.APPLICATION_VERSION,
        "python_version": sys.version.split()[0],
        "database_uri": Config.SQLALCHEMY_DATABASE_URI,
        "cases_dir": str(Config.CASES_DIR),
        "evidence_dir": str(Config.EVIDENCE_DIR),
        "reports_dir": str(Config.REPORTS_DIR),
        "disk_total_gb": round(total / (1024**3), 2),
        "disk_used_gb": round(used / (1024**3), 2),
        "disk_free_gb": round(free / (1024**3), 2),
        "total_cases_count": Case.query.count(),
        "total_artifacts_count": Artifact.query.count(),
        "parsers": [
            {"browser": "Google Chrome", "class": "ChromeBrowserAdapter", "version": ChromeBrowserAdapter.parser_version, "status": "ACTIVE"},
            {"browser": "Microsoft Edge", "class": "EdgeBrowserAdapter", "version": EdgeBrowserAdapter.parser_version, "status": "ACTIVE"},
            {"browser": "Mozilla Firefox", "class": "FirefoxBrowserAdapter", "version": FirefoxBrowserAdapter.parser_version, "status": "ACTIVE"}
        ]
    }
    return render_template("settings/index.html", health=health_info)
