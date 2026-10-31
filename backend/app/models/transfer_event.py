"""Transfer Event Model."""

from sqlalchemy import String, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime
import uuid
from app.models.base import Base, utc_now


class TransferEvent(Base):
    __tablename__ = "transfer_events"

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
    source_institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    destination_institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_programme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programmes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    destination_programme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programmes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    transfer_date: Mapped[date] = mapped_column(Date, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
    )  # 'PENDING', 'DOCUMENTED', 'REJECTED'
    evidence_reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    student_identity = relationship("StudentIdentity", back_populates="transfers")
    source_institution = relationship("Institution", foreign_keys=[source_institution_id])
    destination_institution = relationship("Institution", foreign_keys=[destination_institution_id])
    source_programme = relationship("Programme", foreign_keys=[source_programme_id])
    destination_programme = relationship("Programme", foreign_keys=[destination_programme_id])

