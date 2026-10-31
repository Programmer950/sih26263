"""Student Verification & QR Disclosure API Router."""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user, require_roles
from app.models import User
from app.schemas.verification import (
    VerificationRequestCreate,
    VerificationRequestResponse,
    QRVerificationResponse,
)
from app.services.verification_service import VerificationService

logger = logging.getLogger("apaar_setu.verification_api")

router = APIRouter(prefix="/verification", tags=["Verification"])


@router.post("/request", response_model=VerificationRequestResponse, status_code=status.HTTP_200_OK)
def create_verification_request(
    req: VerificationRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submits an authorized external student verification request with mandatory stated purpose
    and candidate consent. Enforces minimal field disclosure whitelist.
    """
    return VerificationService.request_verification(
        db=db,
        req=req,
        actor=current_user,
    )


@router.get("/qr", response_model=QRVerificationResponse, status_code=status.HTTP_200_OK)
@router.get("/qr/", response_model=QRVerificationResponse, status_code=status.HTTP_200_OK)
def verify_via_empty_qr_token():
    return QRVerificationResponse(
        valid=False,
        status="INVALID",
        reason="Verification token is missing or empty.",
    )


@router.get("/qr/{token}", response_model=QRVerificationResponse, status_code=status.HTTP_200_OK)
def verify_via_qr_token(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Public QR verification validation endpoint.
    Validates token authenticity, expiration, and revocation with minimal field disclosure.
    """
    if not token or not token.strip():
        return QRVerificationResponse(
            valid=False,
            status="INVALID",
            reason="Verification token is missing or empty.",
        )
    return VerificationService.verify_qr_token(
        db=db,
        token=token.strip(),
    )

