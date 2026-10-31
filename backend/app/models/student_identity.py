"""Student Identity Model."""

from sqlalchemy import String, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
import uuid
from app.models.base import Base, TimestampMixin


class StudentIdentity(Base, TimestampMixin):
    __tablename__ = "student_identities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    internal_student_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid.uuid4,
        index=True,
    )
    encrypted_apaar_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    masked_apaar_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    apaar_blind_index: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    identity_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UNVERIFIED",
    )  # 'MISSING_APAAR', 'FORMAT_VALID', 'EXTERNALLY_VERIFIED', 'DISPUTED'

    # Relationships
    institution_records = relationship("InstitutionStudentRecord", back_populates="student_identity")
    admission_episodes = relationship("AdmissionEpisode", back_populates="student_identity")
    annual_observations = relationship("AnnualRosterObservation", back_populates="student_identity")
    transfers = relationship("TransferEvent", back_populates="student_identity")

