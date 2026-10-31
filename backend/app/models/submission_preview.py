"""Submission Preview Model."""

from sqlalchemy import String, Boolean, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from app.models.base import Base, utc_now


class SubmissionPreview(Base):
    """
    Immutable preview version binding reviewed column mappings, parser metadata,
    and validation summaries to subsequent confirmation.
    """
    __tablename__ = "submission_previews"
    __table_args__ = (
        # Safeguard 1: At most one active preview per submission
        Index(
            "uq_active_preview_per_submission",
            "submission_id",
            unique=True,
            postgresql_where=text("is_active = TRUE"),
        ),
        Index("idx_submission_previews_lookup", "submission_id", "is_active"),
        Index("idx_submission_previews_hash", "mapping_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    column_mapping: Mapped[dict] = mapped_column(JSONB, nullable=False)
    mapping_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0")
    mapping_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Version tracking safeguards
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False, default="openpyxl-v3.1.2/csv-std")
    validation_rules_version: Mapped[str] = mapped_column(String(50), nullable=False, default="rules-v2026.1")
    normalization_version: Mapped[str] = mapped_column(String(50), nullable=False, default="norm-v1.0")

    validation_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    submission = relationship("SourceSubmission", back_populates="previews")

