"""Student API Schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import uuid


class StudentRegisterRequest(BaseModel):
    institution_student_id: str = Field(..., max_length=100)
    full_name: str = Field(..., max_length=255)
    programme_id: uuid.UUID
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")  # '2024-25'
    admission_date: date
    apaar_id: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    admission_category: str = Field(default="REGULAR", max_length=50)
    supernumerary_status: bool = False
    nri_status: bool = False


class StudentSummary(BaseModel):
    id: uuid.UUID
    internal_student_uuid: uuid.UUID
    full_name: str
    masked_apaar_reference: Optional[str] = None
    identity_status: str
    institution_id: uuid.UUID
    institution_name: str
    institution_student_id: str
    programme_id: uuid.UUID
    programme_code: str
    programme_name: str
    status: str
    latest_academic_year: str


class PaginatedStudentsResponse(BaseModel):
    items: List[StudentSummary]
    total: int
    page: int
    limit: int
    pages: int


class StudentTimelineResponse(BaseModel):
    identity: Dict[str, Any]
    institutions_enrolled: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]

