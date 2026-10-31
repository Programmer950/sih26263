"""Reconciliation Runs, Result Items, Discrepancy Cases and Decisions (Milestone 3E).

Revision ID: 0004_reconciliation_and_discrepancies
Revises: 0003_submissions_and_snapshots
Create Date: 2026-10-30 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004_reconciliation_cases'
down_revision: Union[str, None] = '0003_submissions_and_snapshots'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. reconciliation_runs table
    # -------------------------------------------------------------------------
    op.create_table(
        'reconciliation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('candidate_snapshot_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roster_snapshots.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('candidate_snapshot_hash', sa.String(64), nullable=False),
        sa.Column('baseline_snapshot_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roster_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('baseline_snapshot_hash', sa.String(64), nullable=True),
        sa.Column('run_type', sa.String(50), nullable=False, server_default='REGULATORY_RECONCILIATION'),
        sa.Column('execution_status', sa.String(50), nullable=False, server_default='COMPLETED'),
        sa.Column('engine_version', sa.String(50), nullable=False, server_default='v1.0'),
        sa.Column('rules_version', sa.String(50), nullable=False, server_default='v1.0-rules-apaar-setu'),
        sa.Column('result_fingerprint', sa.String(64), nullable=False),
        sa.Column('summary_counts', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('parameters_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('idempotency_key', sa.String(128), nullable=True),
        sa.Column('initiated_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_recon_runs_context', 'reconciliation_runs', ['institution_id', 'programme_id', 'academic_year'])
    op.create_index('idx_recon_runs_candidate', 'reconciliation_runs', ['candidate_snapshot_id'])
    op.create_index(
        'idx_uq_recon_run_idempotency',
        'reconciliation_runs',
        ['institution_id', 'idempotency_key'],
        unique=True,
        postgresql_where=sa.text('idempotency_key IS NOT NULL'),
    )

    # -------------------------------------------------------------------------
    # 2. discrepancy_cases table
    # -------------------------------------------------------------------------
    op.create_table(
        'discrepancy_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_number', sa.String(50), nullable=False, unique=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('student_identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_identities.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('initial_reconciliation_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reconciliation_runs.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('latest_reconciliation_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reconciliation_runs.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('linked_prior_case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('discrepancy_cases.id', ondelete='SET NULL'), nullable=True),
        sa.Column('classification', sa.String(50), nullable=False),
        sa.Column('review_priority', sa.String(20), nullable=False, server_default='MEDIUM'),
        sa.Column('case_status', sa.String(50), nullable=False, server_default='OPEN'),
        sa.Column('occurrence_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_discrepancy_cases_inst_status', 'discrepancy_cases', ['institution_id', 'case_status'])
    op.create_index('idx_discrepancy_cases_student', 'discrepancy_cases', ['student_identity_id'])
    op.create_index('idx_discrepancy_cases_lineage', 'discrepancy_cases', ['institution_id', 'programme_id', 'student_identity_id', 'classification'])

    # -------------------------------------------------------------------------
    # 3. reconciliation_result_items table
    # -------------------------------------------------------------------------
    op.create_table(
        'reconciliation_result_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('reconciliation_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reconciliation_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('student_identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_identities.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('candidate_observation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('annual_roster_observations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('candidate_submission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('source_submissions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('candidate_row_number', sa.Integer(), nullable=True),
        sa.Column('baseline_observation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('annual_roster_observations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('baseline_submission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('source_submissions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('baseline_row_number', sa.Integer(), nullable=True),
        sa.Column('classification', sa.String(50), nullable=False),
        sa.Column('review_priority', sa.String(20), nullable=False, server_default='NONE'),
        sa.Column('system_explanation', sa.Text(), nullable=False),
        sa.Column('rules_version', sa.String(50), nullable=False),
        sa.Column('is_case_eligible', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('discrepancy_case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('discrepancy_cases.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_recon_results_run', 'reconciliation_result_items', ['reconciliation_run_id'])
    op.create_index('idx_recon_results_classification', 'reconciliation_result_items', ['reconciliation_run_id', 'classification'])
    op.create_index('idx_recon_results_student', 'reconciliation_result_items', ['student_identity_id'])

    # -------------------------------------------------------------------------
    # 4. discrepancy_case_decisions table
    # -------------------------------------------------------------------------
    op.create_table(
        'discrepancy_case_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('discrepancy_case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('discrepancy_cases.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('from_status', sa.String(50), nullable=False),
        sa.Column('to_status', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('mandatory_reason', sa.Text(), nullable=False),
        sa.Column('evidence_references', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('decided_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('audit_event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('audit_events.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_case_decisions_case', 'discrepancy_case_decisions', ['discrepancy_case_id'])


def downgrade() -> None:
    op.drop_table('discrepancy_case_decisions')
    op.drop_table('reconciliation_result_items')
    op.drop_table('discrepancy_cases')
    op.drop_table('reconciliation_runs')
