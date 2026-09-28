# TraceFusion REST API Reference

TraceFusion exposes a standardized REST-style API for integration with forensic scripts, SOAR pipelines, and external workstations.

All API responses return JSON with the standard schema:
```json
{
  "success": true,
  "data": {},
  "message": "",
  "errors": []
}
```

---

## Endpoints

### 1. Case Management

#### `GET /api/cases`
Returns a list of all registered forensic cases.
- **Headers**: Session Cookie (Authenticated)
- **Response**: Array of Case objects with artifact and timeline counts.

#### `POST /api/cases`
Create a new forensic case docket.
- **Request Body**:
  ```json
  {
    "case_number": "TF-2026-0002",
    "title": "Incident Investigation B",
    "investigator_name": "Examiner Doe",
    "organization": "DFIR Unit",
    "description": "Scope details..."
  }
  ```
- **Response**: Created case record with status code `201`.

#### `GET /api/cases/<case_id>`
Returns full metadata for the specified case.

---

### 2. Timeline & Artifact Queries

#### `GET /api/cases/<case_id>/timeline`
Paginated chronological query across all browsers.
- **Query Parameters**:
  - `page` (int, default 1)
  - `per_page` (int, default 50)
  - `sort` (`asc` or `desc`, default `desc`)
  - `browser` (`ALL`, `CHROME`, `EDGE`, `FIREFOX`)
  - `type` (`ALL`, `HISTORY`, `DOWNLOAD`, `COOKIE`, `BOOKMARK`, `SESSION`, `CACHE`)
  - `domain` (string filter)
  - `q` (free-text search keyword)
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "total_items": 150,
      "page": 1,
      "per_page": 50,
      "total_pages": 3,
      "events": [...]
    }
  }
  ```

#### `GET /api/cases/<case_id>/artifacts`
Query normalized artifacts with pagination.
- **Query Parameters**: `page`, `per_page`, `type`.

---

### 3. Cross-Source Correlations

#### `GET /api/cases/<case_id>/correlations`
Executes correlation algorithms on the case and returns:
- `cross_browser_domains`: Convergence across multiple browser platforms.
- `cross_browser_urls`: Exact identical URLs visited in different engines.
- `visit_download_sequences`: Temporally correlated visit-to-download events.
- `activity_bursts`: Rapid action clusters ($\ge 10$ actions within 60 seconds).

---

### 4. Integrity Verification

#### `POST /api/evidence/file/<file_id>/verify`
Re-hashes the underlying file and compares against the baseline SHA-256 hash.
- **Response**:
  ```json
  {
    "success": true,
    "data": {
      "status": "INTEGRITY VERIFIED",
      "is_valid": true,
      "expected_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "calculated_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "verified_at": "2026-09-23T14:00:00Z"
    }
  }
  ```

---

### 5. Automated Reporting

#### `POST /api/cases/<case_id>/reports`
Compiles an evidentiary report on the server.
- **Request Body**:
  ```json
  {
    "format": "pdf", // "pdf", "html", "json", "csv"
    "notes": "Examiner findings summary..."
  }
  ```
- **Response**: ReportRecord object with generated file path and document SHA-256 hash.
