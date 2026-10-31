"""Source Submission Model."""

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from app.models.base import Base, TimestampMixin


class SourceSubmission(Base, TimestampMixin):
    """
    Immutable ledger of uploaded ingestion files, tenancy bindings,
    and finite state machine lifecycle transitions.
    """
    __tablename__ = "source_submissions"
    __table_args__ = (
        # Relational Integrity: Enforce programme belongs strictly to target institution
        ForeignKeyConstraint(
            ["institution_id", "programme_id"],
            ["programmes.institution_id", "programmes.id"],
            name="fk_submission_programme",
            ondelete="RESTRICT",
        ),
        # Composite Anchor: Enables child snapshots and observations to guarantee identical context
        UniqueConstraint(
            "id", "institution_id", "programme_id", "academic_year",
            name="uq_submission_relational_anchor",
        ),
        # Database-enforced tenant-scoped idempotency key uniqueness for non-null keys
        Index(
            "uq_source_submissions_tenant_idempotency",
            "institution_id",
            "client_idempotency_key",
            unique=True,
            postgresql_where=text("client_idempotency_key IS NOT NULL"),
        ),
        # Database-enforced retry-safe contextual deduplication:
        # Blocks duplicates while active or committed, permits retries after FAILED or CANCELLED:
        Index(
            "uq_active_context_fingerprint",
            "institution_id",
            "programme_id",
            "academic_year",
            "submission_type",
            "file_fingerprint",
            unique=True,
            postgresql_where=text("submission_status NOT IN ('FAILED', 'CANCELLED')"),
        ),
        Index("idx_submissions_lookup", "institution_id", "academic_year", "submission_type"),
        Index("idx_submissions_status", "submission_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    programme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programmes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    submission_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ANNUAL_ROSTER",
    )  # 'ANNUAL_ROSTER', 'ADMISSION_BATCH', 'CORRECTION'

    submission_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UPLOADED",
    )  # 'UPLOADED', 'VALIDATING', 'PREVIEW_READY', 'INGESTING', 'COMMITTED', 'VALIDATION_FAILED', 'FAILED', 'CANCELLED'

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    file_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)

    total_rows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_rows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    mapping_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    validation_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    committed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    institution = relationship("Institution", foreign_keys=[institution_id])
    programme = relationship("Programme", foreign_keys=[programme_id])
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])
    records = relationship("SourceSubmissionRecord", back_populates="submission")
    previews = relationship("SubmissionPreview", back_populates="submission")
