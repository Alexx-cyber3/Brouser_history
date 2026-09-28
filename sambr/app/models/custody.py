from datetime import datetime, timezone
from app.extensions import db

class CustodyEvent(db.Model):
    __tablename__ = "custody_events"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey("evidence_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    evidence_file_id = db.Column(db.Integer, db.ForeignKey("evidence_files.id", ondelete="SET NULL"), nullable=True, index=True)

    action = db.Column(db.String(64), nullable=False) # IMPORTED, HASHED, COPIED, PROCESSED, ANALYZED, EXPORTED, REPORT_GENERATED, VERIFIED
    actor = db.Column(db.String(128), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    hash_value = db.Column(db.String(64), nullable=True) # SHA-256 at the moment of action if applicable
    system_info = db.Column(db.String(255), default="TraceFusion Forensic Engine (Windows)")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "evidence_id": self.evidence_id,
            "evidence_file_id": self.evidence_file_id,
            "action": self.action,
            "actor": self.actor,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "description": self.description,
            "hash_value": self.hash_value,
            "system_info": self.system_info
        }
