# TraceFusion User & Examination Guide

## 1. Authentication & Role Clearances

Upon loading `http://127.0.0.1:5000`, investigators are greeted with the secure workstation login screen.

### Default Accounts
| Username | Password | Role | Description |
|---|---|---|---|
| `admin` | `forensic2026` | `ADMIN` | Chief Forensic Examiner. Full access to create cases, ingest evidence, re-verify hashes, and audit system logs. |
| `investigator` | `investigator2026` | `INVESTIGATOR` | Lead Cyber Investigator. Full investigative privileges. |

---

## 2. Case Registry & Management

Every forensic examination must occur within the scope of an official case docket to preserve chain of custody.

1. Navigate to **Cases Registry** via the left sidebar.
2. Click **"Open New Case Docket"**.
3. Fill in:
   - **Case Number** (e.g. `TF-2026-0001` or agency CAD number)
   - **Case Title**
   - **Lead Investigator**
   - **Organization**
   - **Preliminary Scope Description**
4. Once created, the case automatically becomes your **Active Case** (indicated by the pulsing green indicator in the top bar).

---

## 3. Evidence Ingestion Workflow (The 9-Step Wizard)

To acquire evidence:
1. In the top bar or case overview, click **"Acquire Evidence"**.
2. **Select Mode**:
   - **Automatically Detected System Profiles**: TraceFusion automatically scans Windows default paths for installed Chrome, Edge, and Firefox profiles.
   - **Manual Evidence Directory / Forensic Image**: Enter an absolute path to an extracted browser folder (e.g. from an E01/DD disk image mount).
3. **Select Profile**: Pick the specific profile to process (e.g. `Default`, `Profile 1`).
4. **Click "Compute Hashes & Process Evidence"**:
   - TraceFusion opens the evidence in read-only mode.
   - Computes baseline SHA-256 hashes of all database files (`History`, `Cookies`, `places.sqlite`, etc.).
   - Replicates files into `cases/<case_number>/evidence/`.
   - Ingests and normalizes all artifacts.
   - Records an immutable `IMPORTED` and `HASHED` entry in the Chain of Custody.

---

## 4. Inspecting Normalized Artifacts

Navigate to **Artifacts Inventory** (`/cases/<id>/artifacts`) to view normalized records categorized into:
- **History**: Visited URLs, page titles, visit counts, visit duration, transition types.
- **Downloads**: Target file paths, file sizes, MIME types, referrers, download start/end timestamps.
- **Cookies**: Host domains, cookie names, creation timestamps, expiry dates, security flags (`HttpOnly`, `Secure`). Note: Protected credentials are explicitly marked `Encrypted/Protected`.
- **Bookmarks**: Bookmark titles, URLs, folder hierarchy trees.
- **Sessions & Cache**: Open tabs and cache block metadata.

Clicking on any record opens the **Slide-Over Forensic Inspector** showing raw parser metadata, database provenance, and hash values.

---

## 5. Unified Forensic Timeline Analysis

Navigate to **Forensic Timeline** (`/cases/<id>/timeline` or shortcut `Ctrl+Shift+T`):
- Filter by **Browser Platform** (Chrome, Edge, Firefox).
- Filter by **Artifact Category**.
- Filter by **Specific Target Domain** (with autocomplete).
- Search URLs and page titles using **Free-Text Search**.
- Toggle chronological sorting (**Newest First** vs **Oldest First**).
- Click any timeline event card to inspect raw fields in the detail drawer.

---

## 6. Cross-Source Evidence Correlation

Navigate to **Cross-Correlation** (`/cases/<id>/correlation`):
- **Cross-Browser Domain Convergence**: Lists domains visited on two or more distinct browser platforms.
- **Temporally Correlated Visit-to-Download Chains**: Maps instances where an investigator-of-interest visited a domain and subsequently downloaded a file from that domain within a 10-minute window.
- **Activity Bursts**: Highlights clusters where 10 or more browser actions occurred within a 60-second window.

---

## 7. Re-Verifying Hash Integrity

To confirm that evidence files have not been altered:
1. Navigate to **Evidence Sources** (`/cases/<id>/evidence`).
2. Click **"Verify Hash"** on any file to re-calculate its live SHA-256 and compare it with the baseline.
3. Or click **"Re-Verify All Hashes"** to execute a batch verification across all evidence databases.
4. An integrity confirmation (`✓ VERIFIED` or `⚠ MISMATCH`) is logged into the append-only Chain of Custody.

---

## 8. Compiling Forensic Reports

Navigate to **Forensic Reports** (`/cases/<id>/reports` or shortcut `Ctrl+Shift+R`):
1. Select output format:
   - **Formal Legal PDF Dossier**
   - **Interactive Forensic HTML Dossier**
   - **Machine-Readable Structured JSON**
   - **Chronological Timeline CSV**
2. Enter contemporaneous conclusion notes.
3. Click **"Compile Forensic Report"**.
4. Download the generated report. Each report is automatically hashed with SHA-256 upon compilation.

---

## 9. Keyboard Shortcuts & Command Palette

| Shortcut | Action |
|---|---|
| `Ctrl + K` | Open Universal Command Palette |
| `Ctrl + Shift + T` | Jump directly to Forensic Timeline |
| `Ctrl + Shift + E` | Jump directly to Evidence Inventory |
| `Ctrl + Shift + R` | Jump directly to Report Generator |
| `Escape` | Dismiss open drawers and modals |
