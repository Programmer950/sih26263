"""Intake Reconciliation Summary Model."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now


class IntakeReconciliationSummary(Base):
    """
    Summary breakdown of seat accounting and statutory quota adherence for an intake verification run.
    Stores regular variance, supernumerary breakdown, and lateral entry counts.
    """
    __tablename__ = "intake_reconciliation_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    reconciliation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reconciliation_runs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    approval_configuration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_configurations.id", ondelete="SET NULL"),
        nullable=True,
    )
    approval_configuration_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compliance_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="COMPLIANT",
    )  # 'COMPLIANT', 'INTAKE_EXCESS', 'INSUFFICIENT_INFORMATION'

    regular_approved_intake: Mapped[int] = mapped_column(Integer, nullable=False)
    regular_enrolled_count: Mapped[int] = mapped_column(Integer, nullable=False)
    regular_variance: Mapped[int] = mapped_column(Integer, nullable=False)

    supernumerary_total_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supernumerary_enrolled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supernumerary_variance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    lateral_entry_approved_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lateral_entry_enrolled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lateral_entry_variance: Mapped[int | None] = mapped_column(Integer, nullable=True)

    category_breakdown_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    reconciliation_run = relationship("ReconciliationRun")
    approval_configuration = relationship("ApprovalConfiguration")

