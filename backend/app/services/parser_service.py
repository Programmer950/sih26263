"""Parser Service for Safe CSV and XLSX Ingestion with Resource and Archive Protection."""

import os
import csv
import zipfile
import time
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings


class ArchiveSecurityError(ValueError):
    """Raised when an archive fails security or resource checks (e.g. Zip Bomb)."""
    pass


class InvalidArchiveError(ValueError):
    """Raised when an archive is malformed or unparseable."""
    pass


class ParserLimitExceededError(ValueError):
    """Raised when row or column limits are exceeded."""
    pass


class ParsedRow:
    """Represents a single parsed line/row from a file."""

    def __init__(
        self,
        row_number: int,
        raw_payload: Dict[str, Any],
        parsed_payload: Dict[str, Any],
        formula_metadata: Optional[Dict[str, Any]] = None,
    ):
        self.row_number = row_number
        self.raw_payload = raw_payload
        self.parsed_payload = parsed_payload
        self.formula_metadata = formula_metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_number": self.row_number,
            "raw_payload": self.raw_payload,
            "parsed_payload": self.parsed_payload,
            "formula_metadata": self.formula_metadata,
        }


class ParsedFileResult:
    """Encapsulates the complete or sample parsed output of a roster file."""

    def __init__(
        self,
        headers: List[str],
        rows: List[ParsedRow],
        total_rows_detected: int,
        warnings: Optional[List[str]] = None,
        encoding: Optional[str] = None,
    ):
        self.headers = headers
        self.rows = rows
        self.total_rows_detected = total_rows_detected
        self.warnings = warnings or []
        self.encoding = encoding


