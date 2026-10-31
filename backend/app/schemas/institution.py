"""Institution and Programme API Schemas."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime
import uuid


# --- Programme Schemas ---
class ProgrammeCreate(BaseModel):
    programme_code: str = Field(..., max_length=50)
    programme_name: str = Field(..., max_length=255)
    qualification_level: str = Field(..., max_length=50)  # 'DIPLOMA', 'UG', 'PG'
    duration_years: int = Field(default=4, ge=1, le=6)


class ApprovalConfigCreate(BaseModel):
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")  # e.g. '2024-25'
    approved_intake: int = Field(..., gt=0)
    supernumerary_quota_percentage: float = Field(default=15.00, ge=0.0, le=50.0)
    lateral_entry_quota_percentage: float = Field(default=10.00, ge=0.0, le=50.0)
    approval_reference: str = Field(..., max_length=100)
    effective_from: date
    effective_to: date


class ApprovalConfigResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    programme_id: uuid.UUID
    academic_year: str
    approved_intake: int
    supernumerary_quota_percentage: float
    lateral_entry_quota_percentage: float
    approval_reference: str
    effective_from: date
    effective_to: date
    configuration_version: int
    status: str
    created_at: datetime


class ProgrammeResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    programme_code: str
    programme_name: str
    qualification_level: str
    duration_years: int
    status: str
    approved_intake: Optional[int] = None
    academic_year: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# --- Institution Schemas ---
class InstitutionCreate(BaseModel):
    institution_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    category: str = Field(..., max_length=50)  # 'ENGINEERING', 'POLYTECHNIC', 'UNIVERSITY'
    state: str = Field(..., max_length=100)
    district: str = Field(..., max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None


class InstitutionResponse(BaseModel):
    id: uuid.UUID
    institution_code: str
    name: str
    category: str
    approval_status: str
    state: str
    district: str
    pincode: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None
    programme_count: int = 0
    created_at: datetime
    updated_at: datetime


class PaginatedInstitutionsResponse(BaseModel):
    items: List[InstitutionResponse]
    total: int
    page: int
    limit: int
    pages: int

