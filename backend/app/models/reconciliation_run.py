"""Reconciliation Run Model."""

import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now


class ReconciliationRun(Base):
    """
    Immutable record of a formal reconciliation comparison execution.
    Decoupled from ongoing case investigations.
    """
    __tablename__ = "reconciliation_runs"
    __table_args__ = (
        Index("idx_recon_runs_context", "institution_id", "programme_id", "academic_year"),
        Index("idx_recon_runs_candidate", "candidate_snapshot_id"),
        Index(
            "idx_uq_recon_run_idempotency",
            "institution_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
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

    candidate_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roster_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candidate_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    baseline_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roster_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    baseline_snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    run_type: Mapped[str] = mapped_column(String(50), nullable=False, default="REGULATORY_RECONCILIATION")
    execution_status: Mapped[str] = mapped_column(String(50), nullable=False, default="COMPLETED")
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0")
    rules_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0-rules-apaar-setu")
    result_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

    summary_counts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    parameters_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)

    initiated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    # Relationships
    institution = relationship("Institution", foreign_keys=[institution_id])
    programme = relationship("Programme", foreign_keys=[programme_id])
    candidate_snapshot = relationship("RosterSnapshot", foreign_keys=[candidate_snapshot_id])
    baseline_snapshot = relationship("RosterSnapshot", foreign_keys=[baseline_snapshot_id])
    initiated_by = relationship("User", foreign_keys=[initiated_by_user_id])
    result_items = relationship("ReconciliationResultItem", back_populates="reconciliation_run", cascade="all, delete-orphan")

