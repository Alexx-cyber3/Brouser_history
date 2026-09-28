# TraceFusion Testing & Quality Assurance Guide

## Automated Test Suite

TraceFusion employs `pytest` to execute comprehensive automated unit and integration tests.

### Running the Test Suite
```powershell
python -m pytest tests/ -v
```

### Test Coverage Areas

| Test Module | Coverage Scope |
|---|---|
| **`tests/test_timestamps.py`** | Chrome WebKit microsecond epoch conversion ($11,644,473,600$s offset), Firefox PRTime, Unix seconds/milliseconds, zero timestamps, malformed format warning captures. |
| **`tests/test_hashing.py`** | Streaming SHA-256 computation, `INTEGRITY VERIFIED` confirmation, intentional file tampering detection (`INTEGRITY MISMATCH`). |
| **`tests/test_browser_adapters.py`** | Synthetic Chrome, Edge, and Firefox profile parsing, SQLite structure validation, cookie encryption flag assertion. |
| **`tests/test_timeline_and_correlation.py`** | Chronological ordering, descending sequence validation, cross-browser domain convergence, Chain of Custody logging. |
| **`tests/test_reports.py`** | Compilation and validation of PDF (ReportLab), HTML, JSON, and CSV reports, document SHA-256 hashing. |
| **`tests/test_api_and_routes.py`** | Authentication flow, credential validation, case docket creation, and REST endpoints. |

---

## Safe Synthetic Demonstration Generator

The synthetic generator (`app/forensic/synthetic_generator.py`) generates fully functional, isolated Chromium and Firefox SQLite databases without touching personal browser data.

To generate a synthetic dataset from the command line:
```powershell
python -m flask --app run.py seed-demo
```
This seeds case `TF-DEMO-001` with realistic test browsing sessions, downloads, bookmarks, and cookies for validation and demonstration.
