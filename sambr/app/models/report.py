from datetime import datetime, timezone
import json
from app.extensions import db

class ReportRecord(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    report_format = db.Column(db.String(16), nullable=False) # PDF, HTML, JSON, CSV
    file_path = db.Column(db.Text, nullable=False)
    file_hash = db.Column(db.String(64), nullable=False) # SHA-256 of the generated report document
    generated_by = db.Column(db.String(128), nullable=False)
    generated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    parameters_json = db.Column(db.Text, nullable=True)

    def get_parameters(self):
        if not self.parameters_json:
            return {}
        try:
            return json.loads(self.parameters_json)
        except Exception:
            return {}

    def set_parameters(self, data):
        self.parameters_json = json.dumps(data) if data is not None else None

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "title": self.title,
            "report_format": self.report_format,
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "parameters": self.get_parameters()
        }
