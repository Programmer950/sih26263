"""Programme Model."""

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.models.base import Base, TimestampMixin


class Programme(Base, TimestampMixin):
    __tablename__ = "programmes"
    __table_args__ = (
        UniqueConstraint("institution_id", "programme_code", name="uq_institution_programme"),
        UniqueConstraint("institution_id", "id", name="uq_institution_programme_id"),
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
    programme_code: Mapped[str] = mapped_column(String(50), nullable=False)
    programme_name: Mapped[str] = mapped_column(String(255), nullable=False)
    qualification_level: Mapped[str] = mapped_column(String(50), nullable=False)  # 'DIPLOMA', 'UG', 'PG'
    duration_years: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")

    institution = relationship("Institution", back_populates="programmes")
    approval_configurations = relationship("ApprovalConfiguration", back_populates="programme")

