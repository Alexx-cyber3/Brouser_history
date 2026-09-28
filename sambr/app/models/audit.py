from datetime import datetime, timezone
import json
from app.extensions import db

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(64), nullable=False, index=True)
    status = db.Column(db.String(32), default="SUCCESS") # SUCCESS, WARNING, ERROR
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    details_json = db.Column(db.Text, nullable=True)

    def get_details(self):
        if not self.details_json:
            return {}
        try:
            return json.loads(self.details_json)
        except Exception:
            return {}

    def set_details(self, data):
        self.details_json = json.dumps(data) if data is not None else None

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "status": self.status,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "details": self.get_details()
        }
