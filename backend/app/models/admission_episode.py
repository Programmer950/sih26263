"""Admission Episode Model."""

from sqlalchemy import String, Date, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime
import uuid
from app.models.base import Base, utc_now


class AdmissionEpisode(Base):
    __tablename__ = "admission_episodes"
    __table_args__ = (
        Index("idx_admission_episodes_seat_cat", "programme_id", "academic_year", "seat_accounting_category"),
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
    admission_date: Mapped[date] = mapped_column(Date, nullable=False)

    # 1. Classification Dimensions (Decisions 1 & 4)
    nationality_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="INDIAN_DOMICILE",
    )  # 'INDIAN_DOMICILE', 'NRI', 'OCI', 'PIO', 'FOREIGN_NATIONAL'

    admission_channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="CENTRALIZED_COUNSELING",
    )  # 'CENTRALIZED_COUNSELING', 'INSTITUTIONAL_MERIT', 'MANAGEMENT_QUOTA', 'GOVERNMENT_NOMINATION', 'DIRECT_ADMISSION'

    seat_accounting_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REGULAR",
    )  # 'REGULAR', 'TFW', 'EWS', 'NRI', 'OCI_PIO', 'FOREIGN_NATIONAL', 'PMSSS', 'MANAGEMENT_QUOTA', 'UNCLASSIFIED_SEAT_CATEGORY'

    entry_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="FIRST_YEAR",
    )  # 'FIRST_YEAR', 'LATERAL_ENTRY_SECOND_YEAR', 'TRANSFER_IN'

    applicable_approval_rule_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Legacy compatibility fields preserved
    admission_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REGULAR",
    )
    supernumerary_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    nri_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    oci_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    foreign_national_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    source_submission_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    student_identity = relationship("StudentIdentity", back_populates="admission_episodes")
    institution = relationship("Institution")
    programme = relationship("Programme")
