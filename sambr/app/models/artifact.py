from datetime import datetime, timezone
import json
from app.extensions import db

class Artifact(db.Model):
    __tablename__ = "artifacts"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = db.Column(db.Integer, db.ForeignKey("evidence_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_file_id = db.Column(db.Integer, db.ForeignKey("evidence_files.id", ondelete="SET NULL"), nullable=True, index=True)

    browser = db.Column(db.String(32), nullable=False, index=True)  # CHROME, EDGE, FIREFOX
    profile = db.Column(db.String(128), default="Default", nullable=False)
    artifact_type = db.Column(db.String(32), nullable=False, index=True) # HISTORY, COOKIE, DOWNLOAD, BOOKMARK, CACHE, SESSION, OTHER

    record_identifier = db.Column(db.String(128), nullable=True) # ID in original db
    title = db.Column(db.String(512), nullable=True)
    url = db.Column(db.Text, nullable=True)
    domain = db.Column(db.String(255), nullable=True, index=True)

    timestamp_raw = db.Column(db.String(128), nullable=True) # Original un-normalized timestamp representation
    timestamp_utc = db.Column(db.DateTime, nullable=True, index=True) # Normalized to UTC datetime

    # Associated files / downloads / cache
    file_path = db.Column(db.Text, nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)
    mime_type = db.Column(db.String(128), nullable=True)

    is_encrypted = db.Column(db.Boolean, default=False)
    parser_name = db.Column(db.String(64), nullable=False)
    parser_version = db.Column(db.String(32), default="1.0")
    confidence = db.Column(db.String(32), default="DIRECT", nullable=False) # DIRECT, DERIVED, CORRELATED, UNKNOWN

    metadata_json = db.Column(db.Text, nullable=True) # Serialized JSON with raw fields
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    timeline_event = db.relationship("TimelineEvent", backref="artifact", uselist=False, cascade="all, delete-orphan")

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
            "source_id": self.source_id,
            "evidence_file_id": self.evidence_file_id,
            "browser": self.browser,
            "profile": self.profile,
            "artifact_type": self.artifact_type,
            "record_identifier": self.record_identifier,
            "title": self.title,
            "url": self.url,
            "domain": self.domain,
            "timestamp_raw": self.timestamp_raw,
            "timestamp_utc": self.timestamp_utc.isoformat() if self.timestamp_utc else None,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "is_encrypted": self.is_encrypted,
            "parser_name": self.parser_name,
            "parser_version": self.parser_version,
            "confidence": self.confidence,
            "metadata": self.get_metadata(),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
