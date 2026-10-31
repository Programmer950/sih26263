"""Approval Category Allocation Model."""

import uuid
from datetime import datetime
from sqlalchemy import String, Numeric, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now


class ApprovalCategoryAllocation(Base):
    """
    Explicit quota allocations attached to a specific versioned ApprovalConfiguration.
    Enforces the four canonical allocation types, entry levels, and rounding methods
    without hardcoded universal formulas.
    """
    __tablename__ = "approval_category_allocations"
    __table_args__ = (
        UniqueConstraint("approval_configuration_id", "category_code", "entry_level", name="uq_approval_category_entry_quota"),
        Index("idx_approval_category_config", "approval_configuration_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    approval_configuration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_configurations.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_code: Mapped[str] = mapped_column(String(50), nullable=False)
    entry_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="FIRST_YEAR",
    )  # 'FIRST_YEAR', 'LATERAL_ENTRY_SECOND_YEAR', 'ALL'
    allocation_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="WITHIN_SANCTIONED_INTAKE",
    )  # 'WITHIN_SANCTIONED_INTAKE', 'ADDITIONAL_SUPERNUMERARY', 'INDEPENDENT_CAP', 'INFORMATIONAL_ONLY'
    allocation_basis: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PERCENTAGE",
    )  # 'PERCENTAGE', 'FIXED_SEATS'
    allocated_value: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0.00)
    rounding_method: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="FLOOR",
    )  # 'FLOOR', 'CEILING', 'ROUND_HALF_UP', 'EXPLICIT_FIXED_CAP'
    denominator_basis: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 'SANCTIONED_INTAKE', 'ACTUAL_ENROLMENT', 'PRIOR_YEAR_VACANCY', 'NONE'
    calculated_seat_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_clause: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    approval_configuration = relationship("ApprovalConfiguration", back_populates="category_allocations")
