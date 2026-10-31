"""Schemas for Regulatory & Institutional Dashboards and Analytics."""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ProgrammeEnrolmentMetric(BaseModel):
    programme_id: uuid.UUID
    programme_name: str
    enrolled_count: int
    approved_intake: Optional[int] = None
    variance: Optional[int] = None


class AcademicYearEnrolmentMetric(BaseModel):
    academic_year: str
    enrolled_count: int


class DashboardSummaryResponse(BaseModel):
    institution_id: Optional[uuid.UUID] = None
    institution_name: Optional[str] = None
    role_scope: str  # 'INSTITUTION' or 'SYSTEM_WIDE'
    total_registered_students: int
    total_institutions: int
    total_programmes: int
    total_submissions: int
    total_snapshots: int
    total_discrepancy_cases: int
    open_discrepancies_count: int
    resolved_discrepancies_count: int
    apaar_coverage_percentage: float
    intake_compliance_rate: float
    enrolment_by_programme: List[ProgrammeEnrolmentMetric] = Field(default_factory=list)
    enrolment_by_academic_year: List[AcademicYearEnrolmentMetric] = Field(default_factory=list)
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)


class ReportExportRequest(BaseModel):
    report_type: str  # 'INSTITUTION_ENROLMENT', 'PROGRAMME_ENROLMENT', 'APAAR_VERIFICATION', 'INTAKE_COMPLIANCE', 'DUPLICATE_CANDIDATES', 'COHORT_RECONCILIATION', 'DISCREPANCY_RESOLUTION', 'REGULATORY_OVERVIEW'
    academic_year: Optional[str] = None
    institution_id: Optional[uuid.UUID] = None
    programme_id: Optional[uuid.UUID] = None
    format: str = "json"  # 'json' or 'csv'

