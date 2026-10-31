"""Discrepancy Case Decision Model."""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now


class DiscrepancyCaseDecision(Base):
    """
    Append-only chronological decision record for a discrepancy investigation case.
    Preserves actor justification, state change, and cryptographic audit linkage.
    """
    __tablename__ = "discrepancy_case_decisions"
    __table_args__ = (
        Index("idx_case_decisions_case", "discrepancy_case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    discrepancy_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discrepancy_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )

    from_status: Mapped[str] = mapped_column(String(50), nullable=False)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    mandatory_reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_references: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    decided_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    audit_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    # Relationships
    discrepancy_case = relationship("DiscrepancyCase", back_populates="decisions")
    decided_by = relationship("User", foreign_keys=[decided_by_user_id])
    audit_event = relationship("AuditEvent", foreign_keys=[audit_event_id])

