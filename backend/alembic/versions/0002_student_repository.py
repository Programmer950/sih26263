"""Student Repository and Global Identity Entities.

Revision ID: 0002_students
Revises: 0001_foundation
Create Date: 2026-10-30 16:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002_students'
down_revision: Union[str, None] = '0001_foundation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. student_identities
    op.create_table(
        'student_identities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('internal_student_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('encrypted_apaar_reference', sa.String(500), nullable=True),
        sa.Column('masked_apaar_reference', sa.String(50), nullable=True),
        sa.Column('apaar_blind_index', sa.String(64), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(20), nullable=True),
        sa.Column('identity_status', sa.String(50), nullable=False, server_default='UNVERIFIED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_student_identities_uuid', 'student_identities', ['internal_student_uuid'], unique=True)
    op.create_index('ix_student_identities_blind_index', 'student_identities', ['apaar_blind_index'], unique=False)

    # 2. institution_student_records
    op.create_table(
        'institution_student_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_identities.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('institution_student_id', sa.String(100), nullable=False),
        sa.Column('programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='ENROLLED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('institution_id', 'institution_student_id', name='uq_inst_student_id'),
    )
    op.create_index('ix_inst_records_student_id', 'institution_student_records', ['student_identity_id'], unique=False)
    op.create_index('ix_inst_records_inst_prog', 'institution_student_records', ['institution_id', 'programme_id'], unique=False)

    # 3. admission_episodes
    op.create_table(
        'admission_episodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_identities.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('admission_date', sa.Date(), nullable=False),
        sa.Column('admission_category', sa.String(50), nullable=False, server_default='REGULAR'),
        sa.Column('supernumerary_status', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('nri_status', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('oci_status', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('foreign_national_status', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('source_submission_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_admissions_student_id', 'admission_episodes', ['student_identity_id'], unique=False)
    op.create_index('ix_admissions_inst_prog_year', 'admission_episodes', ['institution_id', 'programme_id', 'academic_year'], unique=False)

    # 4. annual_roster_observations (MULTI-VERSION: NO UNIQUE CONSTRAINT across student/year)
    op.create_table(
        'annual_roster_observations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_identities.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('student_status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('source_submission_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_record_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('observation_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('observation_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
    )
    op.create_index('ix_roster_obs_timeline', 'annual_roster_observations', ['institution_id', 'programme_id', 'academic_year', 'student_identity_id'], unique=False)
    op.create_index('ix_roster_obs_submission', 'annual_roster_observations', ['source_submission_id'], unique=False)

    # 5. transfer_events
    op.create_table(
        'transfer_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('student_identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_identities.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('source_institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('destination_institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('source_programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('destination_programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('transfer_date', sa.Date(), nullable=False),
        sa.Column('verification_status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('evidence_reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_transfers_student_id', 'transfer_events', ['student_identity_id'], unique=False)
    op.create_index('ix_transfers_source_inst', 'transfer_events', ['source_institution_id', 'academic_year'], unique=False)
    op.create_index('ix_transfers_dest_inst', 'transfer_events', ['destination_institution_id', 'academic_year'], unique=False)


def downgrade() -> None:
    op.drop_table('transfer_events')
    op.drop_table('annual_roster_observations')
    op.drop_table('admission_episodes')
    op.drop_table('institution_student_records')
    op.drop_table('student_identities')

