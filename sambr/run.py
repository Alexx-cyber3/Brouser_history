import sys
from app import create_app
from app.extensions import db
from app.models.case import Case
from app.models.user import User
from app.forensic.synthetic_generator import SyntheticForensicEvidenceGenerator
from app.forensic.evidence_manager import EvidenceManager
from app.config import Config

app = create_app()

@app.cli.command("seed-demo")
def seed_demo_command():
    """CLI helper to generate and ingest synthetic demo case."""
    with app.app_context():
        case = Case.query.filter_by(case_number="TF-DEMO-001").first()
        if not case:
            case = Case(
                case_number="TF-DEMO-001",
                title="Synthetic Cross-Browser Incident Analysis",
                investigator_name="Chief Forensic Examiner",
                organization="Digital Forensics & Cyber Intelligence Unit",
                description="Simulated investigation demonstrating multi-browser evidence normalization, SHA-256 verification, and correlation.",
                status="OPEN"
            )
            db.session.add(case)
            db.session.commit()
            print("Created case TF-DEMO-001")

        demo_dir = Config.EVIDENCE_DIR / "demo_synthetic_cli"
        profiles = SyntheticForensicEvidenceGenerator.generate_all(demo_dir)
        for browser, path in profiles.items():
            res = EvidenceManager.import_and_process_profile(
                case=case,
                source_path=path,
                browser_type=browser,
                profile_name="Synthetic Profile (DEMO)",
                actor="System Demo Seeder"
            )
            print(f"Ingested {browser}: {res['artifacts_count']} artifacts.")

if __name__ == "__main__":
    print("\n" + "="*65)
    print("  TRACEFUSION - Multi-Source Browser Evidence Analyzer")
    print("  Forensic Workstation Console")
    print("="*65)
    print("  URL: http://127.0.0.1:5000")
    print("  Default Accounts:")
    print("    Admin:        admin        / forensic2026")
    print("    Investigator: investigator / investigator2026")
    print("="*65 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=True)
