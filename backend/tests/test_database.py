"""Tests for Database Connectivity, Schema Integrity, and Foundational Models (Milestone 1A)."""

import pytest
import uuid
from datetime import date, datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.core.config import Settings
from app.core.database import SessionLocal, check_db_connection
from app.models import (
    Role,
    Institution,
    Programme,
    ApprovalConfiguration,
    User,
    SessionRevocation,
    AuditEvent,
)


@pytest.fixture(scope="module")
def db_session():
    """Provides a transactional database session for tests."""
    session = SessionLocal()
    yield session
    session.close()


def test_postgres_connection():
    """Verify active database connectivity."""
    assert check_db_connection() is True


def test_settings_validation_rejects_weak_secrets():
    """Safeguard 5: Validate all required environment secrets."""
    with pytest.raises(Exception):
        Settings(
            JWT_SECRET_KEY="too-short",
            DATA_ENCRYPTION_KEY="3034bb1956a6c08e3836cecfcbc86992aaa389267a29cf28e4ccc9415174b1f6",
            BLIND_INDEX_SECRET_KEY="9166d729a0b0e724886f2b17067fa28ba5913a0461d6602bc824165bbbf79c49",
        )


def test_insert_and_query_foundational_entities(db_session):
    """Verify insertion, relationships, and queries across all 7 foundational entities."""
    test_suffix = uuid.uuid4().hex[:8]

    # 1. Role
    role = Role(
        role_name=f"TEST_ROLE_{test_suffix}",
        description="Automated Test Role",
        permissions={"can_view": True, "can_submit": False},
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    assert role.id is not None

    # 2. Institution
    inst = Institution(
        institution_code=f"INST_{test_suffix}",
        name="Test Engineering College",
        category="ENGINEERING",
        approval_status="APPROVED",
        state="Maharashtra",
        district="Pune",
        contact_email="test@inst.edu.in",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    assert inst.id is not None

    # 3. Programme
    prog = Programme(
        institution_id=inst.id,
        programme_code="CSE",
        programme_name="Computer Science and Engineering",
        qualification_level="UG",
        duration_years=4,
    )
    db_session.add(prog)
    db_session.commit()
    db_session.refresh(prog)
    assert prog.id is not None
    assert prog.institution.name == "Test Engineering College"

    # 4. ApprovalConfiguration
    approval = ApprovalConfiguration(
        institution_id=inst.id,
        programme_id=prog.id,
        academic_year="2024-25",
        approved_intake=120,
        supernumerary_quota_percentage=15.00,
        lateral_entry_quota_percentage=10.00,
        approval_reference=f"EOA/TEST/{test_suffix}",
        effective_from=date(2024, 7, 1),
        effective_to=date(2025, 6, 30),
        configuration_version=1,
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)
    assert approval.approved_intake == 120

    # 5. User
    user = User(
        name="Test Administrator",
        email=f"admin_{test_suffix}@inst.edu.in",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fake_salt$fake_hash",
        role_id=role.id,
        institution_id=inst.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.role.role_name == f"TEST_ROLE_{test_suffix}"
    assert user.institution.institution_code == f"INST_{test_suffix}"

    # 6. SessionRevocation
    jti = f"jti_{uuid.uuid4()}"
    revocation = SessionRevocation(
        user_id=user.id,
        jti=jti,
        revocation_reason="Logout test",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db_session.add(revocation)
    db_session.commit()
    db_session.refresh(revocation)
    assert revocation.jti == jti

    # 7. AuditEvent
    audit = AuditEvent(
        actor_id=user.id,
        action="TEST_INIT_COMPLETED",
        entity_type="INSTITUTION",
        entity_id=inst.id,
        metadata_payload={"test": True, "suffix": test_suffix},
        previous_event_hash="0" * 64,
        event_hash="a" * 64,
    )
    db_session.add(audit)
    db_session.commit()
    db_session.refresh(audit)
    assert audit.action == "TEST_INIT_COMPLETED"


def test_unique_constraint_enforcement(db_session):
    """Verify relational database uniqueness constraints."""
    suffix = uuid.uuid4().hex[:8]

    # Create initial role
    role = Role(role_name=f"UNIQUE_ROLE_{suffix}", permissions={})
    db_session.add(role)
    db_session.commit()

    # Attempt inserting duplicate role name
    duplicate_role = Role(role_name=f"UNIQUE_ROLE_{suffix}", permissions={})
    db_session.add(duplicate_role)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_violation_rollback(db_session):
    """Verify foreign key constraint rejects orphan entities and rolls back."""
    fake_role_id = uuid.uuid4()
    orphan_user = User(
        name="Orphan User",
        email=f"orphan_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        role_id=fake_role_id,
    )
    db_session.add(orphan_user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

