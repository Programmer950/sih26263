"""Pydantic schemas for Roster Snapshot Management, Comparison, and Promotion."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class SnapshotSummary(BaseModel):
    """Summary overview of a roster snapshot."""
    id: uuid.UUID
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    source_submission_id: uuid.UUID
    completeness_status: str
    lifecycle_status: str
    is_authoritative: bool
    declared_headcount: int
    observed_headcount: int
    snapshot_canonicalization_version: str
    snapshot_hash: str
    effective_from: datetime
    created_at: datetime
    superseded_by_snapshot_id: Optional[uuid.UUID] = None
    superseded_at: Optional[datetime] = None


class PaginatedSnapshotsResponse(BaseModel):
    """Paginated envelope for snapshot listing."""
    items: List[SnapshotSummary]
    total: int
    page: int
    limit: int
    pages: int


class SnapshotDetailResponse(BaseModel):
    """Detailed response for a single snapshot with metadata and provenance."""
    id: uuid.UUID
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    source_submission_id: uuid.UUID
    completeness_status: str
    lifecycle_status: str
    is_authoritative: bool
    declared_headcount: int
    observed_headcount: int
    snapshot_canonicalization_version: str
    snapshot_hash: str
    snapshot_metadata: Dict[str, Any]
    effective_from: datetime
    created_at: datetime
    created_by_user_id: Optional[uuid.UUID] = None
    superseded_by_snapshot_id: Optional[uuid.UUID] = None
    superseded_at: Optional[datetime] = None
    source_submission_filename: Optional[str] = None
    source_submission_fingerprint: Optional[str] = None


class SnapshotPromoteRequest(BaseModel):
    """Request payload for manual snapshot authoritative promotion."""
    reason: Optional[str] = Field(None, max_length=500, description="Optional regulatory or administrative reason for promotion")


class SnapshotPromoteResponse(BaseModel):
    """Response returned upon successful snapshot promotion."""
    snapshot_id: uuid.UUID
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    is_authoritative: bool
    lifecycle_status: str
    superseded_snapshot_id: Optional[uuid.UUID] = None
    audit_event_id: uuid.UUID
    promoted_at: datetime


class ComparisonRecordItem(BaseModel):
    """Comparison item for an individual student record between candidate and baseline snapshots."""
    student_identity_id: uuid.UUID
    internal_student_uuid: uuid.UUID
    student_name: str
    masked_apaar: Optional[str] = None
    classification: str  # 'ADDED', 'CONTINUING', 'WITHDRAWN', 'DOCUMENTED_TRANSFER', 'UNEXPLAINED_APPEARANCE', 'UNEXPLAINED_DISAPPEARANCE', 'AMBIGUOUS_IDENTITY', 'INSUFFICIENT_EVIDENCE'
    explanation: str
    source_status_baseline: Optional[str] = None
    source_status_candidate: Optional[str] = None
    source_row_baseline: Optional[int] = None
    source_row_candidate: Optional[int] = None
    provenance: Dict[str, Any]


class SnapshotComparisonResponse(BaseModel):
    """Detailed comparison response between candidate snapshot and baseline snapshot."""
    candidate_snapshot_id: uuid.UUID
    baseline_snapshot_id: Optional[uuid.UUID] = None
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    summary_metrics: Dict[str, int]
    records: List[ComparisonRecordItem]

