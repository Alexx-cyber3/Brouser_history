from datetime import datetime, timezone
import json
from app.extensions import db

class InvestigatorNote(db.Model):
    __tablename__ = "investigator_notes"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = db.Column(db.String(32), nullable=False) # CASE, EVIDENCE, ARTIFACT, TIMELINE, CORRELATION
    target_id = db.Column(db.Integer, nullable=True) # ID of the target object if applicable
    author = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "author": self.author,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class SavedSearch(db.Model):
    __tablename__ = "saved_searches"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    query_text = db.Column(db.String(255), nullable=True)
    filters_json = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def get_filters(self):
        if not self.filters_json:
            return {}
        try:
            return json.loads(self.filters_json)
        except Exception:
            return {}

    def set_filters(self, data):
        self.filters_json = json.dumps(data) if data is not None else None

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "name": self.name,
            "query_text": self.query_text,
            "filters": self.get_filters(),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
