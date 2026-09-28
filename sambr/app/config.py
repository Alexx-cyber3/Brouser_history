import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "tracefusion-dev-secret-key-2026")
    APPLICATION_NAME = "TraceFusion"
    APPLICATION_VERSION = "1.0.0-FORENSIC"

    # Workspaces
    BASE_DIR = BASE_DIR
    INSTANCE_DIR = BASE_DIR / "instance"
    EVIDENCE_DIR = BASE_DIR / os.environ.get("EVIDENCE_WORKSPACE", "evidence")
    CASES_DIR = BASE_DIR / os.environ.get("CASES_WORKSPACE", "cases")
    REPORTS_DIR = BASE_DIR / os.environ.get("REPORTS_WORKSPACE", "reports")
    LOGS_DIR = BASE_DIR / os.environ.get("LOGS_WORKSPACE", "logs")

    # Ensure directories exist
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Database
    db_env = os.environ.get("DATABASE_URL")
    if not db_env or "instance/tracefusion.db" in db_env or "sqlite:///" in db_env:
        abs_db_path = (INSTANCE_DIR / "tracefusion.db").resolve().as_posix()
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{abs_db_path}"
    else:
        SQLALCHEMY_DATABASE_URI = db_env
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security & limits
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 100 * 1024 * 1024)) # 100MB
    TIMEZONE = os.environ.get("TIMEZONE", "UTC")
    DEFAULT_REPORT_FORMAT = os.environ.get("DEFAULT_REPORT_FORMAT", "pdf")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Browser Detection Default Paths on Windows
    LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
    APPDATA = os.environ.get("APPDATA", "")

    CHROME_DEFAULT_PATH = Path(LOCALAPPDATA) / "Google" / "Chrome" / "User Data" if LOCALAPPDATA else None
    EDGE_DEFAULT_PATH = Path(LOCALAPPDATA) / "Microsoft" / "Edge" / "User Data" if LOCALAPPDATA else None
    FIREFOX_DEFAULT_PATH = Path(APPDATA) / "Mozilla" / "Firefox" / "Profiles" if APPDATA else None
