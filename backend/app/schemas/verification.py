"""Schemas for Authorised Student Verification and Minimal Field Disclosure."""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class VerificationRequestCreate(BaseModel):
    apaar_id: str = Field(..., description="12-digit numeric APAAR or student identifier reference")
    stated_purpose: str = Field(..., description="Mandatory stated purpose for background verification")
    consent_confirmed: bool = Field(..., description="Mandatory confirmation of candidate consent")
    organization_name: Optional[str] = Field(None, description="Requesting organization or employer")
    verifier_name: Optional[str] = Field(None, description="Verifier name or employee reference")

    @field_validator("stated_purpose")
    @classmethod
    def validate_purpose_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Stated purpose cannot be empty or whitespace only.")
        return v.strip()


class DisclosedStudentRecord(BaseModel):
    student_name: str
    masked_apaar: str
    institution_name: str
    programme_name: str
    academic_year: str
    enrolment_status: str = "ACTIVE"
    supported_status: str = "ENROLLED"


class VerificationRequestResponse(BaseModel):
    verification_reference: str
    status: str  # 'VERIFIED', 'NOT_FOUND', 'UNAVAILABLE', 'EXPIRED', 'REVOKED'
    token: Optional[str] = None
    qr_payload: Optional[str] = None
    disclosed_record: Optional[DisclosedStudentRecord] = None
    message: Optional[str] = None
    expires_at: Optional[datetime] = None


class QRVerificationResponse(BaseModel):
    valid: bool
    status: str  # 'VERIFIED', 'INVALID', 'EXPIRED', 'REVOKED'
    reason: Optional[str] = None
    verification_reference: Optional[str] = None
    disclosed_record: Optional[DisclosedStudentRecord] = None
    verified_at: Optional[datetime] = None
