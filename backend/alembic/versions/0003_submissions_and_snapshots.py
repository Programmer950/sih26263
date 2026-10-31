"""Submissions, Previews, Records and Snapshots Entities (Milestone 3A).

Revision ID: 0003_submissions_and_snapshots
Revises: 0002_students
Create Date: 2026-10-30 18:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0003_submissions_and_snapshots'
down_revision: Union[str, None] = '0002_students'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Preflight Check: Inspect student_identities for duplicate blind indexes
    # -------------------------------------------------------------------------
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT apaar_blind_index, count(*) "
            "FROM student_identities "
            "WHERE apaar_blind_index IS NOT NULL "
            "GROUP BY apaar_blind_index "
            "HAVING count(*) > 1;"
        )
    ).fetchall()
    if result:
        dupes = [row[0] for row in result]
        raise RuntimeError(
            f"Preflight Migration Failure: Duplicate APAAR blind indexes detected in database: {dupes}. "
            "Migration halted to prevent unsafe automatic merges. Manual resolution required."
        )

    # 1. student_identities unique partial index on non-null apaar_blind_index
    op.drop_index('ix_student_identities_blind_index', table_name='student_identities')
    op.create_index(
        'uq_student_identities_apaar_blind_index',
        'student_identities',
        ['apaar_blind_index'],
        unique=True,
        postgresql_where=sa.text('apaar_blind_index IS NOT NULL'),
    )

    # 2. programmes: add uq_institution_programme_id to enable composite institution FK
    op.create_unique_constraint(
        'uq_institution_programme_id',
        'programmes',
        ['institution_id', 'id'],
    )

    # 3. source_submissions
    op.create_table(
        'source_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('submission_type', sa.String(50), nullable=False, server_default='ANNUAL_ROSTER'),
        sa.Column('submission_status', sa.String(50), nullable=False, server_default='UPLOADED'),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('storage_key', sa.String(255), nullable=False),
        sa.Column('file_fingerprint', sa.String(64), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('client_idempotency_key', sa.String(128), nullable=True),
        sa.Column('total_rows_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_rows_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_rows_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('warning_rows_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicate_rows_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mapping_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('validation_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('committed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.ForeignKeyConstraint(
            ['institution_id', 'programme_id'],
            ['programmes.institution_id', 'programmes.id'],
            name='fk_submission_programme',
            ondelete='RESTRICT',
        ),
        sa.UniqueConstraint(
            'id', 'institution_id', 'programme_id', 'academic_year',
            name='uq_submission_relational_anchor',
        ),
    )
    op.create_index('idx_submissions_lookup', 'source_submissions', ['institution_id', 'academic_year', 'submission_type'], unique=False)
    op.create_index('idx_submissions_status', 'source_submissions', ['submission_status'], unique=False)
    op.create_index(
        'uq_source_submissions_tenant_idempotency',
        'source_submissions',
        ['institution_id', 'client_idempotency_key'],
        unique=True,
        postgresql_where=sa.text('client_idempotency_key IS NOT NULL'),
    )
    op.create_index(
        'uq_active_context_fingerprint',
        'source_submissions',
        ['institution_id', 'programme_id', 'academic_year', 'submission_type', 'file_fingerprint'],
        unique=True,
        postgresql_where=sa.text("submission_status NOT IN ('FAILED', 'CANCELLED')"),
    )

    # 4. submission_previews
    op.create_table(
        'submission_previews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('source_submissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_fingerprint', sa.String(64), nullable=False),
        sa.Column('column_mapping', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('mapping_version', sa.String(50), nullable=False, server_default='v1.0'),
        sa.Column('mapping_hash', sa.String(64), nullable=False),
        sa.Column('parser_version', sa.String(50), nullable=False, server_default='openpyxl-v3.1.2/csv-std'),
        sa.Column('validation_rules_version', sa.String(50), nullable=False, server_default='rules-v2026.1'),
        sa.Column('normalization_version', sa.String(50), nullable=False, server_default='norm-v1.0'),
        sa.Column('validation_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index(
        'uq_active_preview_per_submission',
        'submission_previews',
        ['submission_id'],
        unique=True,
        postgresql_where=sa.text('is_active = TRUE'),
    )
    op.create_index('idx_submission_previews_lookup', 'submission_previews', ['submission_id', 'is_active'], unique=False)
    op.create_index('idx_submission_previews_hash', 'submission_previews', ['mapping_hash'], unique=False)

    # 5. source_submission_records
    op.create_table(
        'source_submission_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('source_submissions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('parsed_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('formula_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('validation_status', sa.String(50), nullable=False, server_default='VALID'),
        sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('mapping_version', sa.String(50), nullable=False, server_default='v1.0'),
        sa.Column('resolved_student_identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_identities.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolved_institution_student_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institution_student_records.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('submission_id', 'row_number', name='uq_submission_record_row'),
        sa.UniqueConstraint('id', 'submission_id', name='uq_submission_record_composite'),
    )
    op.create_index('idx_sub_records_subid', 'source_submission_records', ['submission_id'], unique=False)
    op.create_index('idx_sub_records_identity', 'source_submission_records', ['resolved_student_identity_id'], unique=False)

    # 6. annual_roster_observations foreign keys and composite constraints
    op.create_foreign_key(
        'fk_roster_obs_submission',
        'annual_roster_observations',
        'source_submissions',
        ['source_submission_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_roster_obs_source_record',
        'annual_roster_observations',
        'source_submission_records',
        ['source_record_id', 'source_submission_id'],
        ['id', 'submission_id'],
        ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_roster_obs_context',
        'annual_roster_observations',
        'source_submissions',
        ['source_submission_id', 'institution_id', 'programme_id', 'academic_year'],
        ['id', 'institution_id', 'programme_id', 'academic_year'],
        ondelete='RESTRICT',
    )

    # 7. roster_snapshots
    op.create_table(
        'roster_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('source_submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('completeness_status', sa.String(50), nullable=False, server_default='UNKNOWN'),
        sa.Column('lifecycle_status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('is_authoritative', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('declared_headcount', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('observed_headcount', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('snapshot_canonicalization_version', sa.String(50), nullable=False, server_default='v1-sha256-sorted-uuids'),
        sa.Column('snapshot_hash', sa.String(64), nullable=False),
        sa.Column('snapshot_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('superseded_by_snapshot_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roster_snapshots.id', ondelete='SET NULL'), nullable=True),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(
            ['source_submission_id', 'institution_id', 'programme_id', 'academic_year'],
            ['source_submissions.id', 'source_submissions.institution_id', 'source_submissions.programme_id', 'source_submissions.academic_year'],
            name='fk_snapshot_submission',
            ondelete='RESTRICT',
        ),
        sa.CheckConstraint(
            "NOT (is_authoritative = TRUE AND lifecycle_status = 'SUPERSEDED')",
            name='chk_authoritative_lifecycle',
        ),
    )
    op.create_index(
        'idx_uq_authoritative_snapshot',
        'roster_snapshots',
        ['institution_id', 'programme_id', 'academic_year'],
        unique=True,
        postgresql_where=sa.text('is_authoritative = TRUE'),
    )
    op.create_index('idx_snapshots_inst_prog_year', 'roster_snapshots', ['institution_id', 'programme_id', 'academic_year'], unique=False)
    op.create_index('idx_snapshots_authoritative', 'roster_snapshots', ['is_authoritative', 'lifecycle_status'], unique=False)


def downgrade() -> None:
    op.drop_table('roster_snapshots')
    op.drop_constraint('fk_roster_obs_context', 'annual_roster_observations', type_='foreignkey')
    op.drop_constraint('fk_roster_obs_source_record', 'annual_roster_observations', type_='foreignkey')
    op.drop_constraint('fk_roster_obs_submission', 'annual_roster_observations', type_='foreignkey')
    op.drop_table('source_submission_records')
    op.drop_table('submission_previews')
    op.drop_table('source_submissions')
    op.drop_constraint('uq_institution_programme_id', 'programmes', type_='unique')
    op.drop_index('uq_student_identities_apaar_blind_index', table_name='student_identities')
    op.create_index('ix_student_identities_blind_index', 'student_identities', ['apaar_blind_index'], unique=False)

