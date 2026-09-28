import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

CHUNK_SIZE = 1024 * 1024  # 1MB chunks for high-throughput hashing

class HashEngine:
    """
    Forensic SHA-256 hashing and integrity verification engine.
    Follows forensic standard: strictly read-only stream processing.
    """

    @staticmethod
    def calculate_file_sha256(file_path: Path | str) -> str:
        """
        Calculate SHA-256 hash of a file using chunked binary streaming.
        Guarantees strictly read-only access.
        """
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"Target evidence file does not exist: {file_path}")

        hasher = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                hasher.update(chunk)
        return hasher.hexdigest().lower()

    @staticmethod
    def calculate_bytes_sha256(data: bytes) -> str:
        """Calculate SHA-256 hash of a raw byte buffer."""
        return hashlib.sha256(data).hexdigest().lower()

    @classmethod
    def verify_file_integrity(cls, file_path: Path | str, expected_hash: str) -> Dict[str, Any]:
        """
        Re-hashes the target file and compares against the baseline forensic hash.
        Returns verifiable forensic integrity status.
        """
        now = datetime.now(timezone.utc)
        clean_expected = (expected_hash or "").strip().lower()

        try:
            current_hash = cls.calculate_file_sha256(file_path)
            is_match = (current_hash == clean_expected)
            status = "INTEGRITY VERIFIED" if is_match else "INTEGRITY MISMATCH"

            return {
                "status": status,
                "is_valid": is_match,
                "expected_hash": clean_expected,
                "calculated_hash": current_hash,
                "verified_at": now.isoformat(),
                "file_path": str(file_path),
                "error": None
            }
        except Exception as e:
            return {
                "status": "VERIFICATION FAILED",
                "is_valid": False,
                "expected_hash": clean_expected,
                "calculated_hash": None,
                "verified_at": now.isoformat(),
                "file_path": str(file_path),
                "error": str(e)
            }
