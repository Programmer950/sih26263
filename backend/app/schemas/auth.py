"""Authentication Schemas."""

from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSummary(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    institution_id: Optional[uuid.UUID] = None
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # in seconds
    user: UserSummary


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    institution_id: Optional[uuid.UUID] = None
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    permissions: Dict[str, Any]
    last_login_at: Optional[datetime] = None


class LogoutResponse(BaseModel):
    success: bool = True
    message: str = "Session successfully terminated and token revoked."

