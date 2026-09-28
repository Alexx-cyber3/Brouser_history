from datetime import datetime, timezone
from app.extensions import db

class Case(db.Model):
    __tablename__ = "cases"

    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(64), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    investigator_name = db.Column(db.String(128), nullable=False)
    organization = db.Column(db.String(128), default="Digital Forensics Unit")
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default="OPEN", nullable=False)  # OPEN, IN PROGRESS, ANALYSIS COMPLETE, CLOSED
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    evidence_sources = db.relationship("EvidenceSource", backref="case", cascade="all, delete-orphan", lazy="dynamic")
    evidence_files = db.relationship("EvidenceFile", backref="case", cascade="all, delete-orphan", lazy="dynamic")
    artifacts = db.relationship("Artifact", backref="case", cascade="all, delete-orphan", lazy="dynamic")
    timeline_events = db.relationship("TimelineEvent", backref="case", cascade="all, delete-orphan", lazy="dynamic")
    custody_events = db.relationship("CustodyEvent", backref="case", cascade="all, delete-orphan", lazy="dynamic")
    audit_logs = db.relationship("AuditLog", backref="case", cascade="all, delete-orphan", lazy="dynamic")
    reports = db.relationship("ReportRecord", backref="case", cascade="all, delete-orphan", lazy="dynamic")
    notes = db.relationship("InvestigatorNote", backref="case", cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "case_number": self.case_number,
            "title": self.title,
            "investigator_name": self.investigator_name,
            "organization": self.organization,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "evidence_sources_count": self.evidence_sources.count(),
            "artifacts_count": self.artifacts.count(),
            "timeline_events_count": self.timeline_events.count(),
        }
