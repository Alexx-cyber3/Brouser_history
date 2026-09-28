import tempfile
import shutil
from pathlib import Path

from app.forensic.synthetic_generator import SyntheticForensicEvidenceGenerator
from app.browser_adapters.chrome import ChromeBrowserAdapter
from app.browser_adapters.edge import EdgeBrowserAdapter
from app.browser_adapters.firefox import FirefoxBrowserAdapter

def test_synthetic_chrome_adapter():
    temp_dir = Path(tempfile.mkdtemp(prefix="tf_chrome_test_"))
    try:
        profiles = SyntheticForensicEvidenceGenerator.generate_all(temp_dir)
        chrome_dir = profiles["CHROME"]

        adapter = ChromeBrowserAdapter(chrome_dir)
        artifacts = adapter.collect_all_artifacts()

        assert len(artifacts["history"]) > 0
        assert len(artifacts["downloads"]) > 0
        assert len(artifacts["cookies"]) > 0
        assert len(artifacts["bookmarks"]) > 0

        # Check history item fields
        h0 = artifacts["history"][0]
        assert h0["artifact_type"] == "HISTORY"
        assert h0["browser"] == "CHROME"
        assert h0["timestamp_utc"] is not None
        assert h0["domain"] is not None

        # Check cookie protection status
        c0 = artifacts["cookies"][0]
        assert c0["is_encrypted"] is True
        assert c0["metadata"]["protection_status"] == "Encrypted/Protected"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_synthetic_firefox_adapter():
    temp_dir = Path(tempfile.mkdtemp(prefix="tf_ff_test_"))
    try:
        profiles = SyntheticForensicEvidenceGenerator.generate_all(temp_dir)
        ff_dir = profiles["FIREFOX"]

        adapter = FirefoxBrowserAdapter(ff_dir)
        artifacts = adapter.collect_all_artifacts()

        assert len(artifacts["history"]) > 0
        assert len(artifacts["cookies"]) > 0
        assert len(artifacts["bookmarks"]) > 0

        h0 = artifacts["history"][0]
        assert h0["browser"] == "FIREFOX"
        assert h0["domain"] is not None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