class ParserService:
    """
    Safely inspects, bounds, and parses untrusted CSV and XLSX files.
    Enforces pre-flight ZIP archive inspection, dual formula extraction,
    resource caps, and safe XML handling.
    """

    CURRENT_PARSER_VERSION = "openpyxl-v3.1.2/csv-std"
    SUPPORTED_PARSER_VERSIONS = {"openpyxl-v3.1.2/csv-std"}


    @classmethod
    def inspect_zip_archive(cls, file_path: str) -> None:
        """
        Pre-flight ZIP archive inspection before passing to openpyxl.
        Enforces size, compression ratio, entry count, and path traversal guards.
        """
        try:
            if not zipfile.is_zipfile(file_path):
                raise InvalidArchiveError("Provided file is not a valid ZIP/XLSX archive.")

            with zipfile.ZipFile(file_path, "r") as zf:
                infolist = zf.infolist()

                # 1. Entry Count Limit
                if len(infolist) > settings.MAX_ARCHIVE_ENTRY_COUNT:
                    raise ArchiveSecurityError(
                        f"ZIP archive entry count ({len(infolist)}) exceeds maximum limit of {settings.MAX_ARCHIVE_ENTRY_COUNT}."
                    )

                total_uncompressed = 0
                total_compressed = 0

                for info in infolist:
                    # 2. Path Traversal & Suspicious Name Guard
                    filename = info.filename
                    if (
                        ".." in filename
                        or filename.startswith("/")
                        or filename.startswith("\\")
                        or "\x00" in filename
                    ):
                        raise ArchiveSecurityError(
                            f"ZIP entry contains prohibited path traversal sequence: {filename}"
                        )

                    # 3. Individual Entry Size Limit (20 MB)
                    if info.file_size > 20 * 1024 * 1024:
                        raise ArchiveSecurityError(
                            f"ZIP entry '{filename}' size ({info.file_size} bytes) exceeds individual entry cap of 20 MB."
                        )

                    total_uncompressed += info.file_size
                    total_compressed += info.compress_size

                # 4. Total Uncompressed Size Limit (50 MB)
                if total_uncompressed > settings.MAX_UNCOMPRESSED_ARCHIVE_BYTES:
                    raise ArchiveSecurityError(
                        f"Total uncompressed ZIP archive size ({total_uncompressed} bytes) exceeds limit of {settings.MAX_UNCOMPRESSED_ARCHIVE_BYTES} bytes."
                    )

                # 5. Compression Ratio Limit (Zip Bomb Defense: Default 20:1)
                if total_compressed > 0:
                    ratio = total_uncompressed / total_compressed
                    if ratio > settings.MAX_COMPRESSION_RATIO:
                        raise ArchiveSecurityError(
                            f"ZIP archive compression ratio ({ratio:.1f}:1) exceeds safe limit of {settings.MAX_COMPRESSION_RATIO}:1 (potential decompression bomb)."
                        )

        except zipfile.BadZipFile as e:
            raise InvalidArchiveError(f"Corrupt or invalid ZIP archive: {str(e)}")

    @classmethod
    def parse_csv(
        cls,
        file_path: str,
        max_rows: Optional[int] = None,
    ) -> ParsedFileResult:
        """
        Parses CSV files with encoding detection, column limits, and row limits.
        """
        # Validate that the file does not contain binary control/null bytes
        with open(file_path, "rb") as bf:
            sample_bytes = bf.read(4096)
            if b"\x00" in sample_bytes:
                raise ValueError("Unsupported binary file format: null bytes detected in text CSV.")
            has_bom = sample_bytes.startswith(b"\xef\xbb\xbf")

        # Select encoding priority based on presence of UTF-8 BOM
        if has_bom:
            encodings = ["utf-8-sig", "utf-8", "latin-1"]
        else:
            encodings = ["utf-8", "latin-1"]
        lines = None
        selected_enc = None
        warnings: List[str] = []

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    lines = f.readlines()
                selected_enc = enc
                break
            except UnicodeDecodeError:
                continue

        if lines is None:
            raise ValueError("Unable to decode CSV file with supported encodings (UTF-8, Latin-1).")

        if selected_enc == "latin-1":
            warnings.append(
                "File decoded using fallback encoding 'latin-1'. Non-ASCII characters may require verification."
            )

        reader = csv.reader(lines)
        headers: List[str] = []
        parsed_rows: List[ParsedRow] = []
        total_rows = 0

        start_time = time.time()

        for idx, row in enumerate(reader):
            if time.time() - start_time > settings.PARSER_TIMEOUT_SECONDS:
                raise TimeoutError(f"CSV parsing exceeded maximum timeout of {settings.PARSER_TIMEOUT_SECONDS}s.")

            # Skip empty lines
            if not row or all(not cell.strip() for cell in row):
                continue

            if not headers:
                # First non-empty row is headers
                headers = [col.strip() for col in row]
                if len(headers) > settings.MAX_COL_COUNT:
                    raise ParserLimitExceededError(
                        f"CSV column count ({len(headers)}) exceeds maximum allowed cap of {settings.MAX_COL_COUNT}."
                    )
                continue

            total_rows += 1
            if total_rows > settings.MAX_ROW_COUNT:
                raise ParserLimitExceededError(
                    f"CSV row count exceeds maximum allowed cap of {settings.MAX_ROW_COUNT}."
                )

            if max_rows and len(parsed_rows) >= max_rows:
                continue

            raw_payload: Dict[str, Any] = {}
            parsed_payload: Dict[str, Any] = {}

            for col_idx, col_name in enumerate(headers):
                cell_val = row[col_idx] if col_idx < len(row) else ""
                # Verbatim raw value preserved unmutated (no apostrophe prepended!)
                raw_payload[col_name] = cell_val
                # Normalized parsed value (trimmed)
                parsed_payload[col_name] = cell_val.strip()

            parsed_rows.append(
                ParsedRow(
                    row_number=total_rows,
                    raw_payload=raw_payload,
                    parsed_payload=parsed_payload,
                )
            )

        return ParsedFileResult(
            headers=headers,
            rows=parsed_rows,
            total_rows_detected=total_rows,
            warnings=warnings,
            encoding=selected_enc,
        )

    @classmethod
    def parse_xlsx(
        cls,
        file_path: str,
        max_rows: Optional[int] = None,
    ) -> ParsedFileResult:
        """
        Parses XLSX files using two passes:
        Pass 1: data_only=False (captures raw formula strings).
        Pass 2: data_only=True (extracts cached calculation results).
        Enforces pre-flight inspection, resource limits, and missing cached value handling.
        """
        import openpyxl

        # 1. Pre-flight ZIP archive inspection
        cls.inspect_zip_archive(file_path)

        start_time = time.time()

        # Pass 1: Raw formula inspection (open binary stream to support any storage extension)
        f_formula = open(file_path, "rb")
        wb_formula = openpyxl.load_workbook(f_formula, read_only=True, data_only=False)
        # Pass 2: Cached value inspection
        f_data = open(file_path, "rb")
        wb_data = openpyxl.load_workbook(f_data, read_only=True, data_only=True)

        try:
            sheet_formula = wb_formula.active
            sheet_data = wb_data.active

            if sheet_formula is None or sheet_data is None:
                raise InvalidArchiveError("XLSX workbook does not contain an active sheet.")

            headers: List[str] = []
            parsed_rows: List[ParsedRow] = []
            total_rows = 0
            warnings: List[str] = []

            # Iterate rows in lockstep
            rows_formula_iter = sheet_formula.iter_rows(values_only=False)
            rows_data_iter = sheet_data.iter_rows(values_only=True)

            for formula_row, data_row in zip(rows_formula_iter, rows_data_iter):
                if time.time() - start_time > settings.PARSER_TIMEOUT_SECONDS:
                    raise TimeoutError(f"XLSX parsing exceeded maximum timeout of {settings.PARSER_TIMEOUT_SECONDS}s.")

                # Extract cell string values
                formula_vals = [c.value for c in formula_row]
                data_vals = list(data_row)

                # Skip completely empty rows
                if all(v is None or str(v).strip() == "" for v in formula_vals):
                    continue

                if not headers:
                    headers = [str(v).strip() if v is not None else f"Column_{i+1}" for i, v in enumerate(formula_vals)]
                    if len(headers) > settings.MAX_COL_COUNT:
                        raise ParserLimitExceededError(
                            f"XLSX column count ({len(headers)}) exceeds maximum allowed cap of {settings.MAX_COL_COUNT}."
                        )
                    continue

                total_rows += 1
                if total_rows > settings.MAX_ROW_COUNT:
                    raise ParserLimitExceededError(
                        f"XLSX row count exceeds maximum allowed cap of {settings.MAX_ROW_COUNT}."
                    )

                if max_rows and len(parsed_rows) >= max_rows:
                    continue

                raw_payload: Dict[str, Any] = {}
                parsed_payload: Dict[str, Any] = {}
                formula_metadata: Dict[str, Any] = {}

                for col_idx, col_name in enumerate(headers):
                    f_val = formula_vals[col_idx] if col_idx < len(formula_vals) else None
                    d_val = data_vals[col_idx] if col_idx < len(data_vals) else None

                    # Check if cell contains a spreadsheet formula
                    is_formula = isinstance(f_val, str) and f_val.startswith("=")

                    if is_formula:
                        formula_str = str(f_val)
                        raw_payload[col_name] = formula_str  # Verbatim formula preserved unmutated!

                        if d_val is None or str(d_val).strip() == "":
                            # Missing cached evaluation value
                            formula_metadata[col_name] = {
                                "formula": formula_str,
                                "cached_value": None,
                                "status": "UNRESOLVED_FORMULA_NO_CACHED_VALUE",
                            }
                            parsed_payload[col_name] = ""
                            warnings.append(
                                f"Row {total_rows}, Column '{col_name}': Formula '{formula_str}' has no cached calculation value."
                            )
                        else:
                            formula_metadata[col_name] = {
                                "formula": formula_str,
                                "cached_value": str(d_val),
                                "status": "CACHED_VALUE_PRESENT",
                            }
                            parsed_payload[col_name] = str(d_val).strip()
                    else:
                        val_str = str(f_val) if f_val is not None else ""
                        raw_payload[col_name] = val_str
                        parsed_payload[col_name] = val_str.strip()

                parsed_rows.append(
                    ParsedRow(
                        row_number=total_rows,
                        raw_payload=raw_payload,
                        parsed_payload=parsed_payload,
                        formula_metadata=formula_metadata,
                    )
                )

            return ParsedFileResult(
                headers=headers,
                rows=parsed_rows,
                total_rows_detected=total_rows,
                warnings=warnings,
                encoding="utf-8",
            )

        finally:
            wb_formula.close()
            wb_data.close()
            f_formula.close()
            f_data.close()

    @classmethod
    def parse_file(
        cls,
        file_path: str,
        mime_type: Optional[str] = None,
        filename: Optional[str] = None,
        max_rows: Optional[int] = None,
    ) -> ParsedFileResult:
        """
        Entry point to parse either CSV or XLSX based on magic bytes, archive structure, and filename consistency.
        Validates actual file content and archive structure without trusting extensions or client MIME types alone.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read magic bytes
        with open(file_path, "rb") as f:
            magic = f.read(8)

        # 1. Prohibit known unsupported binary executable / document formats
        if magic.startswith(b"%PDF"):
            raise ValueError("Unsupported file format: PDF documents are not supported for student roster ingestion.")
        if magic.startswith(b"MZ") or magic.startswith(b"\x7fELF"):
            raise ValueError("Unsupported file format: Executable binary files are strictly prohibited.")

        # 2. Check contradictory filename extensions vs content
        is_zip = magic.startswith(b"PK\x03\x04")
        if filename:
            fn_lower = filename.lower()
            if fn_lower.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")) and not is_zip:
                raise InvalidArchiveError(
                    f"Contradictory file format: File '{filename}' has an XLSX extension but is not a valid ZIP/XLSX archive (invalid archive headers)."
                )
            if fn_lower.endswith(".csv") and is_zip:
                raise InvalidArchiveError(
                    f"Contradictory file format: File '{filename}' has a CSV extension but contains binary ZIP/XLSX archive content."
                )

        # 3. Route to XLSX if ZIP archive or XLSX MIME type
        if is_zip or (mime_type and ("spreadsheetml" in mime_type or "excel" in mime_type)):
            return cls.parse_xlsx(file_path, max_rows=max_rows)
        else:
            return cls.parse_csv(file_path, max_rows=max_rows)

