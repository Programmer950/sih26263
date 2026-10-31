"""Approval Intake Matrix, Versioning, Quotas, and Reconciliation Summaries (Milestone 4).

Revision ID: 0005_approval_intake_matrix
Revises: 0004_reconciliation_cases
Create Date: 2026-10-31 00:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0005_approval_intake_matrix'
down_revision: Union[str, None] = '0004_reconciliation_cases'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Enhance approval_configurations
    # -------------------------------------------------------------------------
    op.add_column('approval_configurations', sa.Column('issuing_authority', sa.String(100), nullable=False, server_default='AICTE'))
    op.add_column('approval_configurations', sa.Column('approval_letter_date', sa.Date(), nullable=True))
    op.add_column('approval_configurations', sa.Column('amendment_reason', sa.Text(), nullable=True))
    op.add_column('approval_configurations', sa.Column('superseded_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('approval_configurations.id', ondelete='SET NULL'), nullable=True))
    op.add_column('approval_configurations', sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('approval_configurations', sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=True))
    op.add_column('approval_configurations', sa.Column('amended_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=True))

    op.create_index(
        'uq_active_approval_config',
        'approval_configurations',
        ['institution_id', 'programme_id', 'academic_year'],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    # -------------------------------------------------------------------------
    # 2. Create approval_category_allocations table
    # -------------------------------------------------------------------------
    op.create_table(
        'approval_category_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('approval_configuration_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('approval_configurations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category_code', sa.String(50), nullable=False),
        sa.Column('entry_level', sa.String(30), nullable=False, server_default='FIRST_YEAR'),
        sa.Column('allocation_type', sa.String(30), nullable=False, server_default='WITHIN_SANCTIONED_INTAKE'),
        sa.Column('allocation_basis', sa.String(30), nullable=False, server_default='PERCENTAGE'),
        sa.Column('allocated_value', sa.Numeric(8, 2), nullable=False, server_default='0.00'),
        sa.Column('rounding_method', sa.String(30), nullable=False, server_default='FLOOR'),
        sa.Column('denominator_basis', sa.String(50), nullable=True),
        sa.Column('calculated_seat_cap', sa.Integer(), nullable=True),
        sa.Column('policy_clause', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('approval_configuration_id', 'category_code', 'entry_level', name='uq_approval_category_entry_quota'),
    )
    op.create_index('idx_approval_category_config', 'approval_category_allocations', ['approval_configuration_id'])

    # -------------------------------------------------------------------------
    # 3. Enhance discrepancy_cases table for programme-level findings
    # -------------------------------------------------------------------------
    op.alter_column('discrepancy_cases', 'student_identity_id', nullable=True)
    op.add_column('discrepancy_cases', sa.Column('scope_type', sa.String(20), nullable=False, server_default='STUDENT'))
    op.add_column('discrepancy_cases', sa.Column('observed_count', sa.Integer(), nullable=True))
    op.add_column('discrepancy_cases', sa.Column('approved_limit', sa.Integer(), nullable=True))
    op.add_column('discrepancy_cases', sa.Column('excess_count', sa.Integer(), nullable=True))
    op.add_column('discrepancy_cases', sa.Column('approval_configuration_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('approval_configurations.id', ondelete='SET NULL'), nullable=True))
    op.add_column('discrepancy_cases', sa.Column('approval_configuration_version', sa.Integer(), nullable=True))
    op.add_column('discrepancy_cases', sa.Column('source_submission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('source_submissions.id', ondelete='SET NULL'), nullable=True))
    op.add_column('discrepancy_cases', sa.Column('evidence_context_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))

    op.create_index('idx_discrepancy_cases_scope', 'discrepancy_cases', ['scope_type', 'institution_id', 'programme_id'])

    # -------------------------------------------------------------------------
    # 4. Create intake_reconciliation_summaries table
    # -------------------------------------------------------------------------
    op.create_table(
        'intake_reconciliation_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('reconciliation_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reconciliation_runs.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('approval_configuration_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('approval_configurations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approval_configuration_version', sa.Integer(), nullable=True),
        sa.Column('compliance_status', sa.String(50), nullable=False, server_default='COMPLIANT'),
        sa.Column('regular_approved_intake', sa.Integer(), nullable=False),
        sa.Column('regular_enrolled_count', sa.Integer(), nullable=False),
        sa.Column('regular_variance', sa.Integer(), nullable=False),
        sa.Column('supernumerary_total_cap', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('supernumerary_enrolled_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('supernumerary_variance', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('lateral_entry_approved_cap', sa.Integer(), nullable=True),
        sa.Column('lateral_entry_enrolled_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('lateral_entry_variance', sa.Integer(), nullable=True),
        sa.Column('category_breakdown_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -------------------------------------------------------------------------
    # 5. Enhance admission_episodes with multi-dimensional classification
    # -------------------------------------------------------------------------
    op.add_column('admission_episodes', sa.Column('nationality_category', sa.String(50), nullable=False, server_default='INDIAN_DOMICILE'))
    op.add_column('admission_episodes', sa.Column('admission_channel', sa.String(50), nullable=False, server_default='CENTRALIZED_COUNSELING'))
    op.add_column('admission_episodes', sa.Column('seat_accounting_category', sa.String(50), nullable=False, server_default='REGULAR'))
    op.add_column('admission_episodes', sa.Column('entry_level', sa.String(30), nullable=False, server_default='FIRST_YEAR'))
    op.add_column('admission_episodes', sa.Column('applicable_approval_rule_id', sa.String(100), nullable=True))
    op.create_index('idx_admission_episodes_seat_cat', 'admission_episodes', ['programme_id', 'academic_year', 'seat_accounting_category'])


def downgrade() -> None:
    # 5. Revert admission_episodes
    op.drop_index('idx_admission_episodes_seat_cat', table_name='admission_episodes')
    op.drop_column('admission_episodes', 'applicable_approval_rule_id')
    op.drop_column('admission_episodes', 'entry_level')
    op.drop_column('admission_episodes', 'seat_accounting_category')
    op.drop_column('admission_episodes', 'admission_channel')
    op.drop_column('admission_episodes', 'nationality_category')

    # 4. Drop intake_reconciliation_summaries
    op.drop_table('intake_reconciliation_summaries')

    # 3. Revert discrepancy_cases
    op.drop_index('idx_discrepancy_cases_scope', table_name='discrepancy_cases')
    op.drop_column('discrepancy_cases', 'evidence_context_json')
    op.drop_column('discrepancy_cases', 'source_submission_id')
    op.drop_column('discrepancy_cases', 'approval_configuration_version')
    op.drop_column('discrepancy_cases', 'approval_configuration_id')
    op.drop_column('discrepancy_cases', 'excess_count')
    op.drop_column('discrepancy_cases', 'approved_limit')
    op.drop_column('discrepancy_cases', 'observed_count')
    op.drop_column('discrepancy_cases', 'scope_type')
    op.alter_column('discrepancy_cases', 'student_identity_id', nullable=False)

    # 2. Drop approval_category_allocations
    op.drop_index('idx_approval_category_config', table_name='approval_category_allocations')
    op.drop_table('approval_category_allocations')

    # 1. Revert approval_configurations
    op.drop_index('uq_active_approval_config', table_name='approval_configurations', postgresql_where=sa.text("status = 'ACTIVE'"))
    op.drop_column('approval_configurations', 'amended_by_user_id')
    op.drop_column('approval_configurations', 'created_by_user_id')
    op.drop_column('approval_configurations', 'superseded_at')
    op.drop_column('approval_configurations', 'superseded_by_id')
    op.drop_column('approval_configurations', 'amendment_reason')
    op.drop_column('approval_configurations', 'approval_letter_date')
    op.drop_column('approval_configurations', 'issuing_authority')

