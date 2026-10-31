"""Roster Snapshot Model."""

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
from datetime import datetime
import uuid
from app.models.base import Base, utc_now


class RosterSnapshot(Base):
    """
    Authoritative snapshot selection mechanism for reconciliation.
    Decouples raw multi-version observations from regulatory analysis.
    """
    __tablename__ = "roster_snapshots"
    __table_args__ = (
        # Relational Integrity: Enforce snapshot context matches source submission context
        ForeignKeyConstraint(
            ["source_submission_id", "institution_id", "programme_id", "academic_year"],
            ["source_submissions.id", "source_submissions.institution_id", "source_submissions.programme_id", "source_submissions.academic_year"],
            name="fk_snapshot_submission",
            ondelete="RESTRICT",
        ),
        # Consistency Constraint: Authoritative snapshot CANNOT be marked SUPERSEDED
        CheckConstraint(
            "NOT (is_authoritative = TRUE AND lifecycle_status = 'SUPERSEDED')",
            name="chk_authoritative_lifecycle",
        ),
        # Partial unique index guaranteeing at most ONE authoritative snapshot per institution, programme, year
        Index(
            "idx_uq_authoritative_snapshot",
            "institution_id",
            "programme_id",
            "academic_year",
            unique=True,
            postgresql_where=text("is_authoritative = TRUE"),
        ),
        Index("idx_snapshots_inst_prog_year", "institution_id", "programme_id", "academic_year"),
        Index("idx_snapshots_authoritative", "is_authoritative", "lifecycle_status"),
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
    )
    programme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programmes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    source_submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    completeness_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UNKNOWN",
    )  # 'COMPLETE', 'PARTIAL', 'UNKNOWN'

    lifecycle_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
    )  # 'ACTIVE', 'SUPERSEDED'

    is_authoritative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    declared_headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    observed_headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    record_count = synonym("observed_headcount")

    snapshot_canonicalization_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="v1-sha256-sorted-uuids",
    )
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_fingerprint_sha256 = synonym("snapshot_hash")
    snapshot_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    effective_from: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    superseded_by_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roster_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    superseded_at: Mapped[datetime | None] = mapped_column(nullable=True)

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    institution = relationship("Institution", foreign_keys=[institution_id])
    programme = relationship("Programme", foreign_keys=[programme_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    source_submission = relationship("SourceSubmission", foreign_keys=[source_submission_id])
