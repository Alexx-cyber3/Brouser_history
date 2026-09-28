import pytest
import tempfile
import shutil
from pathlib import Path

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User
from app.models.case import Case

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

@pytest.fixture
def app():
    # Setup temporary directory for test cases and evidence
    temp_dir = tempfile.mkdtemp(prefix="tracefusion_test_")
    TestConfig.BASE_DIR = Path(temp_dir)
    TestConfig.CASES_DIR = Path(temp_dir) / "cases"
    TestConfig.EVIDENCE_DIR = Path(temp_dir) / "evidence"
    TestConfig.REPORTS_DIR = Path(temp_dir) / "reports"
    TestConfig.CASES_DIR.mkdir(parents=True, exist_ok=True)
    TestConfig.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    TestConfig.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        # Seed test admin if needed
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@test.local",
                full_name="Test Administrator",
                role="ADMIN"
            )
            admin.set_password("testpass123")
            db.session.add(admin)
            db.session.commit()
        yield app

        db.session.remove()
        db.drop_all()

    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client, app):
    """Client authenticated as the test administrator."""
    client.post("/login", data={"username": "admin", "password": "forensic2026"}, follow_redirects=True)
    return client

@pytest.fixture
def sample_case(app):
    with app.app_context():
        case = Case(
            case_number="TF-TEST-001",
            title="Unit Test Investigation Case",
            investigator_name="Test Examiner",
            organization="Digital Forensics Test Lab",
            status="OPEN"
        )
        db.session.add(case)
        db.session.commit()
        return Case.query.get(case.id)
