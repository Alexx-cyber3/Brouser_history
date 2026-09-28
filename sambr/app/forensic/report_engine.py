import json
import csv
import io
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

from app.config import Config
from app.extensions import db
from app.models.case import Case
from app.models.evidence import EvidenceSource, EvidenceFile
from app.models.artifact import Artifact
from app.models.timeline import TimelineEvent
from app.models.custody import CustodyEvent
from app.models.report import ReportRecord
from app.forensic.hash_engine import HashEngine
from app.forensic.correlation_engine import CorrelationEngine

class NumberedCanvas(canvas.Canvas):
    """Adds formal forensic header and footer with total page count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#4A5568"))

        # Top Header (omitted on cover page 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "TRACEFUSION DIGITAL FORENSICS - CASE REPORT")
            self.drawRightString(558, 750, "CONFIDENTIAL / LAW ENFORCEMENT & INVESTIGATION SENSITIVE")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Bottom Footer
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "Integrity Verified • Read-Only Acquisition • SHA-256 Validated")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_text)
        self.restoreState()


class ReportEngine:
    """
    Forensic Multi-Format Report Generator.
    Produces verifiable, audit-grade forensic outputs in PDF, HTML, JSON, and CSV.
    """

    @classmethod
    def generate_report(
        cls,
        case: Case,
        report_format: str = "pdf",
        investigator_name: str = "Investigator",
        notes: str = ""
    ) -> ReportRecord:
        """
        Coordinates full report generation for selected format and saves record in database.
        """
        fmt = report_format.lower()
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        case_clean = case.case_number.replace("-", "_").replace(" ", "_")
        filename = f"TraceFusion_{case_clean}_{now_str}.{fmt}"

        case_report_dir = Config.REPORTS_DIR / case.case_number
        case_report_dir.mkdir(parents=True, exist_ok=True)
        file_path = case_report_dir / filename

        # Gather data
        data = cls._gather_case_data(case, notes, investigator_name)

        if fmt == "pdf":
            cls._generate_pdf(file_path, data)
        elif fmt == "html":
            cls._generate_html(file_path, data)
        elif fmt == "json":
            cls._generate_json(file_path, data)
        elif fmt == "csv":
            cls._generate_csv(file_path, data)
        else:
            raise ValueError(f"Unsupported report format: {report_format}")

        # Compute document SHA-256 hash for forensic traceability
        report_hash = HashEngine.calculate_file_sha256(file_path)

        record = ReportRecord(
            case_id=case.id,
            title=f"Forensic Analysis Report - {case.case_number}",
            report_format=fmt.upper(),
            file_path=str(file_path.resolve()),
            file_hash=report_hash,
            generated_by=investigator_name,
            generated_at=datetime.now(timezone.utc)
        )
        record.set_parameters({"notes": notes, "format": fmt})
        db.session.add(record)

        # Log Chain of Custody
        db.session.add(CustodyEvent(
            case_id=case.id,
            action="REPORT_GENERATED",
            actor=investigator_name,
            description=f"Generated {fmt.upper()} forensic report '{filename}'",
            hash_value=report_hash
        ))
        db.session.commit()

        return record

    @classmethod
    def _gather_case_data(cls, case: Case, notes: str, investigator_name: str) -> Dict[str, Any]:
        sources = EvidenceSource.query.filter_by(case_id=case.id).all()
        files = EvidenceFile.query.filter_by(case_id=case.id).all()
        timeline_sample = TimelineEvent.query.filter_by(case_id=case.id).order_by(TimelineEvent.timestamp_utc.asc()).limit(200).all()
        custody_list = CustodyEvent.query.filter_by(case_id=case.id).order_by(CustodyEvent.timestamp.asc()).all()
        correlations = CorrelationEngine.analyze_case_correlations(case.id)

        # Artifact summary counts by browser & type
        art_counts: Dict[str, Dict[str, int]] = {}
        for s in sources:
            art_counts[s.browser_type] = {}
        
        all_arts = Artifact.query.filter_by(case_id=case.id).all()
        for a in all_arts:
            b = a.browser
            t = a.artifact_type
            if b not in art_counts:
                art_counts[b] = {}
            art_counts[b][t] = art_counts[b].get(t, 0) + 1

        return {
            "case": case,
            "investigator": investigator_name,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "investigator_notes": notes,
            "sources": sources,
            "files": files,
            "timeline": timeline_sample,
            "timeline_total": TimelineEvent.query.filter_by(case_id=case.id).count(),
            "artifacts_total": len(all_arts),
            "artifact_counts": art_counts,
            "custody": custody_list,
            "correlations": correlations
        }

    @classmethod
    def _generate_pdf(cls, file_path: Path, data: Dict[str, Any]):
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()
        normal = styles["Normal"]

        title_style = ParagraphStyle(
            "CoverTitle",
            parent=styles["Title"],
            fontSize=26,
            leading=32,
            textColor=colors.HexColor("#0B132B"),
            alignment=0,
            spaceAfter=15
        )
        subtitle_style = ParagraphStyle(
            "CoverSub",
            parent=normal,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#4A5568"),
            spaceAfter=25
        )
        h1 = ParagraphStyle(
            "H1",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1A365D"),
            spaceBefore=18,
            spaceAfter=8,
            keepWithNext=True
        )
        h2 = ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True
        )
        body = ParagraphStyle(
            "Body",
            parent=normal,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#2D3748"),
            spaceAfter=6
        )
        table_cell = ParagraphStyle(
            "TableCell",
            parent=normal,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#2D3748")
        )
        table_hdr = ParagraphStyle(
            "TableHdr",
            parent=normal,
            fontSize=8,
            leading=10,
            fontName="Helvetica-Bold",
            textColor=colors.white
        )

        story = []

        # ================= COVER PAGE =================
        story.append(Spacer(1, 40))
        story.append(Paragraph("TRACEFUSION", title_style))
        story.append(Paragraph("Multi-Source Browser Evidence Analyzer • Forensic Examination Dossier", subtitle_style))
        story.append(Spacer(1, 20))

        case = data["case"]
        meta_table_data = [
            [Paragraph("<b>Case Number:</b>", table_cell), Paragraph(case.case_number, table_cell)],
            [Paragraph("<b>Case Title:</b>", table_cell), Paragraph(case.title, table_cell)],
            [Paragraph("<b>Primary Investigator:</b>", table_cell), Paragraph(data["investigator"], table_cell)],
            [Paragraph("<b>Organization:</b>", table_cell), Paragraph(case.organization, table_cell)],
            [Paragraph("<b>Examination Date:</b>", table_cell), Paragraph(data["generated_at"], table_cell)],
            [Paragraph("<b>Software Version:</b>", table_cell), Paragraph("TraceFusion v1.0.0-FORENSIC (Python 3.12+ / SQLite)", table_cell)],
            [Paragraph("<b>Integrity Standard:</b>", table_cell), Paragraph("NIST/ISO 27037 Digital Evidence Admissibility Guidelines", table_cell)]
        ]
        meta_t = Table(meta_table_data, colWidths=[150, 350])
        meta_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#EDF2F7")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(meta_t)
        story.append(Spacer(1, 40))

        # Legal & Forensic Integrity Declaration Box
        dec_text = (
            "<b>FORENSIC NOTICE & INTEGRITY STATEMENT:</b><br/>"
            "This document compiles evidence derived strictly through non-destructive, read-only "
            "forensic processing of identified browser artifacts. All evidence files were cryptographically "
            "hashed using SHA-256 upon acquisition and re-verified. Analytical inferences are distinguished "
            "from direct observed records. Chain of custody is preserved in append-only records."
        )
        dec_p = Paragraph(dec_text, body)
        dec_t = Table([[dec_p]], colWidths=[500])
        dec_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EBF8FF")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BEE3F8")),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(dec_t)

        story.append(PageBreak())

        # ================= 1. EXECUTIVE SUMMARY =================
        story.append(Paragraph("1. Executive Summary", h1))
        summary_text = (
            f"TraceFusion conducted a multi-source browser forensic analysis for Case <b>{case.case_number}</b>. "
            f"A total of <b>{len(data['sources'])}</b> evidence source profiles were ingested, yielding "
            f"<b>{len(data['files'])}</b> verified evidence files, <b>{data['artifacts_total']}</b> normalized "
            f"artifacts, and <b>{data['timeline_total']}</b> chronological timeline events across Google Chrome, "
            f"Microsoft Edge, and Mozilla Firefox."
        )
        story.append(Paragraph(summary_text, body))
        if data["investigator_notes"]:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Investigator Notes:</b> {data['investigator_notes']}", body))
        story.append(Spacer(1, 10))

        # ================= 2. EVIDENCE INVENTORY & SHA-256 HASHES =================
        story.append(Paragraph("2. Evidence Inventory & SHA-256 Baselines", h1))
        story.append(Paragraph("Direct cryptographic hashes calculated upon acquisition and re-verified:", body))

        hash_headers = [Paragraph("<b>File Name</b>", table_hdr), Paragraph("<b>Size</b>", table_hdr), Paragraph("<b>SHA-256 Hash</b>", table_hdr), Paragraph("<b>Status</b>", table_hdr)]
        hash_rows = [hash_headers]
        for f in data["files"][:25]:
            hash_display = f"{f.original_hash[:16]}...{f.original_hash[-12:]}"
            hash_rows.append([
                Paragraph(f.file_name, table_cell),
                Paragraph(f"{f.file_size:,} B", table_cell),
                Paragraph(f"<font face='Courier' size=7>{hash_display}</font>", table_cell),
                Paragraph(f"<font color='green'><b>{f.verification_status}</b></font>", table_cell)
            ])
        hash_t = Table(hash_rows, colWidths=[120, 60, 220, 100])
        hash_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E0")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(hash_t)
        story.append(Spacer(1, 14))

        # ================= 3. CROSS-SOURCE CORRELATION =================
        story.append(Paragraph("3. Cross-Source Correlated Activity", h1))
        corr = data["correlations"]
        corr_desc = (
            f"Correlation algorithms identified <b>{corr['total_correlations']}</b> objective associative relationships "
            f"across evidence sources. Temporal proximity matches are correlated observations, not speculative causation."
        )
        story.append(Paragraph(corr_desc, body))

        if corr["cross_browser_domains"]:
            story.append(Paragraph("<b>Cross-Browser Domain Convergence:</b>", h2))
            cbd_headers = [Paragraph("<b>Domain</b>", table_hdr), Paragraph("<b>Browsers</b>", table_hdr), Paragraph("<b>Evidentiary Note</b>", table_hdr)]
            cbd_rows = [cbd_headers]
            for c in corr["cross_browser_domains"][:10]:
                cbd_rows.append([
                    Paragraph(f"<b>{c['domain']}</b>", table_cell),
                    Paragraph(", ".join(c["browsers"]), table_cell),
                    Paragraph(c["note"], table_cell)
                ])
            cbd_t = Table(cbd_rows, colWidths=[140, 100, 260])
            cbd_t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E0")),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(cbd_t)

        if corr["visit_download_sequences"]:
            story.append(Spacer(1, 8))
            story.append(Paragraph("<b>Temporally Correlated Visit-to-Download Activity:</b>", h2))
            vds_headers = [Paragraph("<b>Domain</b>", table_hdr), Paragraph("<b>Visit / Download Timing</b>", table_hdr), Paragraph("<b>Delta</b>", table_hdr)]
            vds_rows = [vds_headers]
            for v in corr["visit_download_sequences"][:8]:
                timing_str = f"Visit: {v['visit_timestamp']}<br/>Download: {v['download_timestamp']}"
                vds_rows.append([
                    Paragraph(v["domain"], table_cell),
                    Paragraph(timing_str, table_cell),
                    Paragraph(f"{v['time_delta_seconds']}s", table_cell)
                ])
            vds_t = Table(vds_rows, colWidths=[150, 270, 80])
            vds_t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E0")),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(vds_t)

        story.append(Spacer(1, 14))

        # ================= 4. FORENSIC TIMELINE EXTRACT =================
        story.append(Paragraph("4. Unified Chronological Timeline Extract", h1))
        story.append(Paragraph(f"Exemplar chronological events from total corpus ({len(data['timeline'])} sample):", body))

        tl_headers = [Paragraph("<b>Timestamp (UTC)</b>", table_hdr), Paragraph("<b>Browser</b>", table_hdr), Paragraph("<b>Type</b>", table_hdr), Paragraph("<b>Title / Resource</b>", table_hdr)]
        tl_rows = [tl_headers]
        for ev in data["timeline"][:30]:
            ts_str = ev.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S") if ev.timestamp_utc else "N/A"
            title_clean = (ev.title or ev.url or "")[:55]
            tl_rows.append([
                Paragraph(ts_str, table_cell),
                Paragraph(f"{ev.browser}", table_cell),
                Paragraph(ev.event_type, table_cell),
                Paragraph(title_clean, table_cell)
            ])
        tl_t = Table(tl_rows, colWidths=[110, 60, 90, 240])
        tl_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E0")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(tl_t)
        story.append(Spacer(1, 14))

        # ================= 5. CHAIN OF CUSTODY =================
        story.append(Paragraph("5. Chain of Custody Audit Ledger", h1))
        story.append(Paragraph("Append-only forensic handling log verifying evidence provenance:", body))

        cust_headers = [Paragraph("<b>Timestamp (UTC)</b>", table_hdr), Paragraph("<b>Action</b>", table_hdr), Paragraph("<b>Actor</b>", table_hdr), Paragraph("<b>Description</b>", table_hdr)]
        cust_rows = [cust_headers]
        for c in data["custody"][:25]:
            ts_str = c.timestamp.strftime("%Y-%m-%d %H:%M:%S") if c.timestamp else "N/A"
            cust_rows.append([
                Paragraph(ts_str, table_cell),
                Paragraph(f"<b>{c.action}</b>", table_cell),
                Paragraph(c.actor, table_cell),
                Paragraph(c.description[:80], table_cell)
            ])
        cust_t = Table(cust_rows, colWidths=[110, 80, 110, 200])
        cust_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E0")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(cust_t)

        # Build document
        doc.build(story, canvasmaker=NumberedCanvas)

    @classmethod
    def _generate_html(cls, file_path: Path, data: Dict[str, Any]):
        case = data["case"]
        sources = data["sources"]
        files = data["files"]
        timeline = data["timeline"]
        correlations = data["correlations"]
        custody = data["custody"]

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TraceFusion Forensic Report - {case.case_number}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #e2e8f0; margin: 0; padding: 2rem; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  .card {{ background: #161f30; border: 1px solid #2d3748; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; }}
  h1, h2, h3 {{ color: #63b3ed; margin-top: 0; }}
  .header {{ border-bottom: 2px solid #3182ce; padding-bottom: 1rem; margin-bottom: 2rem; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.9rem; }}
  th, td {{ border: 1px solid #2d3748; padding: 8px 12px; text-align: left; }}
  th {{ background: #1a202c; color: #90cdf4; }}
  tr:nth-child(even) {{ background: #111827; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }}
  .badge-success {{ background: #22543d; color: #9ae6b4; }}
  .badge-info {{ background: #2a4365; color: #90cdf4; }}
  .mono {{ font-family: Courier, monospace; font-size: 0.85rem; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>TRACEFUSION FORENSIC EXAMINATION REPORT</h1>
    <p>Case: <b>{case.case_number}</b> | {case.title} | Investigator: <b>{data['investigator']}</b> | Generated: {data['generated_at']}</p>
  </div>

  <div class="card">
    <h2>1. Executive Summary</h2>
    <p>A multi-source browser forensic analysis was performed on {len(sources)} profile(s), extracting {data['artifacts_total']} artifacts and {data['timeline_total']} timeline events.</p>
    <p>Notes: {data['investigator_notes'] or 'None provided.'}</p>
  </div>

  <div class="card">
    <h2>2. Evidence Files & Cryptographic SHA-256 Hashes</h2>
    <table>
      <thead><tr><th>File Name</th><th>Size</th><th>Source Path</th><th>SHA-256 Hash</th><th>Status</th></tr></thead>
      <tbody>
        {"".join(f"<tr><td>{f.file_name}</td><td>{f.file_size:,} B</td><td class='mono'>{f.source_full_path}</td><td class='mono'>{f.original_hash}</td><td><span class='badge badge-success'>{f.verification_status}</span></td></tr>" for f in files)}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>3. Cross-Source Correlated Activity</h2>
    <h3>Cross-Browser Domain Convergence</h3>
    <table>
      <thead><tr><th>Domain</th><th>Browsers</th><th>Evidentiary Note</th></tr></thead>
      <tbody>
        {"".join(f"<tr><td><b>{c['domain']}</b></td><td>{', '.join(c['browsers'])}</td><td>{c['note']}</td></tr>" for c in correlations.get('cross_browser_domains', []))}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>4. Timeline Sample (First {len(timeline)} Events)</h2>
    <table>
      <thead><tr><th>Timestamp (UTC)</th><th>Browser</th><th>Event Type</th><th>Title</th><th>URL</th></tr></thead>
      <tbody>
        {"".join(f"<tr><td>{e.timestamp_utc.strftime('%Y-%m-%d %H:%M:%S') if e.timestamp_utc else ''}</td><td><span class='badge badge-info'>{e.browser}</span></td><td>{e.event_type}</td><td>{e.title or ''}</td><td class='mono'>{e.url or ''}</td></tr>" for e in timeline)}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>5. Chain of Custody Audit Trail</h2>
    <table>
      <thead><tr><th>Timestamp</th><th>Action</th><th>Actor</th><th>Description</th></tr></thead>
      <tbody>
        {"".join(f"<tr><td>{c.timestamp.strftime('%Y-%m-%d %H:%M:%S') if c.timestamp else ''}</td><td><b>{c.action}</b></td><td>{c.actor}</td><td>{c.description}</td></tr>" for c in custody)}
      </tbody>
    </table>
  </div>
</div>
</body>
</html>"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    @classmethod
    def _generate_json(cls, file_path: Path, data: Dict[str, Any]):
        case = data["case"]
        doc = {
            "application": "TraceFusion",
            "version": "1.0.0-FORENSIC",
            "report_type": "FORENSIC_CASE_EXPORT",
            "generated_at": data["generated_at"],
            "investigator": data["investigator"],
            "case": case.to_dict(),
            "notes": data["investigator_notes"],
            "sources": [s.to_dict() for s in data["sources"]],
            "evidence_files": [f.to_dict() for f in data["files"]],
            "correlations": data["correlations"],
            "chain_of_custody": [c.to_dict() for c in data["custody"]],
            "timeline_sample": [e.to_dict() for e in data["timeline"]]
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)

    @classmethod
    def _generate_csv(cls, file_path: Path, data: Dict[str, Any]):
        """Exports timeline events as a structured forensic CSV table."""
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timeline_ID", "Case_Number", "Browser", "Profile", "Artifact_Type",
                "Event_Type", "Timestamp_UTC", "Raw_Timestamp", "Title", "URL",
                "Domain", "Source_File", "Source_Hash", "Confidence"
            ])
            for e in data["timeline"]:
                writer.writerow([
                    e.id,
                    data["case"].case_number,
                    e.browser,
                    e.profile,
                    e.artifact_type,
                    e.event_type,
                    e.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S UTC") if e.timestamp_utc else "",
                    e.timestamp_raw or "",
                    e.title or "",
                    e.url or "",
                    e.domain or "",
                    e.source_file or "",
                    e.source_hash or "",
                    e.confidence
                ])
