"""Pydantic Schemas for Regulatory Approval Configurations and Intake Verification."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import uuid


class ApprovalCategoryAllocationBase(BaseModel):
    category_code: str = Field(..., max_length=50, description="Unique quota category code (e.g. TFW, EWS, MANAGEMENT_QUOTA, FN)")
    entry_level: str = Field(default="FIRST_YEAR", description="'FIRST_YEAR' or 'LATERAL_ENTRY_SECOND_YEAR'")
    allocation_type: str = Field(
        default="WITHIN_SANCTIONED_INTAKE",
        description="'WITHIN_SANCTIONED_INTAKE', 'ADDITIONAL_SUPERNUMERARY', 'INDEPENDENT_CAP', or 'INFORMATIONAL_ONLY'",
    )
    allocation_basis: str = Field(default="PERCENTAGE", description="'PERCENTAGE' or 'FIXED_SEATS'")
    allocated_value: float = Field(..., ge=0.0, description="Percentage (e.g. 5.0 for 5%) or fixed seat count (e.g. 10.0)")
    rounding_method: str = Field(
        default="FLOOR",
        description="'FLOOR', 'CEILING', 'ROUND_HALF_UP', or 'EXPLICIT_FIXED_CAP'",
    )
    denominator_basis: Optional[str] = Field(
        default="SANCTIONED_INTAKE",
        description="'SANCTIONED_INTAKE', 'ACTUAL_ENROLMENT', 'PRIOR_YEAR_VACANCY', or 'NONE'",
    )
    policy_clause: Optional[str] = Field(None, max_length=100, description="AICTE Approval Process Handbook reference clause")


class ApprovalCategoryAllocationCreate(ApprovalCategoryAllocationBase):
    pass


class ApprovalCategoryAllocationResponse(ApprovalCategoryAllocationBase):
    id: uuid.UUID
    approval_configuration_id: uuid.UUID
    calculated_seat_cap: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalConfigurationCreate(BaseModel):
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str = Field(..., max_length=20, pattern=r"^\d{4}(-[A-Za-z0-9\-]+)?$", description="e.g. 2024-25")
    approved_intake: int = Field(..., gt=0, description="Sanctioned annual regular intake (> 0)")
    approval_reference: str = Field(..., max_length=100, description="Official EoA letter order number")
    issuing_authority: str = Field(default="AICTE", max_length=100)
    approval_letter_date: Optional[date] = None
    effective_from: date
    effective_to: date
    supernumerary_quota_percentage: float = Field(default=15.0, ge=0.0, le=100.0)
    lateral_entry_quota_percentage: float = Field(default=10.0, ge=0.0, le=100.0)
    category_allocations: Optional[List[ApprovalCategoryAllocationCreate]] = Field(default_factory=list)


class ApprovalConfigurationAmend(BaseModel):
    amendment_reason: str = Field(..., min_length=10, description="Mandatory justification for regulatory quota amendment")
    approved_intake: Optional[int] = Field(None, gt=0)
    approval_reference: Optional[str] = Field(None, max_length=100)
    issuing_authority: Optional[str] = Field(None, max_length=100)
    approval_letter_date: Optional[date] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    supernumerary_quota_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    lateral_entry_quota_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    category_allocations: Optional[List[ApprovalCategoryAllocationCreate]] = None


class ApprovalConfigurationRevoke(BaseModel):
    revocation_reason: str = Field(..., min_length=10, description="Mandatory regulatory revocation justification")


class ApprovalConfigurationResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    approved_intake: int
    supernumerary_quota_percentage: float
    lateral_entry_quota_percentage: float
    approval_reference: str
    issuing_authority: str
    approval_letter_date: Optional[date] = None
    effective_from: date
    effective_to: date
    configuration_version: int
    status: str
    amendment_reason: Optional[str] = None
    superseded_by_id: Optional[uuid.UUID] = None
    superseded_at: Optional[datetime] = None
    created_by_user_id: Optional[uuid.UUID] = None
    amended_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime
    category_allocations: List[ApprovalCategoryAllocationResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class IntakeReconciliationRequest(BaseModel):
    candidate_snapshot_id: uuid.UUID
    baseline_snapshot_id: Optional[uuid.UUID] = None
    parameters: Optional[Dict[str, Any]] = None


class CategoryComplianceResult(BaseModel):
    category_code: str
    entry_level: str
    allocation_type: str
    approved_limit: Optional[int] = None
    observed_count: int
    variance: Optional[int] = None
    status: str  # 'COMPLIANT', 'EXCEPTION_FOUND', 'INSUFFICIENT_INFORMATION'
    notes: Optional[str] = None


class IntakeReconciliationSummaryResponse(BaseModel):
    id: uuid.UUID
    reconciliation_run_id: uuid.UUID
    approval_configuration_id: Optional[uuid.UUID] = None
    approval_configuration_version: Optional[int] = None
    compliance_status: str  # 'COMPLIANT', 'EXCEPTION_FOUND', 'INSUFFICIENT_INFORMATION', 'PARTIALLY_EVALUATED'
    regular_approved_intake: int
    regular_enrolled_count: int
    regular_variance: int
    supernumerary_total_cap: int
    supernumerary_enrolled_count: int
    supernumerary_variance: int
    lateral_entry_approved_cap: Optional[int] = None
    lateral_entry_enrolled_count: int
    lateral_entry_variance: Optional[int] = None
    unclassified_count: int = 0
    category_breakdown: List[CategoryComplianceResult] = Field(default_factory=list)
    category_breakdown_json: Dict[str, Any] = Field(default_factory=dict)
    discrepancy_cases_created: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
