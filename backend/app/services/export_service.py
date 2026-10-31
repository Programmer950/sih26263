"""Export Service for Snapshot Roster and Comparison Reports with Formula Injection Defusing."""

import io
import csv
import uuid
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.models import (
    User,
    RosterSnapshot,
    AnnualRosterObservation,
    StudentIdentity,
    SourceSubmissionRecord,
)
from app.services.comparison_service import ComparisonService
from app.schemas.snapshot import SnapshotComparisonResponse

logger = logging.getLogger("apaar_setu.export")

FORMULA_PREFIX_CHARS = ("=", "+", "-", "@", "|", "%")
CONTROL_OR_WHITESPACE = " \t\r\n\x00\x0b\x0c"


def is_pure_number(s: str) -> bool:
    """Checks if a string represents a pure numeric literal without formula expressions or operators."""
    s_clean = s.strip()
    if not s_clean:
        return False
    try:
        float(s_clean)
        if s_clean.lower() in ("nan", "inf", "-inf", "+inf", "infinity", "-infinity"):
            return False
        return True
    except ValueError:
        return False


def defuse_formula_injection(value: Any) -> Any:
    """
    Defuses spreadsheet formula injection (CSV/Excel Formula Injection / CWE-1236).

    1. Preserves None as empty string and booleans as boolean strings.
    2. Preserves legitimate numeric types (int, float) as numbers.
    3. Preserves legitimate pure numeric strings (e.g. '-5', '-12.50', '42') without mutation.
    4. Detects formula prefixes (=, +, -, @, |, %) including those preceded by leading
       whitespace (spaces, tabs) or control characters (newlines, carriage returns, null bytes).
    5. Defuses formula injection attempts by prepending a single quote (').
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return value

    s = str(value)
    if not s:
        return ""

    # Pure numeric strings (e.g. "-5", "-12.50") retain intended numeric meaning
    if is_pure_number(s):
        return s

    # Strip leading whitespace and control characters to inspect effective starting character
    stripped = s.lstrip(CONTROL_OR_WHITESPACE)

    # Check if stripped starts with formula characters, or original starts with control characters
    starts_with_control = ord(s[0]) < 32

    if (stripped and stripped[0] in FORMULA_PREFIX_CHARS) or starts_with_control:
        return f"'{s}"

    return s


class ExportService:
    """
    Handles secure generation of CSV and XLSX exports for Roster Snapshots and Comparison Reports.
    Enforces tenant isolation, complete provenance metadata, and formula injection defusing.
    """

    @classmethod
    def export_snapshot_roster(
        cls,
        db: Session,
        snapshot_id: uuid.UUID,
        current_user: User,
        export_format: str = "csv",
    ) -> StreamingResponse:
        """
        Exports all student records for a single snapshot in CSV or XLSX format.
        """
        snapshot = db.get(RosterSnapshot, snapshot_id)
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot {snapshot_id} not found.",
            )

        if current_user.role.role_name == "INSTITUTION_ADMIN" and snapshot.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Access to snapshot for external institution forbidden.",
            )

        # Query all observations in this snapshot
        rows = db.execute(
            select(AnnualRosterObservation, StudentIdentity, SourceSubmissionRecord)
            .join(StudentIdentity, AnnualRosterObservation.student_identity_id == StudentIdentity.id)
            .outerjoin(SourceSubmissionRecord, AnnualRosterObservation.source_record_id == SourceSubmissionRecord.id)
            .where(AnnualRosterObservation.source_submission_id == snapshot.source_submission_id)
            .order_by(SourceSubmissionRecord.row_number.asc())
        ).all()

        headers = [
            "Student UUID",
            "Full Name",
            "Masked APAAR",
            "Identity Status",
            "Student Status",
            "Academic Year",
            "Source Row Index",
            "Observation Timestamp",
            "Observation ID",
        ]

        data = []
        for obs, ident, rec in rows:
            data.append([
                str(ident.internal_student_uuid),
                ident.full_name,
                ident.masked_apaar_reference or "N/A",
                ident.identity_status,
                obs.student_status,
                obs.academic_year,
                rec.row_number if rec else "",
                obs.observation_timestamp.isoformat() if obs.observation_timestamp else "",
                str(obs.id),
            ])

        filename_prefix = f"roster_snapshot_{snapshot.academic_year}_{snapshot.id}"

        if export_format.lower() == "xlsx":
            return cls._build_xlsx_response(
                headers=headers,
                data=data,
                sheet_title="Roster Snapshot",
                filename=f"{filename_prefix}.xlsx",
                metadata_rows=[
                    ("Snapshot ID", str(snapshot.id)),
                    ("Institution ID", str(snapshot.institution_id)),
                    ("Programme ID", str(snapshot.programme_id)),
                    ("Academic Year", snapshot.academic_year),
                    ("Is Authoritative", str(snapshot.is_authoritative)),
                    ("Completeness Status", snapshot.completeness_status),
                    ("Observed Headcount", str(snapshot.observed_headcount)),
                    ("Snapshot Hash", snapshot.snapshot_hash),
                    ("Exported At (UTC)", datetime.now(timezone.utc).isoformat()),
                ],
            )
        else:
            return cls._build_csv_response(
                headers=headers,
                data=data,
                filename=f"{filename_prefix}.csv",
                metadata_rows=[
                    f"# Snapshot ID: {snapshot.id}",
                    f"# Academic Year: {snapshot.academic_year}",
                    f"# Authoritative: {snapshot.is_authoritative}",
                    f"# Observed Headcount: {snapshot.observed_headcount}",
                    f"# Hash: {snapshot.snapshot_hash}",
                ],
            )

    @classmethod
    def export_comparison_report(
        cls,
        db: Session,
        candidate_id: uuid.UUID,
        current_user: User,
        baseline_id: Optional[uuid.UUID] = None,
        export_format: str = "csv",
    ) -> StreamingResponse:
        """
        Exports reconciliation comparison report between candidate snapshot and baseline.
        """
        comparison: SnapshotComparisonResponse = ComparisonService.compare_snapshots(
            db=db,
            candidate_id=candidate_id,
            current_user=current_user,
            baseline_id=baseline_id,
        )

        headers = [
            "Student UUID",
            "Student Name",
            "Masked APAAR",
            "Classification",
            "Explanation",
            "Baseline Status",
            "Candidate Status",
            "Baseline Row",
            "Candidate Row",
            "Candidate Obs ID",
            "Baseline Obs ID",
            "Identity Status",
        ]

        data = []
        for rec in comparison.records:
            data.append([
                str(rec.internal_student_uuid),
                rec.student_name,
                rec.masked_apaar or "N/A",
                rec.classification,
                rec.explanation,
                rec.source_status_baseline or "",
                rec.source_status_candidate or "",
                rec.source_row_baseline if rec.source_row_baseline is not None else "",
                rec.source_row_candidate if rec.source_row_candidate is not None else "",
                rec.provenance.get("candidate_observation_id") or "",
                rec.provenance.get("baseline_observation_id") or "",
                rec.provenance.get("identity_status") or "",
            ])

        filename_prefix = f"comparison_{comparison.academic_year}_{candidate_id}"

        metadata_tuples = [
            ("Candidate Snapshot ID", str(comparison.candidate_snapshot_id)),
            ("Baseline Snapshot ID", str(comparison.baseline_snapshot_id) if comparison.baseline_snapshot_id else "None (Initial)"),
            ("Institution ID", str(comparison.institution_id)),
            ("Programme ID", str(comparison.programme_id)),
            ("Academic Year", comparison.academic_year),
            ("Added Records", str(comparison.summary_metrics.get("ADDED", 0))),
            ("Continuing Records", str(comparison.summary_metrics.get("CONTINUING", 0))),
            ("Withdrawn Records", str(comparison.summary_metrics.get("WITHDRAWN", 0))),
            ("Documented Transfers", str(comparison.summary_metrics.get("DOCUMENTED_TRANSFER", 0))),
            ("Unexplained Appearances", str(comparison.summary_metrics.get("UNEXPLAINED_APPEARANCE", 0))),
            ("Unexplained Disappearances", str(comparison.summary_metrics.get("UNEXPLAINED_DISAPPEARANCE", 0))),
            ("Ambiguous Identity", str(comparison.summary_metrics.get("AMBIGUOUS_IDENTITY", 0))),
            ("Insufficient Evidence", str(comparison.summary_metrics.get("INSUFFICIENT_EVIDENCE", 0))),
            ("Exported At (UTC)", datetime.now(timezone.utc).isoformat()),
        ]

        if export_format.lower() == "xlsx":
            return cls._build_xlsx_response(
                headers=headers,
                data=data,
                sheet_title="Comparison Report",
                filename=f"{filename_prefix}.xlsx",
                metadata_rows=metadata_tuples,
            )
        else:
            meta_comments = [f"# {k}: {v}" for k, v in metadata_tuples]
            return cls._build_csv_response(
                headers=headers,
                data=data,
                filename=f"{filename_prefix}.csv",
                metadata_rows=meta_comments,
            )

    @classmethod
    def _build_csv_response(
        cls,
        headers: List[str],
        data: List[List[Any]],
        filename: str,
        metadata_rows: Optional[List[str]] = None,
    ) -> StreamingResponse:
        """
        Builds a CSV StreamingResponse with defused formula injection and UTF-8-SIG encoding.
        """
        output = io.StringIO()
        if metadata_rows:
            for comment in metadata_rows:
                output.write(f"{comment}\n")

        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([defuse_formula_injection(h) for h in headers])

        for row in data:
            writer.writerow([defuse_formula_injection(cell) for cell in row])

        content = output.getvalue().encode("utf-8-sig")
        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @classmethod
    def _build_xlsx_response(
        cls,
        headers: List[str],
        data: List[List[Any]],
        sheet_title: str,
        filename: str,
        metadata_rows: Optional[List[Tuple[str, str]]] = None,
    ) -> StreamingResponse:
        """
        Builds an XLSX StreamingResponse using openpyxl with formatted headers, metadata sheet,
        and defused cell values.
        """
        wb = openpyxl.Workbook()
        ws_data = wb.active
        ws_data.title = sheet_title

        # Style definitions
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
        cell_font = Font(name="Segoe UI", size=10)
        border_side = Side(style="thin", color="E2E8F0")
        cell_border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)

        # Write Headers
        for col_idx, header in enumerate(headers, start=1):
            cell = ws_data.cell(row=1, column=col_idx, value=str(header))
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Write Data
        for row_idx, row_values in enumerate(data, start=2):
            for col_idx, val in enumerate(row_values, start=1):
                clean_val = defuse_formula_injection(val)
                if isinstance(clean_val, (int, float)):
                    cell = ws_data.cell(row=row_idx, column=col_idx, value=clean_val)
                    cell.alignment = Alignment(horizontal="right")
                elif isinstance(clean_val, str) and is_pure_number(clean_val):
                    try:
                        num_val = int(clean_val) if "." not in clean_val else float(clean_val)
                        cell = ws_data.cell(row=row_idx, column=col_idx, value=num_val)
                        cell.alignment = Alignment(horizontal="right")
                    except ValueError:
                        cell = ws_data.cell(row=row_idx, column=col_idx, value=clean_val)
                        cell.alignment = Alignment(horizontal="left")
                else:
                    cell = ws_data.cell(row=row_idx, column=col_idx, value=clean_val)
                    cell.alignment = Alignment(horizontal="left")
                cell.font = cell_font
                cell.border = cell_border

        # Auto-fit column widths
        for col in ws_data.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws_data.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 60)

        # Write Metadata Sheet if provided
        if metadata_rows:
            ws_meta = wb.create_sheet(title="Report Metadata")
            meta_header_fill = PatternFill(start_color="2D3748", end_color="2D3748", fill_type="solid")
            
            c1 = ws_meta.cell(row=1, column=1, value="Property")
            c2 = ws_meta.cell(row=1, column=2, value="Value")
            c1.font = header_font
            c1.fill = meta_header_fill
            c2.font = header_font
            c2.fill = meta_header_fill

            for r_idx, (prop, val) in enumerate(metadata_rows, start=2):
                ws_meta.cell(row=r_idx, column=1, value=prop).font = Font(name="Segoe UI", size=10, bold=True)
                ws_meta.cell(row=r_idx, column=2, value=defuse_formula_injection(val)).font = cell_font

            ws_meta.column_dimensions["A"].width = 28
            ws_meta.column_dimensions["B"].width = 65

        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)

        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

