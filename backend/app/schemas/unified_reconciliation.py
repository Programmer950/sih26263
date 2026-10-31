"""Schemas for Unified Reconciliation and Cross-Institution Duplicate Detection."""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field


class EnrolmentInstitutionContext(BaseModel):
    institution_id: uuid.UUID
    institution_name: str
    programme_id: uuid.UUID
    programme_name: str
    academic_year: str
    snapshot_id: Optional[uuid.UUID] = None
    submission_id: Optional[uuid.UUID] = None
    admission_date: Optional[date] = None
    exit_date: Optional[date] = None
    entry_level: Optional[str] = "FIRST_YEAR"
    seat_accounting_category: Optional[str] = "REGULAR"
    student_status: Optional[str] = "ACTIVE"


class DuplicateConflictItem(BaseModel):
    id: uuid.UUID
    student_identity_id: uuid.UUID
    masked_apaar_reference: Optional[str] = None
    full_name: str
    blind_index: str
    blind_index_version: str = "v1-apaar-sha256"
    identity_verification_status: str
    academic_year: str
    conflict_type: str  # CONCURRENT_DUAL_ENROLMENT, LEGITIMATE_TRANSFER, UNRESOLVED_TRANSFER, INSUFFICIENT_EVIDENCE
    review_priority: str  # HIGH, MEDIUM, LOW, INFO
    enrolments: List[EnrolmentInstitutionContext]
    transfer_event_id: Optional[uuid.UUID] = None
    is_verified_transfer: bool = False
    discrepancy_case_id: Optional[uuid.UUID] = None
    evidence_summary: str


class UnifiedReconciliationRequest(BaseModel):
    snapshot_id: uuid.UUID
    baseline_snapshot_id: Optional[uuid.UUID] = None
    approval_config_id: Optional[uuid.UUID] = None


class UnifiedCohortSummary(BaseModel):
    reconciliation_run_id: uuid.UUID
    candidate_snapshot_id: uuid.UUID
    baseline_snapshot_id: Optional[uuid.UUID] = None
    total_candidate_observations: int
    continuing_count: int
    added_count: int
    documented_transfer_count: int
    unexplained_appearance_count: int
    ambiguous_identity_count: int
    insufficient_evidence_count: int
    baseline_disappearances: Dict[str, int] = Field(default_factory=dict)
    engine_version: str
    rules_version: str
    run_status: str


class UnifiedIntakeSummary(BaseModel):
    intake_summary_id: Optional[uuid.UUID] = None
    approval_configuration_id: Optional[uuid.UUID] = None
    approval_configuration_version: Optional[int] = None
    approved_intake: int
    enrolled_count: int
    variance: int
    compliance_status: str
    category_results: List[Dict[str, Any]] = Field(default_factory=list)
    engine_version: str
    rules_version: str


class UnifiedReconciliationResponse(BaseModel):
    reconciliation_run_id: uuid.UUID
    snapshot_id: uuid.UUID
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    status: str
    cohort_summary: UnifiedCohortSummary
    intake_summary: Optional[UnifiedIntakeSummary] = None
    duplicate_candidates: List[DuplicateConflictItem] = Field(default_factory=list)
    discrepancy_cases_created: List[Dict[str, Any]] = Field(default_factory=list)
    executed_at: datetime

