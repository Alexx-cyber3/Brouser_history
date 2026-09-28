from functools import wraps
from flask import abort, request, session, jsonify
from flask_login import current_user
from datetime import datetime, timezone
import json

from app.extensions import db
from app.models.audit import AuditLog

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles and "ADMIN" not in roles and current_user.role != "ADMIN":
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def investigator_required(f):
    return role_required("ADMIN", "INVESTIGATOR")(f)

def admin_required(f):
    return role_required("ADMIN")(f)

def log_audit(action: str, case_id=None, status="SUCCESS", details=None):
    """Record an audit log entry for the current user and action."""
    try:
        username = current_user.username if current_user.is_authenticated else "SYSTEM"
        user_id = current_user.id if current_user.is_authenticated else None
        ip_addr = request.remote_addr if request else "127.0.0.1"

        entry = AuditLog(
            case_id=case_id,
            user_id=user_id,
            username=username,
            action=action,
            status=status,
            ip_address=ip_addr,
            timestamp=datetime.now(timezone.utc)
        )
        if details:
            entry.set_details(details)
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()

def api_response(success=True, data=None, message="", errors=None, status_code=200):
    return jsonify({
        "success": success,
        "data": data if data is not None else {},
        "message": message,
        "errors": errors or []
    }), status_code
