"""Annual Roster Observation Model."""

from sqlalchemy import String, ForeignKey, ForeignKeyConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from app.models.base import Base, utc_now


class AnnualRosterObservation(Base):
    """
    Preserves annual student observations across multiple submission versions.
    CRITICAL INVARIANT: No unique constraint across student/programme/academic year,
    allowing complete auditability across revisions.
    """
    __tablename__ = "annual_roster_observations"
    __table_args__ = (
        # Relational integrity constraint ensuring source record belongs to referenced submission:
        ForeignKeyConstraint(
            ["source_record_id", "source_submission_id"],
            ["source_submission_records.id", "source_submission_records.submission_id"],
            name="fk_roster_obs_source_record",
            ondelete="RESTRICT",
        ),
        # Relational integrity constraint ensuring observation matches submission context (institution, programme, year):
        ForeignKeyConstraint(
            ["source_submission_id", "institution_id", "programme_id", "academic_year"],
            ["source_submissions.id", "source_submissions.institution_id", "source_submissions.programme_id", "source_submissions.academic_year"],
            name="fk_roster_obs_context",
            ondelete="RESTRICT",
        ),
        Index("idx_roster_observations_timeline", "institution_id", "programme_id", "academic_year", "student_identity_id"),
        Index("idx_roster_observations_submission", "source_submission_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    student_identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_identities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    student_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
    )  # 'ACTIVE', 'DETAINED', 'ABSENT', 'ON_LEAVE'
    source_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_submissions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    observation_timestamp: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    observation_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    student_identity = relationship("StudentIdentity", back_populates="annual_observations")
    institution = relationship("Institution", foreign_keys=[institution_id])
    programme = relationship("Programme", foreign_keys=[programme_id])
    source_submission = relationship("SourceSubmission", foreign_keys=[source_submission_id])
    source_record = relationship("SourceSubmissionRecord", foreign_keys=[source_record_id])


