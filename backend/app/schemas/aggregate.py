"""Schemas for Historical Aggregate Enrolment Reconciliation (PRD Module 9)."""

import uuid
from typing import Optional, List, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator


class AggregateDeclarationCreate(BaseModel):
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str = Field(..., description="e.g. 2024-25")
    reporting_period: str = Field("ANNUAL_FINAL", description="Reporting period")
    declared_count: int = Field(..., ge=0, description="Total declared count")
    population_definition: str = Field("ALL_ENROLLED_REGULAR", description="Population scope")
    student_status_definition: str = Field("ACTIVE_ON_ROLL", description="Status definition")
    counting_methodology: str = Field("HEADCOUNT", description="Counting methodology")
    reporting_source: str = Field("AICTE_MANDATORY_DISCLOSURE", description="Source declaration type")
    source_reference: Optional[str] = Field(None, description="External reference")
    declaration_date: Optional[date] = None


class AggregateDeclarationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    reporting_period: str
    declared_count: int
    population_definition: str
    student_status_definition: str
    counting_methodology: str
    reporting_source: str
    source_reference: Optional[str]
    declaration_date: date
    created_at: datetime


class AggregateReconciliationRequest(BaseModel):
    declaration_id: uuid.UUID
    roster_snapshot_id: Optional[uuid.UUID] = None
    snapshot_id: Optional[uuid.UUID] = None
    generate_discrepancy_on_variance: Optional[bool] = True

    @model_validator(mode="before")
    @classmethod
    def populate_snapshot_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("roster_snapshot_id") and data.get("snapshot_id"):
                data["roster_snapshot_id"] = data["snapshot_id"]
            elif not data.get("snapshot_id") and data.get("roster_snapshot_id"):
                data["snapshot_id"] = data["roster_snapshot_id"]
        return data

    @model_validator(mode="after")
    def validate_snapshot_id(self) -> "AggregateReconciliationRequest":
        if not self.roster_snapshot_id and not self.snapshot_id:
            raise ValueError("roster_snapshot_id or snapshot_id is required")
        if not self.roster_snapshot_id:
            self.roster_snapshot_id = self.snapshot_id
        if not self.snapshot_id:
            self.snapshot_id = self.roster_snapshot_id
        return self


class AggregateReconciliationResult(BaseModel):
    declaration_id: uuid.UUID
    roster_snapshot_id: uuid.UUID
    snapshot_id: Optional[uuid.UUID] = None
    reconciliation_run_id: Optional[uuid.UUID] = None
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    comparability_status: str  # COMPARABLE or NON_COMPARABLE
    declared_count: int
    roster_count: int
    variance: int  # roster_count - declared_count
    outcome_status: str  # EXACT_MATCH, ROSTER_EXCESS, DECLARED_EXCESS, INCOMPARABLE
    reconciliation_status: Optional[str] = None  # MATCH, DISCREPANT, NON_COMPARABLE
    discrepancy_case_id: Optional[uuid.UUID] = None
    explanation: str
    source_references: List[str]
    reconciliation_timestamp: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("snapshot_id") and data.get("roster_snapshot_id"):
                data["snapshot_id"] = data["roster_snapshot_id"]
            if not data.get("reconciliation_status") and data.get("outcome_status"):
                st = data["outcome_status"]
                if st == "EXACT_MATCH":
                    data["reconciliation_status"] = "MATCH"
                elif st == "INCOMPARABLE":
                    data["reconciliation_status"] = "NON_COMPARABLE"
                else:
                    data["reconciliation_status"] = "DISCREPANT"
        return data
