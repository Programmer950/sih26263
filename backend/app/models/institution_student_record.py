"""Institution-Specific Student Record Model."""

from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.models.base import Base, TimestampMixin


class InstitutionStudentRecord(Base, TimestampMixin):
    __tablename__ = "institution_student_records"
    __table_args__ = (
        UniqueConstraint("institution_id", "institution_student_id", name="uq_inst_student_id"),
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
    institution_student_id: Mapped[str] = mapped_column(String(100), nullable=False)
    programme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programmes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ENROLLED",
    )  # 'ENROLLED', 'TRANSFERRED', 'WITHDRAWN', 'GRADUATED', 'SUSPENDED'

    student_identity = relationship("StudentIdentity", back_populates="institution_records")
    institution = relationship("Institution")
    programme = relationship("Programme")

