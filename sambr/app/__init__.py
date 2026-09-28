import os
from flask import Flask, session
from pathlib import Path
from datetime import datetime, timezone

from app.config import Config
from app.extensions import db, login_manager

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.cases import cases_bp
    from app.routes.evidence import evidence_bp
    from app.routes.timeline import timeline_bp
    from app.routes.artifacts import artifacts_bp
    from app.routes.correlation import correlation_bp
    from app.routes.search import search_bp
    from app.routes.custody import custody_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(evidence_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(artifacts_bp)
    app.register_blueprint(correlation_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(custody_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)

    # Template context processors & filters
    @app.context_processor
    def inject_global_forensic_context():
        from app.models.case import Case
        active_case_id = session.get("active_case_id")
        active_case = None
        if active_case_id:
            active_case = Case.query.get(active_case_id)
        all_cases = Case.query.order_by(Case.created_at.desc()).all()
        return {
            "current_active_case": active_case,
            "all_cases_nav": all_cases,
            "app_version": Config.APPLICATION_VERSION,
            "app_name": Config.APPLICATION_NAME,
            "now_utc": datetime.now(timezone.utc)
        }

    @app.template_filter("format_utc")
    def format_utc_filter(dt):
        if not dt:
            return "N/A"
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Create tables and seed default admin investigator if missing
    with app.app_context():
        db.create_all()
        seed_default_user()

    return app

def seed_default_user():
    from app.models.user import User
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@tracefusion.local",
            full_name="Chief Forensic Examiner",
            role="ADMIN",
            organization="Digital Forensics & Cyber Intelligence Unit",
            is_active=True
        )
        admin.set_password("forensic2026")
        db.session.add(admin)

    inv = User.query.filter_by(username="investigator").first()
    if not inv:
        inv = User(
            username="investigator",
            email="examiner@tracefusion.local",
            full_name="Lead Cyber Investigator",
            role="INVESTIGATOR",
            organization="Digital Forensics & Cyber Intelligence Unit",
            is_active=True
        )
        inv.set_password("investigator2026")
        db.session.add(inv)

    db.session.commit()
