import tempfile
import shutil
from pathlib import Path

from app.extensions import db
from app.models.case import Case
from app.models.report import ReportRecord
from app.forensic.synthetic_generator import SyntheticForensicEvidenceGenerator
from app.forensic.evidence_manager import EvidenceManager
from app.forensic.report_engine import ReportEngine

def test_report_generation_all_formats(app):
    with app.app_context():
        case = Case(
            case_number="TF-REP-001",
            title="Report Generation Test Case",
            investigator_name="Examiner Bravo",
            organization="Digital Forensics Lab",
            status="OPEN"
        )
        db.session.add(case)
        db.session.commit()

        temp_dir = Path(tempfile.mkdtemp(prefix="tf_rep_"))
        try:
            # Generate and ingest small synthetic dataset
            profiles = SyntheticForensicEvidenceGenerator.generate_all(temp_dir)
            EvidenceManager.import_and_process_profile(case, profiles["CHROME"], "CHROME", "Default", "Examiner Bravo")

            # 1. Test PDF report
            pdf_rec = ReportEngine.generate_report(case, "pdf", "Examiner Bravo", "PDF Unit Test Notes")
            assert pdf_rec.id is not None
            assert Path(pdf_rec.file_path).exists()
            assert Path(pdf_rec.file_path).stat().st_size > 1000
            assert len(pdf_rec.file_hash) == 64

            # 2. Test HTML report
            html_rec = ReportEngine.generate_report(case, "html", "Examiner Bravo", "HTML Unit Test Notes")
            assert html_rec.id is not None
            assert Path(html_rec.file_path).exists()
            assert Path(html_rec.file_path).stat().st_size > 500

            # 3. Test JSON report
            json_rec = ReportEngine.generate_report(case, "json", "Examiner Bravo", "JSON Unit Test Notes")
            assert json_rec.id is not None
            assert Path(json_rec.file_path).exists()

            # 4. Test CSV report
            csv_rec = ReportEngine.generate_report(case, "csv", "Examiner Bravo", "CSV Unit Test Notes")
            assert csv_rec.id is not None
            assert Path(csv_rec.file_path).exists()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
