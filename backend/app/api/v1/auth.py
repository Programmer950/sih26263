"""Authentication Routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.core.permissions import get_current_user
from app.models import User, SessionRevocation, AuditEvent
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    UserSummary,
    UserProfileResponse,
    LogoutResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(
    req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticates user using Argon2id password verification.
    Generates a short-lived access token with server-side trackable JTI.
    """
    user = db.execute(
        select(User).where(User.email == req.email.strip().lower())
    ).scalar_one_or_none()

    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated or suspended.",
        )

    # Update login timestamp
    now = datetime.now(timezone.utc)
    user.last_login_at = now

    # Issue short-lived access token with unique JTI
    claims = {
        "email": user.email,
        "name": user.name,
        "role": user.role.role_name,
        "institution_id": str(user.institution_id) if user.institution_id else None,
    }
    token_str, jti, expire_dt = create_access_token(
        subject=str(user.id),
        claims=claims,
    )

    db.commit()

    return LoginResponse(
        access_token=token_str,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserSummary(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role.role_name,
            institution_id=user.institution_id,
            institution_name=user.institution.name if user.institution else None,
            institution_code=user.institution.institution_code if user.institution else None,
        ),
    )


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Retrieves session profile and permissions for the active user."""
    return UserProfileResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role.role_name,
        institution_id=current_user.institution_id,
        institution_name=current_user.institution.name if current_user.institution else None,
        institution_code=current_user.institution.institution_code if current_user.institution else None,
        permissions=current_user.role.permissions,
        last_login_at=current_user.last_login_at,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Terminates the user session immediately by recording the access token's JTI
    in the session_revocations table.
    """
    jti = getattr(current_user, "_current_token_jti", None)
    exp = getattr(current_user, "_current_token_exp", None)

    if jti and exp:
        revocation = SessionRevocation(
            user_id=current_user.id,
            jti=jti,
            revocation_reason="Explicit user logout",
            expires_at=exp,
        )
        db.add(revocation)
        db.commit()

    return LogoutResponse()

