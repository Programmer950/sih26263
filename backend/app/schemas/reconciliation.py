"""Pydantic Schemas for Reconciliation Runs, Result Items, and Discrepancy Cases."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class ReconciliationRunCreateRequest(BaseModel):
    """Payload to initiate a formal reconciliation run."""
    candidate_snapshot_id: uuid.UUID
    baseline_snapshot_id: Optional[uuid.UUID] = None
    run_type: str = Field("REGULATORY_RECONCILIATION", description="Run type: REGULATORY_RECONCILIATION, INSTITUTIONAL_SELF_AUDIT")
    parameters: Optional[Dict[str, Any]] = None


class ReconciliationRunResponse(BaseModel):
    """Overview metadata for a completed reconciliation run."""
    id: uuid.UUID
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    candidate_snapshot_id: uuid.UUID
    candidate_snapshot_hash: str
    baseline_snapshot_id: Optional[uuid.UUID] = None
    baseline_snapshot_hash: Optional[str] = None
    run_type: str
    execution_status: str
    engine_version: str
    rules_version: str
    result_fingerprint: str
    summary_counts: Dict[str, int]
    initiated_by_user_id: uuid.UUID
    created_at: datetime


class PaginatedReconciliationRunsResponse(BaseModel):
    """Envelope for paginated list of runs."""
    items: List[ReconciliationRunResponse]
    total: int
    page: int
    limit: int
    pages: int


class ResultItemDetail(BaseModel):
    """Individual student-level result item from a reconciliation run."""
    id: uuid.UUID
    reconciliation_run_id: uuid.UUID
    student_identity_id: uuid.UUID
    student_name: str
    masked_apaar: Optional[str] = None
    classification: str
    review_priority: str
    system_explanation: str
    is_case_eligible: bool
    discrepancy_case_id: Optional[uuid.UUID] = None
    candidate_row_number: Optional[int] = None
    baseline_row_number: Optional[int] = None
    candidate_submission_id: Optional[uuid.UUID] = None
    baseline_submission_id: Optional[uuid.UUID] = None
    created_at: datetime


class PaginatedResultItemsResponse(BaseModel):
    """Envelope for paginated result items."""
    items: List[ResultItemDetail]
    total: int
    page: int
    limit: int
    pages: int


class DiscrepancyCaseDecisionItem(BaseModel):
    """Decision log entry in a case's chronological history."""
    id: uuid.UUID
    from_status: str
    to_status: str
    action: str
    mandatory_reason: str
    evidence_references: Dict[str, Any]
    decided_by_user_id: uuid.UUID
    decided_by_name: Optional[str] = None
    created_at: datetime


class DiscrepancyCaseDetail(BaseModel):
    """Complete dossier view of an active or resolved discrepancy case."""
    id: uuid.UUID
    case_number: str
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    student_identity_id: uuid.UUID
    student_name: str
    masked_apaar: Optional[str] = None
    classification: str
    review_priority: str
    case_status: str
    occurrence_count: int
    system_explanation: str
    initial_reconciliation_run_id: uuid.UUID
    latest_reconciliation_run_id: uuid.UUID
    linked_prior_case_id: Optional[uuid.UUID] = None
    candidate_observation: Optional[Dict[str, Any]] = None
    baseline_observation: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    decisions: List[DiscrepancyCaseDecisionItem] = []


class PaginatedDiscrepancyCasesResponse(BaseModel):
    """Envelope for paginated list of discrepancy cases."""
    items: List[DiscrepancyCaseDetail]
    total: int
    page: int
    limit: int
    pages: int


class CaseDecisionCreateRequest(BaseModel):
    """Action submission on a discrepancy case."""
    action: str = Field(..., description="Action: START_INVESTIGATION, REQUEST_EVIDENCE, SUBMIT_EXPLANATION, CONFIRM_VALID, RECORD_CORRECTION, CLOSE_CASE, REOPEN_CASE")
    mandatory_reason: str = Field(..., min_length=10, max_length=2000, description="Mandatory detailed regulatory rationale")
    evidence_references: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata linking evidence documents or correction submissions")

