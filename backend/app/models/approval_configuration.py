"""Approval Configuration Model."""

from sqlalchemy import (
    String,
    Integer,
    Numeric,
    Date,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date, datetime
import uuid
from app.models.base import Base, utc_now


class ApprovalConfiguration(Base):
    """
    Statutory AICTE/DTE approval configuration for an institution programme in an academic year.
    Strictly versioned and immutable once referenced by reconciliation runs.
    """
    __tablename__ = "approval_configurations"
    __table_args__ = (
        UniqueConstraint("programme_id", "academic_year", "configuration_version", name="uq_approval_config_version"),
        CheckConstraint("effective_to >= effective_from", name="chk_approval_dates"),
        CheckConstraint("approved_intake > 0", name="chk_positive_intake"),
        Index(
            "uq_active_approval_config",
            "institution_id",
            "programme_id",
            "academic_year",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # e.g. '2024-25'
    approved_intake: Mapped[int] = mapped_column(Integer, nullable=False)
    supernumerary_quota_percentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=15.00)
    lateral_entry_quota_percentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=10.00)
    approval_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    issuing_authority: Mapped[str] = mapped_column(String(100), nullable=False, default="AICTE")
    approval_letter_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date] = mapped_column(Date, nullable=False)
    configuration_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")  # 'ACTIVE', 'SUPERSEDED', 'REVOKED'
    amendment_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_configurations.id", ondelete="SET NULL"),
        nullable=True,
    )
    superseded_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    amended_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    institution = relationship("Institution", back_populates="approval_configurations")
    programme = relationship("Programme", back_populates="approval_configurations")
    category_allocations = relationship(
        "ApprovalCategoryAllocation",
        back_populates="approval_configuration",
        cascade="all, delete-orphan",
        order_by="ApprovalCategoryAllocation.category_code.asc()",
    )
    superseded_by = relationship("ApprovalConfiguration", remote_side=[id], foreign_keys=[superseded_by_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    amended_by = relationship("User", foreign_keys=[amended_by_user_id])
