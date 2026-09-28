# TraceFusion Forensic Methodology & Legal Admissibility

## Standard Compliance & Frameworks

TraceFusion is designed to adhere to international standards governing digital forensic examinations:
- **ISO/IEC 27037**: Guidelines for identification, collection, acquisition, and preservation of digital evidence.
- **NIST SP 800-86**: Guide to Integrating Forensic Techniques into Incident Response.
- **Federal Rules of Evidence (FRE) Rule 901 & 902**: Self-authenticating electronic records and certified data copies.

---

## 1. Principles of Evidence Preservation

### Non-Destructive Ingestion
- TraceFusion opens all source evidence files with read-only file system permissions (`rb`).
- Source directories and original files are never altered, touched, renamed, or modified.

### Baseline Hashing
- Prior to copying, a full SHA-256 cryptographic hash is calculated using 1MB chunked streams.
- The evidence is copied to the case workspace (`cases/<case_number>/evidence/source_<id>/`).
- A post-copy SHA-256 verification confirms 100% bit-stream parity before any parser parses the files.

### Working Exclusively on Forensic Copies
- All browser adapters operate solely on the verified forensic copies in the case workspace.
- The original source remains untouched for independent verification and defense expert review.

---

## 2. Distinction of Evidentiary Classifications

In strict compliance with evidentiary standards, TraceFusion distinguishes between four categories of information:

| Classification | Definition | Example in TraceFusion |
|---|---|---|
| **DIRECT** | Direct, raw observed evidence stored natively inside the browser database. | History URL record, visit timestamp, cookie expiration value. |
| **DERIVED** | Formatted or normalized artifacts derived through deterministic algorithm. | Unified UTC timeline event derived from a Chrome microsecond timestamp. |
| **CORRELATED** | Observed spatial or temporal convergence across independent sources. | Identification that Domain X was visited in Chrome and a download from Domain X occurred in Edge within 2 minutes. |
| **NOTES** | Contemporaneous investigator notes or analytical opinions. | Examiner notes regarding case hypotheses or search authorization boundaries. |

---

## 3. Absence of Speculative Causation

In forensic timelines and correlation outputs, TraceFusion enforces objective evidentiary descriptions:
- **Acceptable Terminology**: *"Temporally correlated"*, *"Observed cross-platform convergence"*, *"Associated activity sequence"*.
- **Prohibited Terminology**: *"Caused by"*, *"Resulted in"*, *"Driven by"*.

Examiners are reminded that temporal proximity does not prove technical causation (e.g., a background automated sync might coincide with a user-initiated visit).

---

## 4. Protected Credential Handling

In alignment with cybersecurity legal guidelines and privacy principles:
- TraceFusion parses cookie headers (`host_key`, `name`, `path`, `expiry`, `security flags`).
- For encrypted values protected by the Windows Data Protection API (DPAPI) or local encryption mechanisms, TraceFusion records the protection status as **`Encrypted/Protected`** rather than attempting to bypass operating-system protections or extract plaintext authentication tokens.

---

## 5. Append-Only Chain of Custody

Chain of custody records are append-only. Every critical lifecycle action creates an un-editable audit event:
- **`IMPORTED`**: Records original source path, actor, and import timestamp.
- **`HASHED`**: Records initial SHA-256 baseline.
- **`COPIED`**: Records replication into controlled case folder.
- **`PROCESSED`**: Records parser version and extracted artifact counts.
- **`VERIFIED`**: Records re-verification results (`INTEGRITY VERIFIED` / `INTEGRITY MISMATCH`).
- **`REPORT_GENERATED`**: Records report compilation and generated document SHA-256 hash.
