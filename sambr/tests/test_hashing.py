import tempfile
from pathlib import Path
from app.forensic.hash_engine import HashEngine

def test_file_hashing_and_verification():
    with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f:
        f.write("Forensic Evidence Data Payload 2026")
        f_path = Path(f.name)

    try:
        # Calculate baseline hash
        h1 = HashEngine.calculate_file_sha256(f_path)
        assert len(h1) == 64

        # Verify integrity against baseline
        res1 = HashEngine.verify_file_integrity(f_path, h1)
        assert res1["is_valid"] is True
        assert res1["status"] == "INTEGRITY VERIFIED"

        # Tamper with file
        with open(f_path, "a", encoding="utf-8") as f:
            f.write("TAMPERED")

        # Verify mismatch detected
        res2 = HashEngine.verify_file_integrity(f_path, h1)
        assert res2["is_valid"] is False
        assert res2["status"] == "INTEGRITY MISMATCH"

    finally:
        if f_path.exists():
            f_path.unlink()
