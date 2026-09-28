import tempfile
import shutil
from pathlib import Path

from app.extensions import db
from app.models.case import Case
from app.models.timeline import TimelineEvent
from app.models.custody import CustodyEvent
from app.forensic.synthetic_generator import SyntheticForensicEvidenceGenerator
from app.forensic.evidence_manager import EvidenceManager
from app.forensic.timeline_engine import TimelineEngine
from app.forensic.correlation_engine import CorrelationEngine

def test_evidence_ingestion_timeline_and_correlation(app):
    with app.app_context():
        case = Case(
            case_number="TF-E2E-001",
            title="End-to-End Forensic Investigation Test",
            investigator_name="Examiner Alpha",
            organization="Forensics Lab",
            status="OPEN"
        )
        db.session.add(case)
        db.session.commit()

        temp_dir = Path(tempfile.mkdtemp(prefix="tf_e2e_"))
        try:
            # Generate Chrome and Firefox synthetic datasets
            profiles = SyntheticForensicEvidenceGenerator.generate_all(temp_dir)

            res_chrome = EvidenceManager.import_and_process_profile(
                case=case,
                source_path=profiles["CHROME"],
                browser_type="CHROME",
                profile_name="Default",
                actor="Lead Examiner"
            )
            assert res_chrome["success"] is True
            assert res_chrome["artifacts_count"] > 0

            res_ff = EvidenceManager.import_and_process_profile(
                case=case,
                source_path=profiles["FIREFOX"],
                browser_type="FIREFOX",
                profile_name="default-release",
                actor="Lead Examiner"
            )
            assert res_ff["success"] is True

            # Verify timeline events exist
            timeline = TimelineEngine.query_timeline(case_id=case.id, page=1, per_page=100)
            assert timeline["total_items"] > 0

            # Verify Chronological descending order
            events = timeline["events"]
            for i in range(len(events) - 1):
                assert events[i]["timestamp_utc"] >= events[i+1]["timestamp_utc"]

            # Verify cross-browser correlation finds common domain (demo-corp.internal)
            correlations = CorrelationEngine.analyze_case_correlations(case.id)
            assert correlations["total_correlations"] > 0
            
            # Domain convergence
            converged = [c["domain"] for c in correlations["cross_browser_domains"]]
            assert "cloud-portal.demo-corp.internal" in converged or "malicious-paste.demo-leak.net" in converged

            # Verify Chain of Custody records
            custody_events = CustodyEvent.query.filter_by(case_id=case.id).all()
            assert len(custody_events) >= 4
            actions = [c.action for c in custody_events]
            assert "IMPORTED" in actions
            assert "HASHED" in actions
            assert "PROCESSED" in actions

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
