"""Source Submission Record Model."""

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from app.models.base import Base, utc_now


class SourceSubmissionRecord(Base):
    """
    Immutable row-level storage preserving complete raw source evidence
    and provenance for every parsed record.
    """
    __tablename__ = "source_submission_records"
    __table_args__ = (
        UniqueConstraint("submission_id", "row_number", name="uq_submission_record_row"),
        UniqueConstraint("id", "submission_id", name="uq_submission_record_composite"),
        Index("idx_submission_records_subid", "submission_id"),
        Index("idx_submission_records_identity", "resolved_student_identity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_submissions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)  # Verbatim cell data (formulas unmutated)
    parsed_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)  # Normalized dictionary
    formula_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    validation_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="VALID",
    )  # 'VALID', 'WARNING', 'INVALID', 'DUPLICATE'

    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    mapping_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0")

    resolved_student_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_identities.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_institution_student_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institution_student_records.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    submission = relationship("SourceSubmission", back_populates="records")
    student_identity = relationship("StudentIdentity")
    institution_record = relationship("InstitutionStudentRecord")

