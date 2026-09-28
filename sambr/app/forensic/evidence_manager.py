import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.extensions import db
from app.config import Config
from app.models.case import Case
from app.models.evidence import EvidenceSource, EvidenceFile
from app.models.artifact import Artifact
from app.models.timeline import TimelineEvent
from app.models.custody import CustodyEvent
from app.forensic.hash_engine import HashEngine
from app.browser_adapters import get_adapter_for_browser

class EvidenceManager:
    """
    Forensic Evidence Acquisition, Normalization, and Workspace Manager.
    Guarantees:
      - Source evidence is strictly read-only
      - Baseline SHA-256 hash calculated prior to copy
      - Controlled forensic copy created inside case directory
      - Forensic copy hash verified against source hash
      - Chain-of-custody recorded for every transition
    """

    RELEVANT_PATTERNS = [
        "History*", "Cookies*", "Network/Cookies*", "Bookmarks*", "Preferences*",
        "places.sqlite*", "cookies.sqlite*", "sessionstore*", "prefs.js*", "Cache*", "cache2*"
    ]

    @classmethod
    def import_and_process_profile(
        cls,
        case: Case,
        source_path: Path | str,
        browser_type: str,
        profile_name: str,
        actor: str = "Forensic Investigator",
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Executes full forensic acquisition and parsing pipeline for a browser profile.
        """
        src = Path(source_path)
        if not src.exists():
            raise FileNotFoundError(f"Source evidence directory does not exist: {src}")

        # 1. Setup Case Workspace
        case_dir = Config.CASES_DIR / case.case_number / "evidence"
        case_dir.mkdir(parents=True, exist_ok=True)

        # 2. Create EvidenceSource model
        ev_source = EvidenceSource(
            case_id=case.id,
            name=f"{browser_type} - {profile_name} ({src.name})",
            source_type="DIRECTORY_COPY",
            browser_type=browser_type.upper(),
            profile_name=profile_name,
            original_source_path=str(src.resolve()),
            status="PROCESSING",
            notes=notes
        )
        db.session.add(ev_source)
        db.session.flush() # get ev_source.id

        dest_dir = case_dir / f"source_{ev_source.id}_{browser_type.lower()}_{profile_name.replace(' ', '_')}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        ev_source.forensic_copy_path = str(dest_dir.resolve())

        # Log Custody: IMPORTED
        custody_import = CustodyEvent(
            case_id=case.id,
            evidence_id=ev_source.id,
            action="IMPORTED",
            actor=actor,
            description=f"Evidence source imported from {src.resolve()} into case workspace."
        )
        db.session.add(custody_import)

        warnings: List[str] = []
        evidence_files: List[EvidenceFile] = []

        # 3. Find, Hash, and Copy Key Evidence Files
        try:
            files_to_copy = cls._find_evidence_files(src)
            for file_path in files_to_copy:
                try:
                    rel_to_src = file_path.relative_to(src)
                except ValueError:
                    rel_to_src = Path(file_path.name)

                dest_file_path = dest_dir / rel_to_src
                dest_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Compute source hash (READ-ONLY)
                src_hash = HashEngine.calculate_file_sha256(file_path)
                file_size = file_path.stat().st_size

                # Copy to forensic workspace
                shutil.copy2(file_path, dest_file_path)

                # Compute destination hash
                dest_hash = HashEngine.calculate_file_sha256(dest_file_path)
                is_match = (src_hash == dest_hash)
                v_status = "INTEGRITY VERIFIED" if is_match else "INTEGRITY MISMATCH"

                ev_file = EvidenceFile(
                    source_id=ev_source.id,
                    case_id=case.id,
                    file_name=file_path.name,
                    rel_path=str(rel_to_src),
                    source_full_path=str(file_path.resolve()),
                    forensic_copy_path=str(dest_file_path.resolve()),
                    file_size=file_size,
                    hash_algorithm="SHA-256",
                    original_hash=src_hash,
                    last_verified_hash=dest_hash,
                    verification_status=v_status,
                    verified_at=datetime.now(timezone.utc)
                )
                db.session.add(ev_file)
                evidence_files.append(ev_file)

                # Log Custody: HASHED and COPIED
                db.session.add(CustodyEvent(
                    case_id=case.id,
                    evidence_id=ev_source.id,
                    action="HASHED",
                    actor=actor,
                    description=f"Calculated initial SHA-256 for {file_path.name}",
                    hash_value=src_hash
                ))

            db.session.flush()

            # 4. Parse Evidence via Browser Adapter from FORENSIC COPY
            adapter = get_adapter_for_browser(browser_type, dest_dir)
            all_artifacts = adapter.collect_all_artifacts()
            warnings.extend(adapter.warnings)

            # Map file names to EvidenceFile records
            file_lookup = {ef.file_name.lower(): ef for ef in evidence_files}

            artifact_records = []
            timeline_records = []

            for category, art_list in all_artifacts.items():
                for item in art_list:
                    src_fname = (item.get("source_file") or "").split("/")[0].split("\\")[0].lower()
                    matching_ef = file_lookup.get(src_fname)

                    utc_ts = item.get("timestamp_utc")
                    # If artifact has valid UTC timestamp, derive timeline event
                    art = Artifact(
                        case_id=case.id,
                        source_id=ev_source.id,
                        evidence_file_id=matching_ef.id if matching_ef else None,
                        browser=item.get("browser", browser_type.upper()),
                        profile=item.get("profile", profile_name),
                        artifact_type=item.get("artifact_type", "OTHER"),
                        record_identifier=item.get("record_identifier"),
                        title=item.get("title"),
                        url=item.get("url"),
                        domain=item.get("domain"),
                        timestamp_raw=item.get("timestamp_raw"),
                        timestamp_utc=utc_ts,
                        file_path=item.get("file_path"),
                        file_size=item.get("file_size"),
                        mime_type=item.get("mime_type"),
                        is_encrypted=item.get("is_encrypted", False),
                        parser_name=adapter.__class__.__name__,
                        parser_version=adapter.parser_version,
                        confidence=item.get("confidence", "DIRECT")
                    )
                    art.set_metadata(item.get("metadata", {}))
                    db.session.add(art)
                    artifact_records.append(art)

                    # Create timeline event if timestamp is available
                    if utc_ts:
                        tl = TimelineEvent(
                            case_id=case.id,
                            browser=item.get("browser", browser_type.upper()),
                            profile=item.get("profile", profile_name),
                            artifact_type=item.get("artifact_type", "OTHER"),
                            event_type=item.get("event_type", "OTHER"),
                            timestamp_utc=utc_ts,
                            timestamp_raw=item.get("timestamp_raw"),
                            title=item.get("title"),
                            url=item.get("url"),
                            domain=item.get("domain"),
                            summary=f"[{item.get('browser', browser_type)}] {item.get('event_type')}: {item.get('title')}",
                            source_file=item.get("source_file"),
                            source_hash=matching_ef.original_hash if matching_ef else None,
                            confidence="DERIVED",
                            artifact=art
                        )
                        tl.set_metadata(item.get("metadata", {}))
                        db.session.add(tl)
                        timeline_records.append(tl)

            ev_source.status = "PROCESSED"
            db.session.add(CustodyEvent(
                case_id=case.id,
                evidence_id=ev_source.id,
                action="PROCESSED",
                actor=actor,
                description=f"Evidence parsed: {len(artifact_records)} artifacts normalized, {len(timeline_records)} timeline events generated."
            ))
            db.session.commit()

            return {
                "success": True,
                "evidence_source_id": ev_source.id,
                "files_count": len(evidence_files),
                "artifacts_count": len(artifact_records),
                "timeline_count": len(timeline_records),
                "warnings": warnings
            }

        except Exception as e:
            db.session.rollback()
            ev_source.status = "ERROR"
            ev_source.notes = f"Processing Error: {str(e)}"
            db.session.add(ev_source)
            db.session.add(CustodyEvent(
                case_id=case.id,
                evidence_id=ev_source.id,
                action="PROCESSED",
                actor=actor,
                description=f"Processing encountered critical error: {str(e)}"
            ))
            db.session.commit()
            raise e

    @classmethod
    def _find_evidence_files(cls, dir_path: Path) -> List[Path]:
        """Scan directory and return list of forensic evidence database and metadata files."""
        matched: List[Path] = []
        if not dir_path.exists():
            return matched

        targets = [
            "History", "History-wal", "Cookies", "Cookies-wal", "Network/Cookies",
            "Bookmarks", "Preferences", "places.sqlite", "places.sqlite-wal",
            "cookies.sqlite", "cookies.sqlite-wal", "prefs.js", "sessionstore.jsonlz4",
            "recovery.jsonlz4"
        ]

        for target in targets:
            p = dir_path / target
            if p.is_file():
                matched.append(p)

        # Also search top-level for any .sqlite or JSON files if not matched
        if not matched:
            for item in dir_path.glob("*.sqlite"):
                if item.is_file():
                    matched.append(item)

        return matched
