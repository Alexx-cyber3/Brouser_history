from datetime import datetime, timezone
import json
from app.extensions import db

class TimelineEvent(db.Model):
    __tablename__ = "timeline_events"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=True, index=True)

    browser = db.Column(db.String(32), nullable=False, index=True)
    profile = db.Column(db.String(128), default="Default", nullable=False)
    artifact_type = db.Column(db.String(32), nullable=False, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True) # VISIT, DOWNLOAD, COOKIE_CREATED, etc.

    timestamp_utc = db.Column(db.DateTime, nullable=False, index=True)
    timestamp_raw = db.Column(db.String(128), nullable=True)

    title = db.Column(db.String(512), nullable=True)
    url = db.Column(db.Text, nullable=True)
    domain = db.Column(db.String(255), nullable=True, index=True)
    summary = db.Column(db.Text, nullable=True)

    source_file = db.Column(db.String(255), nullable=True)
    source_hash = db.Column(db.String(64), nullable=True)
    confidence = db.Column(db.String(32), default="DERIVED", nullable=False) # DIRECT, DERIVED, CORRELATED, UNKNOWN

    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def get_metadata(self):
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {}

    def set_metadata(self, data):
        self.metadata_json = json.dumps(data) if data is not None else None

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "artifact_id": self.artifact_id,
            "browser": self.browser,
            "profile": self.profile,
            "artifact_type": self.artifact_type,
            "event_type": self.event_type,
            "timestamp_utc": self.timestamp_utc.isoformat() if self.timestamp_utc else None,
            "timestamp_raw": self.timestamp_raw,
            "title": self.title,
            "url": self.url,
            "domain": self.domain,
            "summary": self.summary,
            "source_file": self.source_file,
            "source_hash": self.source_hash,
            "confidence": self.confidence,
            "metadata": self.get_metadata(),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
