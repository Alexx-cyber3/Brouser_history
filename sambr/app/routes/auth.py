from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timezone

from app.extensions import db, login_manager
from app.models.user import User
from app.utils import log_audit

auth_bp = Blueprint("auth", __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("This investigator account has been deactivated.", "danger")
                return render_template("auth/login.html")

            login_user(user, remember=True)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()

            log_audit("USER_LOGIN", status="SUCCESS", details={"username": username, "role": user.role})
            flash(f"Welcome to TraceFusion Forensic Console, {user.full_name}.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))
        else:
            log_audit("USER_LOGIN_FAILED", status="WARNING", details={"attempted_username": username})
            flash("Invalid investigator credentials or clearance level.", "danger")

    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    log_audit("USER_LOGOUT", status="SUCCESS")
    logout_user()
    flash("Forensic session terminated successfully.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html")
