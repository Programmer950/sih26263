"""Historical Aggregate Enrolment Declaration Model."""

import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class AggregateEnrolmentDeclaration(Base):
    """
    PRD Module 9: Historical aggregate enrolment declarations submitted
    by institutions in past mandatory disclosures, annual reports, or AICTE filings.
    Used for historical aggregate-to-roster reconciliation.
    """
    __tablename__ = "aggregate_enrolment_declarations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    programme_id = Column(UUID(as_uuid=True), ForeignKey("programmes.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year = Column(String(20), nullable=False, index=True)
    reporting_period = Column(String(50), nullable=False, default="ANNUAL_FINAL")
    declared_count = Column(Integer, nullable=False)
    population_definition = Column(String(100), nullable=False, default="ALL_ENROLLED_REGULAR")
    student_status_definition = Column(String(100), nullable=False, default="ACTIVE_ON_ROLL")
    counting_methodology = Column(String(100), nullable=False, default="HEADCOUNT")
    reporting_source = Column(String(100), nullable=False, default="AICTE_MANDATORY_DISCLOSURE")
    source_reference = Column(String(150), nullable=True)
    declaration_date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    institution = relationship("Institution")
    programme = relationship("Programme")

    __table_args__ = (
        Index("ix_agg_decl_inst_prog_ay", "institution_id", "programme_id", "academic_year"),
    )

