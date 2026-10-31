"""Verification Request Model."""

from sqlalchemy import String, Text, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from app.models.base import Base, utc_now


class VerificationRequest(Base):
    """
    Stores external third-party student verification requests, stated purpose,
    consent confirmation, and issued cryptographically secure verification tokens.
    """
    __tablename__ = "verification_requests"
    __table_args__ = (
        Index("idx_verification_token_hash", "token_hash"),
        Index("idx_verification_reference", "verification_reference"),
        Index("idx_verification_requester", "requester_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    verification_reference: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    student_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_identities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requester_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verifier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stated_purpose: Mapped[str] = mapped_column(Text, nullable=False)
    consent_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="VERIFIED",
    )  # 'VERIFIED', 'NOT_FOUND', 'UNAVAILABLE', 'EXPIRED', 'REVOKED'
    disclosed_record_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    student_identity = relationship("StudentIdentity")
    requester = relationship("User")

