"""Submission Schemas for Ingestion, Previews and Lifecycle Management."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class PreviewRequest(BaseModel):
    """Request payload for generating an immutable full-file mapping preview."""
    column_mapping: Dict[str, str] = Field(..., description="Mapping of standard fields to file headers")


class UploadResponse(BaseModel):
    """Response returned upon file upload and initial sample preview."""
    submission_id: uuid.UUID
    submission_status: str
    file_fingerprint: str
    original_filename: str
    file_size_bytes: int
    detected_encoding: Optional[str] = None
    total_rows_count: int
    valid_rows_count: Optional[int] = 0
    warning_rows_count: Optional[int] = 0
    error_rows_count: Optional[int] = 0
    duplicate_rows_count: Optional[int] = 0
    detected_headers: List[str]
    suggested_mapping: Dict[str, Optional[str]]
    sample_rows: List[Dict[str, Any]]


class PreviewResponse(BaseModel):
    """Response returned upon full-file validation preview calculation."""
    preview_id: uuid.UUID
    submission_id: uuid.UUID
    file_fingerprint: str
    mapping_version: str
    mapping_hash: str
    detected_encoding: Optional[str] = None
    total_rows_count: int
    valid_rows_count: int
    warning_rows_count: int
    error_rows_count: int
    duplicate_rows_count: int
    column_mapping: Dict[str, str]
    validation_summary: Dict[str, Any]
    sample_rows: Optional[List[Dict[str, Any]]] = None
    created_at: datetime


class CancelResponse(BaseModel):
    """Response returned when an uncommitted submission is cancelled."""
    submission_id: uuid.UUID
    submission_status: str


class ConfirmRequest(BaseModel):
    """Request payload for committing and ingesting a previewed submission."""
    preview_id: uuid.UUID
    column_mapping: Dict[str, str]
    completeness_status: str = Field(default="COMPLETE", pattern="^(COMPLETE|PARTIAL|UNKNOWN)$")
    mark_as_authoritative: bool = False


class ConfirmResponse(BaseModel):
    """Response returned upon successful atomic ingestion."""
    submission_id: uuid.UUID
    submission_status: str
    snapshot_id: Optional[uuid.UUID] = None
    total_records_processed: int
    valid_records: int
    warning_records: int
    error_records: int
    snapshot_status: Optional[str] = None
    completeness_status: Optional[str] = None
    is_authoritative: bool
    committed_at: datetime


class SubmissionSummary(BaseModel):
    """Summary item for paginated submissions list."""
    id: uuid.UUID
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    submission_type: str
    original_filename: str
    file_fingerprint: str
    file_size_bytes: int
    submission_status: str
    total_rows_count: Optional[int] = None
    valid_rows_count: Optional[int] = None
    warning_rows_count: Optional[int] = None
    error_rows_count: Optional[int] = None
    duplicate_rows_count: Optional[int] = None
    created_at: datetime
    committed_at: Optional[datetime] = None


class PaginatedSubmissionsResponse(BaseModel):
    """Paginated response envelope for submissions."""
    items: List[SubmissionSummary]
    total: int
    page: int
    limit: int
    pages: int


class SubmissionDetailResponse(BaseModel):
    """Detailed response for a single submission entity."""
    id: uuid.UUID
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    submission_type: str
    original_filename: str
    file_fingerprint: str
    file_size_bytes: int
    submission_status: str
    total_rows_count: Optional[int] = None
    valid_rows_count: Optional[int] = None
    warning_rows_count: Optional[int] = None
    error_rows_count: Optional[int] = None
    duplicate_rows_count: Optional[int] = None
    mapping_config: Optional[Dict[str, Any]] = None
    validation_summary: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None
    active_preview_id: Optional[uuid.UUID] = None
    created_at: datetime
    committed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class ConfirmRequest(BaseModel):
    """Payload for confirming and atomically ingesting a roster submission."""
    preview_id: uuid.UUID
    column_mapping: Dict[str, str]
    mark_as_authoritative: bool = True
    completeness_status: str = "COMPLETE"


class ConfirmResponse(BaseModel):
    """Response returned upon successful atomic ingestion confirmation."""
    submission_id: uuid.UUID
    submission_status: str
    snapshot_id: uuid.UUID
    total_records_processed: int
    valid_records: int
    warning_records: int
    error_records: int
    snapshot_status: str
    completeness_status: str
    is_authoritative: bool
    committed_at: datetime


