"""Discrepancy Case Model."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now


class DiscrepancyCase(Base):
    """
    Persistent investigation case for student trajectory discrepancies requiring regulatory review.
    Supports both individual student-level trajectory findings and collective programme-level intake excess cases.
    """
    __tablename__ = "discrepancy_cases"
    __table_args__ = (
        Index("idx_discrepancy_cases_inst_status", "institution_id", "case_status"),
        Index("idx_discrepancy_cases_student", "student_identity_id"),
        Index("idx_discrepancy_cases_lineage", "institution_id", "programme_id", "student_identity_id", "classification"),
        Index("idx_discrepancy_cases_scope", "scope_type", "institution_id", "programme_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, default="STUDENT")  # 'STUDENT', 'PROGRAMME', 'INSTITUTION'
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

    # Nullable for programme/institution level intake excess cases
    student_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_identities.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # Structured intake metrics (Decision 1)
    observed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    excess_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    approval_configuration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_configurations.id", ondelete="SET NULL"),
        nullable=True,
    )
    approval_configuration_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_context_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    initial_reconciliation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reconciliation_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    latest_reconciliation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reconciliation_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    linked_prior_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discrepancy_cases.id", ondelete="SET NULL"),
        nullable=True,
    )

    classification: Mapped[str] = mapped_column(String(50), nullable=False)
    review_priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    case_status: Mapped[str] = mapped_column(String(50), nullable=False, default="OPEN")
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    # Relationships
    institution = relationship("Institution", foreign_keys=[institution_id])
    programme = relationship("Programme", foreign_keys=[programme_id])
    student_identity = relationship("StudentIdentity", foreign_keys=[student_identity_id])
    initial_run = relationship("ReconciliationRun", foreign_keys=[initial_reconciliation_run_id])
    latest_run = relationship("ReconciliationRun", foreign_keys=[latest_reconciliation_run_id])
    linked_prior_case = relationship("DiscrepancyCase", remote_side=[id], foreign_keys=[linked_prior_case_id])
    approval_configuration = relationship("ApprovalConfiguration", foreign_keys=[approval_configuration_id])
    source_submission = relationship("SourceSubmission", foreign_keys=[source_submission_id])
    decisions = relationship("DiscrepancyCaseDecision", back_populates="discrepancy_case", cascade="all, delete-orphan", order_by="DiscrepancyCaseDecision.created_at.asc()")
    result_items = relationship("ReconciliationResultItem", back_populates="discrepancy_case")
