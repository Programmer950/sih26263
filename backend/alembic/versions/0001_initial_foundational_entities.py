"""Initial foundational entities migration.

Revision ID: 0001_foundation
Revises: 
Create Date: 2026-10-30 16:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_foundation'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. roles
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('role_name', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_roles_role_name', 'roles', ['role_name'], unique=True)

    # 2. institutions
    op.create_table(
        'institutions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('approval_status', sa.String(50), nullable=False, server_default='APPROVED'),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('state', sa.String(100), nullable=False),
        sa.Column('district', sa.String(100), nullable=False),
        sa.Column('pincode', sa.String(10), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_institutions_code', 'institutions', ['institution_code'], unique=True)
    op.create_index('ix_institutions_state', 'institutions', ['state'], unique=False)

    # 3. programmes
    op.create_table(
        'programmes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('programme_code', sa.String(50), nullable=False),
        sa.Column('programme_name', sa.String(255), nullable=False),
        sa.Column('qualification_level', sa.String(50), nullable=False),
        sa.Column('duration_years', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('institution_id', 'programme_code', name='uq_institution_programme'),
    )
    op.create_index('ix_programmes_institution_id', 'programmes', ['institution_id'], unique=False)

    # 4. approval_configurations
    op.create_table(
        'approval_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('programme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programmes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('academic_year', sa.String(20), nullable=False),
        sa.Column('approved_intake', sa.Integer(), nullable=False),
        sa.Column('supernumerary_quota_percentage', sa.Numeric(5, 2), nullable=False, server_default='15.00'),
        sa.Column('lateral_entry_quota_percentage', sa.Numeric(5, 2), nullable=False, server_default='10.00'),
        sa.Column('approval_reference', sa.String(100), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=False),
        sa.Column('configuration_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('programme_id', 'academic_year', 'configuration_version', name='uq_approval_config_version'),
        sa.CheckConstraint('effective_to >= effective_from', name='chk_approval_dates'),
        sa.CheckConstraint('approved_intake > 0', name='chk_positive_intake'),
    )
    op.create_index('ix_approval_configs_lookup', 'approval_configurations', ['programme_id', 'academic_year', 'status'], unique=False)

    # 5. users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_institution_id', 'users', ['institution_id'], unique=False)

    # 6. session_revocations
    op.create_table(
        'session_revocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('jti', sa.String(64), nullable=False),
        sa.Column('revocation_reason', sa.String(100), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_session_revocations_jti', 'session_revocations', ['jti'], unique=True)
    op.create_index('ix_session_revocations_expires_at', 'session_revocations', ['expires_at'], unique=False)

    # 7. audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('previous_event_hash', sa.String(64), nullable=False),
        sa.Column('event_hash', sa.String(64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_events_action', 'audit_events', ['action'], unique=False)
    op.create_index('ix_audit_events_entity_type', 'audit_events', ['entity_type'], unique=False)
    op.create_index('ix_audit_events_event_hash', 'audit_events', ['event_hash'], unique=False)
    op.create_index('ix_audit_events_timestamp', 'audit_events', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('session_revocations')
    op.drop_table('users')
    op.drop_table('approval_configurations')
    op.drop_table('programmes')
    op.drop_table('institutions')
    op.drop_table('roles')

