"""Historical Aggregate Reconciliation (PRD Module 9).

Revision ID: 0007_aggregate_reconcile
Revises: 0006_verification_requests
Create Date: 2026-10-31 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0007_aggregate_reconcile'
down_revision: Union[str, None] = '0006_verification_requests'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table already created in partial attempt
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'aggregate_enrolment_declarations' not in tables:
        op.create_table(
            'aggregate_enrolment_declarations',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='CASCADE'), nullable=False),
            sa.Column('academic_year', sa.String(20), nullable=False),
            sa.Column('reporting_period', sa.String(50), nullable=False, server_default='ANNUAL_FINAL'),
            sa.Column('declared_count', sa.Integer(), nullable=False),
            sa.Column('population_definition', sa.String(100), nullable=False, server_default='ALL_ENROLLED_REGULAR'),
            sa.Column('student_status_definition', sa.String(100), nullable=False, server_default='ACTIVE_ON_ROLL'),
            sa.Column('counting_methodology', sa.String(100), nullable=False, server_default='HEADCOUNT'),
            sa.Column('reporting_source', sa.String(100), nullable=False, server_default='AICTE_MANDATORY_DISCLOSURE'),
            sa.Column('source_reference', sa.String(150), nullable=True),
            sa.Column('declaration_date', sa.Date(), nullable=False, server_default=sa.func.current_date()),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('ix_agg_decl_inst_id', 'aggregate_enrolment_declarations', ['institution_id'])
        op.create_index('ix_agg_decl_prog_id', 'aggregate_enrolment_declarations', ['programme_id'])
        op.create_index('ix_agg_decl_ay', 'aggregate_enrolment_declarations', ['academic_year'])
        op.create_index('ix_agg_decl_inst_prog_ay', 'aggregate_enrolment_declarations', ['institution_id', 'programme_id', 'academic_year'])


def downgrade() -> None:
    op.drop_table('aggregate_enrolment_declarations')

