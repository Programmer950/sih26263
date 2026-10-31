"""Reconciliation Result Item Model."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now


class ReconciliationResultItem(Base):
    """
    Immutable student-level reconciliation outcome for all eight classifications.
    Maintains independent provenance for candidate and baseline observations.
    """
    __tablename__ = "reconciliation_result_items"
    __table_args__ = (
        Index("idx_recon_results_run", "reconciliation_run_id"),
        Index("idx_recon_results_classification", "reconciliation_run_id", "classification"),
        Index("idx_recon_results_student", "student_identity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    reconciliation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reconciliation_runs.id", ondelete="CASCADE"),
        nullable=False,
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

    student_identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_identities.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Independent Candidate Provenance (nullable where student absent from candidate)
    candidate_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("annual_roster_observations.id", ondelete="SET NULL"),
        nullable=True,
    )
    candidate_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    candidate_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Independent Baseline Provenance (nullable where student new in candidate)
    baseline_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("annual_roster_observations.id", ondelete="SET NULL"),
        nullable=True,
    )
    baseline_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    baseline_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    classification: Mapped[str] = mapped_column(String(50), nullable=False)
    review_priority: Mapped[str] = mapped_column(String(20), nullable=False, default="NONE")
    system_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    rules_version: Mapped[str] = mapped_column(String(50), nullable=False)

    is_case_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    discrepancy_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discrepancy_cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    # Relationships
    reconciliation_run = relationship("ReconciliationRun", back_populates="result_items")
    student_identity = relationship("StudentIdentity", foreign_keys=[student_identity_id])
    candidate_observation = relationship("AnnualRosterObservation", foreign_keys=[candidate_observation_id])
    baseline_observation = relationship("AnnualRosterObservation", foreign_keys=[baseline_observation_id])
    candidate_submission = relationship("SourceSubmission", foreign_keys=[candidate_submission_id])
    baseline_submission = relationship("SourceSubmission", foreign_keys=[baseline_submission_id])
    discrepancy_case = relationship("DiscrepancyCase", back_populates="result_items")

