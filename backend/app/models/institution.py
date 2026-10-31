"""Institution Model."""

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.models.base import Base, TimestampMixin


class Institution(Base, TimestampMixin):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    institution_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # 'ENGINEERING', 'POLYTECHNIC', 'MANAGEMENT'
    approval_status: Mapped[str] = mapped_column(String(50), nullable=False, default="APPROVED")
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users = relationship("User", back_populates="institution")
    programmes = relationship("Programme", back_populates="institution")
    approval_configurations = relationship("ApprovalConfiguration", back_populates="institution")

