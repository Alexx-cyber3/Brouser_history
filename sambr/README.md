# TraceFusion: Multi-Source Browser Evidence Analyzer

[![License](https://img.shields.io/badge/license-Forensic-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)]()
[![Integrity](https://img.shields.io/badge/Integrity-SHA--256%20Verified-brightgreen.svg)]()
[![Forensics](https://img.shields.io/badge/Standard-NIST%20SP%20800--86-purple.svg)]()

**TraceFusion** is a digital forensics workstation application engineered for cybersecurity incident responders, digital evidence examiners, and law enforcement analysts. It acquires, parses, normalizes, correlates, verifies, visualizes, and reports multi-source browser artifacts from **Google Chrome**, **Microsoft Edge**, and **Mozilla Firefox**.

Unlike static mockups or web prototypes, TraceFusion is a **fully functional, production-ready local forensic suite** built to process actual browser profile folders or forensic disk image extractions while maintaining evidentiary integrity and chain of custody.

---

## Key Forensic Capabilities

1. **Non-Destructive & Read-Only Acquisition**:
   - Zero modifications to original source evidence.
   - Pre-acquisition cryptographic SHA-256 hashing.
   - Bit-stream copying into an isolated case workspace (`cases/<case_id>/evidence/`).
   - SQLite read-only URI cloning to prevent database file modification or lock contention.

2. **Multi-Source Browser Support**:
   - **Google Chrome**: History (`visits`, `urls`), Downloads (`downloads`, `downloads_url_chains`), Cookies (metadata with protected credential marking), Bookmarks (JSON tree hierarchy), Sessions, Cache.
   - **Microsoft Edge**: Chromium-based profiles, Collections, and Edge-specific metadata.
   - **Mozilla Firefox**: Places (`moz_places`, `moz_historyvisits`, `moz_bookmarks`), Cookies (`moz_cookies`), Sessions (`sessionstore.jsonlz4`), Cache2.

3. **Rigorous Forensic Timestamp Normalization**:
   - Chromium WebKit microsecond epoch (since `1601-01-01 00:00:00 UTC`).
   - Mozilla PRTime microsecond epoch (since `1970-01-01 00:00:00 UTC`).
   - Unix seconds, milliseconds, and Windows FILETIME.
   - Preserves original raw representation alongside normalized UTC datetime.
   - Never discards malformed timestamps; logs warning advisories.

4. **Forensic Timeline Engine**:
   - Unified chronological event stream merging actions across all browsers.
   - Multi-attribute filtering (date range, browser platform, artifact type, domain, free-text keywords).
   - Server-side pagination for high-volume datasets.
   - Deep event detail drawer with raw metadata, provenance, and source database hashes.

5. **Cross-Source Evidence Correlation Engine**:
   - Discovers cross-browser visits to identical URLs and domains.
   - Temporal proximity clustering (e.g. website visit followed by download within configurable delta).
   - High-frequency burst detection.
   - Strictly objective forensic terminology: reports *"Temporally Correlated"* rather than claiming speculative causation.

6. **Defensible Chain of Custody & Audit Logging**:
   - Append-only custody ledger recording actions (`IMPORTED`, `HASHED`, `COPIED`, `PROCESSED`, `ANALYZED`, `EXPORTED`, `REPORT_GENERATED`, `VERIFIED`).
   - Contemporaneous investigator notes linked to cases and evidence.
   - Detailed application and user audit trails.

7. **Multi-Format Forensic Reporting**:
   - **PDF**: Formal legal dossier compiled with ReportLab, featuring title page, legal disclaimers, executive summary, hash verification tables, correlation extracts, and custody logs.
   - **HTML**: Standalone interactive report dossier for digital review.
   - **JSON**: Machine-readable structured schema for SIEM/SOAR ingestion.
   - **CSV**: Chronological spreadsheet export for timeline reconstruction.

8. **Modern Cyber-Forensic Workstation UI**:
   - Deep charcoal aesthetic (`#080C14`), glassmorphic panels, and neon blue/purple cyber accents.
   - Real-time Chart.js visual telemetry fed directly from database queries (no fake statistics).
   - Quick command palette (`Ctrl+K`) and keyboard shortcuts (`Ctrl+Shift+T`, `Ctrl+Shift+E`, `Ctrl+Shift+R`).

9. **Safe Synthetic Demonstration Dataset**:
   - Built-in synthetic generator producing realistic, fully compliant Chrome, Edge, and Firefox profiles with populated SQLite databases for safe testing and demonstrations.

---

## Architecture Overview

```
tracefusion/
├── app/
│   ├── browser_adapters/       # Modular browser parsers (Base, Chrome, Edge, Firefox)
│   ├── forensic/               # Core forensic engines (Timestamp, Hash, Evidence, Timeline, Correlation, Reports)
│   ├── models/                 # SQLAlchemy models (User, Case, Evidence, Artifact, Timeline, Custody, Audit)
│   ├── routes/                 # Blueprints (Auth, Dashboard, Cases, Evidence, Timeline, Search, Reports, API)
│   ├── static/                 # Custom cyber-forensic CSS and interactive ES6 scripts
│   ├── templates/              # Jinja2 forensic workstation templates
│   ├── config.py               # Application configuration and paths
│   └── extensions.py           # Database and login manager extensions
├── cases/                      # Case workspace containing forensic copies and generated reports
├── evidence/                   # Working evidence repository
├── tests/                      # Automated pytest forensic test suite
├── run.py                      # Application entrypoint & CLI utilities
└── requirements.txt            # Python dependencies
```

---

## Quick Start

### 1. Requirements
- Python 3.12 or 3.13 on Windows 10/11 (or Linux/macOS)
- Modern web browser (Chrome, Edge, Firefox)

### 2. Installation
```powershell
# Clone or navigate to the repository
cd tracefusion

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Seed Demo Evidence & Run
```powershell
# Generate synthetic multi-browser demonstration dataset
python -m flask --app run.py seed-demo

# Start the Forensic Workstation
python run.py
```
Open **`http://127.0.0.1:5000`** in your browser.

### 4. Default Clearance Credentials
| Role | Username | Password | Permissions |
|---|---|---|---|
| **Administrator** | `admin` | `forensic2026` | Full administrative & forensic access |
| **Investigator** | `investigator` | `investigator2026` | Case management, evidence processing, reports |

---

## Running the Automated Test Suite

TraceFusion includes a complete automated test suite verifying timestamp conversion across all browser epochs, streaming SHA-256 hashing, adapter extraction, timeline ordering, cross-browser correlation, and multi-format report generation:

```powershell
python -m pytest tests/ -v
```

---

## Documentation Index

- [Architecture Specification](ARCHITECTURE.md)
- [Installation Guide](INSTALLATION.md)
- [User & Examination Guide](USER_GUIDE.md)
- [Forensic Methodology & Legal Admissibility](FORENSIC_METHODOLOGY.md)
- [REST API Reference](API_DOCUMENTATION.md)
- [Testing & Quality Assurance](TESTING.md)
- [System Limitations & Boundary Conditions](LIMITATIONS.md)

---

## License & Legal Notice
TraceFusion is provided for authorized cybersecurity, digital forensics, and incident response examinations. Unauthorized access or extraction of protected evidence without appropriate legal authorization or consent is strictly prohibited.
