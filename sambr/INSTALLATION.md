# TraceFusion Installation & Deployment Guide

This guide details setting up TraceFusion on Windows 10/11 or modern Linux systems for authorized forensic investigations.

---

## 1. Prerequisites

- **Python 3.12 or 3.13** installed.
  - On Windows, ensure *"Add Python to PATH"* is checked during installation.
  - Verify installation:
    ```powershell
    python --version
    pip --version
    ```
- Modern Web Browser (Google Chrome, Microsoft Edge, Mozilla Firefox, or Brave).

---

## 2. Step-by-Step Installation

### Step 1: Navigate to Project Directory
```powershell
cd c:\path\to\tracefusion
```

### Step 2: Create a Dedicated Virtual Environment
```powershell
python -m venv venv
```

### Step 3: Activate the Virtual Environment
- **On Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
  *(If execution policies restrict script running, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

- **On Windows (CMD):**
  ```cmd
  venv\Scripts\activate.bat
  ```

- **On Linux / macOS:**
  ```bash
  source venv/bin/activate
  ```

### Step 4: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 5: Configure Environment
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Key configuration parameters in `.env`:
- `SECRET_KEY`: Random cryptographic secret key for session signing.
- `DATABASE_URL`: Path to SQLite instance database (default: `instance/tracefusion.db`).
- `EVIDENCE_WORKSPACE`: Directory for evidence copies (default: `evidence`).
- `CASES_WORKSPACE`: Directory for case workspaces (default: `cases`).
- `REPORTS_WORKSPACE`: Directory for compiled reports (default: `reports`).

---

## 3. Initializing Database & Demonstration Case

TraceFusion automatically creates database tables and default administrator accounts upon the first launch.

To preload a safe, synthetically populated multi-browser test case (`TF-DEMO-001`):
```powershell
python -m flask --app run.py seed-demo
```

---

## 4. Starting the Application

Launch the local forensic workstation:
```powershell
python run.py
```

The console will output:
```text
=================================================================
  TRACEFUSION - Multi-Source Browser Evidence Analyzer
  Forensic Workstation Console
=================================================================
  URL: http://127.0.0.1:5000
  Default Accounts:
    Admin:        admin        / forensic2026
    Investigator: investigator / investigator2026
=================================================================
```

Access **`http://127.0.0.1:5000`** in your browser.

---

## 5. Running Automated Verification Tests

Verify that all forensic parsers, hashing engines, timestamp normalizers, and report generators function correctly:
```powershell
python -m pytest tests/ -v
```
All tests should pass with code `0`.
