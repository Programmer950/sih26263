"""Verification Requests and Disclosure Tokens (Milestone 5.3).

Revision ID: 0006_verification_requests
Revises: 0005_approval_intake_matrix
Create Date: 2026-10-31 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0006_verification_requests'
down_revision: Union[str, None] = '0005_approval_intake_matrix'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'verification_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('verification_reference', sa.String(50), nullable=False, unique=True),
        sa.Column('token', sa.String(128), nullable=False, unique=True),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('student_identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_identities.id', ondelete='SET NULL'), nullable=True),
        sa.Column('requester_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('organization_name', sa.String(255), nullable=True),
        sa.Column('verifier_name', sa.String(255), nullable=True),
        sa.Column('stated_purpose', sa.Text(), nullable=False),
        sa.Column('consent_confirmed', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('status', sa.String(50), nullable=False, server_default='VERIFIED'),
        sa.Column('disclosed_record_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_verification_token_hash', 'verification_requests', ['token_hash'])
    op.create_index('idx_verification_reference', 'verification_requests', ['verification_reference'])
    op.create_index('idx_verification_requester', 'verification_requests', ['requester_user_id'])


def downgrade() -> None:
    op.drop_table('verification_requests')

