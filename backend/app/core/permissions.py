"""Authentication & Multi-Tenant Authorization Dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
import uuid
import jwt

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, SessionRevocation

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Validates JWT token, verifies token has not been revoked in session_revocations,
    and returns the active authenticated User entity.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    revoked_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session has been terminated. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        jti: str = payload.get("jti")
        if user_id_str is None or jti is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    # Check server-side jti session revocation table
    revocation = db.execute(
        select(SessionRevocation).where(
            SessionRevocation.jti == jti,
            SessionRevocation.expires_at > datetime.now(timezone.utc),
        )
    ).scalar_one_or_none()

    if revocation is not None:
        raise revoked_exception

    # Retrieve user from database
    user = db.execute(
        select(User).where(User.id == user_id, User.status == "ACTIVE")
    ).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive or not found.",
        )

    # Attach token JTI to user object for easy logout reference
    user._current_token_jti = jti
    user._current_token_exp = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
    return user


def require_roles(*allowed_roles: str):
    """Factory dependency enforcing that the user possesses one of the specified roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role.role_name
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}. Current role: {user_role}",
            )
        return current_user

    return role_checker


class TenantGuard:
    """
    Enforces object-level tenant isolation.
    Institution Administrators are strictly constrained to their own institution_id.
    """
    def __init__(self, current_user: User = Depends(get_current_user)):
        self.user = current_user
        self.role_name = current_user.role.role_name
        self.institution_id = current_user.institution_id

    def scope_institution_id(self, requested_institution_id: uuid.UUID | None = None) -> uuid.UUID | None:
        """
        Resolves the authorized institution_id:
        - For INSTITUTION_ADMIN: ALWAYS returns self.institution_id.
          Silently ignores or rejects unauthorized requests for other institutions.
        - For REGULATORY_REVIEWER or SYSTEM_ADMIN: returns requested_institution_id (or None for global).
        """
        if self.role_name == "INSTITUTION_ADMIN":
            if requested_institution_id and requested_institution_id != self.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tenancy Violation: Institution Administrators cannot query external institutional records.",
                )
            return self.institution_id

        # Reviewers and System Admins may query any or all institutions
        return requested_institution_id

