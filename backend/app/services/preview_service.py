"""Preview Service for Column Mapping, Validation Scanning and Immutable Preview Versioning."""

import re
import json
import hashlib
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.models.source_submission import SourceSubmission
from app.models.submission_preview import SubmissionPreview
from app.services.storage_service import StorageService
from app.services.parser_service import ParserService, ParsedFileResult


APAAR_REGEX = re.compile(r"^\d{12}$")
HYPHENATED_APAAR_REGEX = re.compile(r"^\d{4}-\d{4}-\d{4}$")


class PreviewService:
    """
    Handles header autodetection, suggested column mapping generation,
    full-file validation scanning, and persistent immutable preview versioning.
    """

    CURRENT_MAPPING_VERSION = "v1.0"
    SUPPORTED_MAPPING_VERSIONS = {"v1.0"}

    CURRENT_VALIDATION_RULES_VERSION = "rules-v2026.1"
    SUPPORTED_VALIDATION_RULES_VERSIONS = {"rules-v2026.1"}

    CURRENT_NORMALIZATION_VERSION = "norm-v1.0"
    SUPPORTED_NORMALIZATION_VERSIONS = {"norm-v1.0"}


    @classmethod
    def suggest_column_mapping(cls, headers: List[str]) -> Dict[str, Optional[str]]:
        """
        Suggests field mappings based on header name conventions.
        """
        normalized_headers = {h.lower().replace(" ", "_").replace("-", "_"): h for h in headers}

        mapping: Dict[str, Optional[str]] = {
            "student_id": None,
            "full_name": None,
            "apaar_id": None,
            "student_status": None,
        }

        # Match student_id
        for candidate in ["student_id", "roll_no", "rollno", "roll", "reg_no", "registration_no", "id", "enrollment_no"]:
            if candidate in normalized_headers:
                mapping["student_id"] = normalized_headers[candidate]
                break

        # Match full_name
        for candidate in ["full_name", "name", "student_name", "studentname", "candidate_name"]:
            if candidate in normalized_headers:
                mapping["full_name"] = normalized_headers[candidate]
                break

        # Match apaar_id
        for candidate in ["apaar_id", "apaar", "apaar_number", "apaarid", "national_id"]:
            if candidate in normalized_headers:
                mapping["apaar_id"] = normalized_headers[candidate]
                break

        # Match student_status
        for candidate in ["student_status", "status", "enrollment_status", "state"]:
            if candidate in normalized_headers:
                mapping["student_status"] = normalized_headers[candidate]
                break

        return mapping

    @classmethod
    def validate_row(
        cls,
        row_number: int,
        raw_payload: Dict[str, Any],
        column_mapping: Dict[str, str],
        seen_student_ids: set,
    ) -> Tuple[str, List[str], List[str]]:
        """
        Validates an individual row according to statutory rules:
        - student_id: mandatory
        - apaar_id: format-only check (12 numeric digits); missing or malformed is non-fatal warning
        - duplicates: checked within file

        Returns:
            Tuple of (validation_status: str, errors: List[str], warnings: List[str])
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Student Identifier Validation
        id_col = column_mapping.get("student_id")
        raw_val = raw_payload.get(id_col) if id_col else None
        student_id_val = str(raw_val).strip() if raw_val is not None else ""

        if not student_id_val:
            errors.append(f"Row {row_number}: Missing mandatory student roll/registration identifier.")
        elif student_id_val in seen_student_ids:
            warnings.append(f"Row {row_number}: Duplicate student identifier '{student_id_val}' detected within file.")
        else:
            seen_student_ids.add(student_id_val)

        # 2. APAAR Identifier Validation (Documented format-only check)
        apaar_col = column_mapping.get("apaar_id")
        raw_apaar_val = raw_payload.get(apaar_col) if apaar_col else None
        raw_apaar = str(raw_apaar_val).strip() if raw_apaar_val is not None else ""

        if not raw_apaar:
            # MISSING_APAAR: permitted reviewable provisional record
            warnings.append(f"Row {row_number}: Missing APAAR identifier. Record will be retained as unverified provisional identity.")
        else:
            clean_apaar = raw_apaar.replace("-", "").replace(" ", "")
            if not APAAR_REGEX.match(clean_apaar):
                # INVALID_FORMAT: non-fatal warning
                warnings.append(
                    f"Row {row_number}: Invalid APAAR format '{raw_apaar}' (expected 12 numeric digits). Retained as unverified reviewable identity."
                )

        if errors:
            status = "INVALID"
        elif any("Duplicate" in w for w in warnings):
            status = "DUPLICATE"
        elif warnings:
            status = "WARNING"
        else:
            status = "VALID"

        return status, errors, warnings

    @classmethod
    def generate_full_preview(
        cls,
        db: Session,
        submission: SourceSubmission,
        column_mapping: Dict[str, str],
    ) -> Tuple[SubmissionPreview, Dict[str, Any]]:
        """
        Operation B: Scans the complete file using the proposed column mapping.
        Computes exact counts across all rows (identifying errors beyond row 50).
        Creates an immutable, persistent SubmissionPreview record.
        Zero student repository mutations.
        """
        file_path = StorageService.resolve_safe_path(submission.storage_key)
        parsed_result: ParsedFileResult = ParserService.parse_file(file_path, mime_type=submission.mime_type)

        seen_ids: set = set()
        valid_count = 0
        warning_count = 0
        error_count = 0
        duplicate_count = 0

        sample_rows: List[Dict[str, Any]] = []
        errors_by_row: List[Dict[str, Any]] = []
        warnings_by_row: List[Dict[str, Any]] = []

        for p_row in parsed_result.rows:
            status, row_errors, row_warnings = cls.validate_row(
                row_number=p_row.row_number,
                raw_payload=p_row.raw_payload,
                column_mapping=column_mapping,
                seen_student_ids=seen_ids,
            )

            if status == "VALID":
                valid_count += 1
            elif status == "WARNING":
                warning_count += 1
            elif status == "DUPLICATE":
                duplicate_count += 1
                warning_count += 1
            elif status == "INVALID":
                error_count += 1

            if row_errors:
                errors_by_row.append({"row_number": p_row.row_number, "errors": row_errors})
            if row_warnings:
                warnings_by_row.append({"row_number": p_row.row_number, "warnings": row_warnings})

            if len(sample_rows) < 15 or row_errors or row_warnings:
                if len(sample_rows) < 25:
                    sample_rows.append({
                        "row_number": p_row.row_number,
                        "raw_payload": p_row.raw_payload,
                        "parsed_payload": p_row.parsed_payload,
                        "validation_status": status,
                        "errors": row_errors,
                        "warnings": row_warnings,
                    })

        # Compute deterministic mapping hash
        canonical_mapping_json = json.dumps(column_mapping, sort_keys=True)
        mapping_hash = hashlib.sha256(canonical_mapping_json.encode("utf-8")).hexdigest()

        summary = {
            "total_rows_detected": parsed_result.total_rows_detected,
            "detected_encoding": parsed_result.encoding,
            "valid_rows_count": valid_count,
            "warning_rows_count": warning_count,
            "error_rows_count": error_count,
            "duplicate_rows_count": duplicate_count,
            "errors_by_row": errors_by_row[:50],  # sample error breakdown
            "warnings_by_row": warnings_by_row[:50],
            "parser_warnings": parsed_result.warnings,
        }

        # Deactivate any previous active preview for this submission
        db.execute(
            update(SubmissionPreview)
            .where(SubmissionPreview.submission_id == submission.id)
            .values(is_active=False)
        )

        # Create new immutable preview version
        preview = SubmissionPreview(
            submission_id=submission.id,
            file_fingerprint=submission.file_fingerprint,
            column_mapping=column_mapping,
            mapping_version=cls.CURRENT_MAPPING_VERSION,
            mapping_hash=mapping_hash,
            parser_version=ParserService.CURRENT_PARSER_VERSION,
            validation_rules_version=cls.CURRENT_VALIDATION_RULES_VERSION,
            normalization_version=cls.CURRENT_NORMALIZATION_VERSION,
            validation_summary=summary,
            is_active=True,
        )
        db.add(preview)

        # Update submission metrics and state
        submission.total_rows_count = parsed_result.total_rows_detected
        submission.valid_rows_count = valid_count
        submission.warning_rows_count = warning_count
        submission.error_rows_count = error_count
        submission.duplicate_rows_count = duplicate_count
        submission.mapping_config = column_mapping
        submission.validation_summary = summary
        submission.submission_status = "PREVIEW_READY"

        db.commit()
        db.refresh(preview)
        db.refresh(submission)

        response_payload = {
            "preview_id": str(preview.id),
            "submission_id": str(submission.id),
            "submission_status": submission.submission_status,
            "file_fingerprint": submission.file_fingerprint,
            "mapping_version": preview.mapping_version,
            "mapping_hash": preview.mapping_hash,
            "detected_encoding": parsed_result.encoding,
            "total_rows_count": submission.total_rows_count,
            "valid_rows_count": submission.valid_rows_count,
            "warning_rows_count": submission.warning_rows_count,
            "error_rows_count": submission.error_rows_count,
            "duplicate_rows_count": submission.duplicate_rows_count,
            "column_mapping": column_mapping,
            "validation_summary": summary,
            "sample_rows": sample_rows,
            "created_at": preview.created_at.isoformat(),
        }

        return preview, response_payload

