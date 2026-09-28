from datetime import datetime, timezone
from app.extensions import db

class EvidenceSource(db.Model):
    __tablename__ = "evidence_sources"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    source_type = db.Column(db.String(64), default="DIRECTORY_COPY") # LIVE_PROFILE, FORENSIC_IMAGE, DIRECTORY_COPY, SYNTHETIC_DEMO
    browser_type = db.Column(db.String(32), nullable=False, index=True) # CHROME, EDGE, FIREFOX, UNKNOWN
    profile_name = db.Column(db.String(128), default="Default")
    original_source_path = db.Column(db.Text, nullable=False)
    forensic_copy_path = db.Column(db.Text, nullable=True)
    acquisition_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    status = db.Column(db.String(32), default="IMPORTED") # IMPORTED, PROCESSING, PROCESSED, VERIFIED, ERROR
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    files = db.relationship("EvidenceFile", backref="source", cascade="all, delete-orphan", lazy="dynamic")
    artifacts = db.relationship("Artifact", backref="source", cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "name": self.name,
            "source_type": self.source_type,
            "browser_type": self.browser_type,
            "profile_name": self.profile_name,
            "original_source_path": self.original_source_path,
            "forensic_copy_path": self.forensic_copy_path,
            "acquisition_date": self.acquisition_date.isoformat() if self.acquisition_date else None,
            "status": self.status,
            "notes": self.notes,
            "files_count": self.files.count(),
            "artifacts_count": self.artifacts.count(),
        }

class EvidenceFile(db.Model):
    __tablename__ = "evidence_files"

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("evidence_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    rel_path = db.Column(db.String(512), nullable=False)
    source_full_path = db.Column(db.Text, nullable=False)
    forensic_copy_path = db.Column(db.Text, nullable=False)
    file_size = db.Column(db.BigInteger, default=0)
    hash_algorithm = db.Column(db.String(32), default="SHA-256")
    original_hash = db.Column(db.String(64), nullable=False, index=True)
    last_verified_hash = db.Column(db.String(64), nullable=True)
    verification_status = db.Column(db.String(32), default="UNVERIFIED") # UNVERIFIED, INTEGRITY VERIFIED, INTEGRITY MISMATCH
    verified_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    artifacts = db.relationship("Artifact", backref="evidence_file", cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "source_id": self.source_id,
            "case_id": self.case_id,
            "file_name": self.file_name,
            "rel_path": self.rel_path,
            "source_full_path": self.source_full_path,
            "forensic_copy_path": self.forensic_copy_path,
            "file_size": self.file_size,
            "hash_algorithm": self.hash_algorithm,
            "original_hash": self.original_hash,
            "last_verified_hash": self.last_verified_hash,
            "verification_status": self.verification_status,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
