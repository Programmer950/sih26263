"""Tests for Student Repository, Global Identities, Format-Only APAAR, Multi-Version Observations & Timelines (Milestone 2)."""

import pytest
import uuid
from datetime import date
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.services.identity_service import validate_apaar_format, IdentityService
from app.models import StudentIdentity, InstitutionStudentRecord, AnnualRosterObservation, Programme, Institution

client = TestClient(app)


@pytest.fixture(scope="module")
def tokens():
    """Logs in seeded users and provides Bearer tokens."""
    # 1. Apex Admin
    res_apex = client.post("/api/v1/auth/login", json={"email": "admin@apex.edu.in", "password": "Apex@12345"})
    assert res_apex.status_code == 200
    apex_token = res_apex.json()["access_token"]
    apex_inst_id = res_apex.json()["user"]["institution_id"]

    # 2. Polytechnic Admin
    res_poly = client.post("/api/v1/auth/login", json={"email": "admin@polytechnic.edu.in", "password": "Poly@12345"})
    assert res_poly.status_code == 200
    poly_token = res_poly.json()["access_token"]
    poly_inst_id = res_poly.json()["user"]["institution_id"]

    # 3. AICTE Reviewer
    res_rev = client.post("/api/v1/auth/login", json={"email": "reviewer@aicte.gov.in", "password": "Reviewer@12345"})
    assert res_rev.status_code == 200
    reviewer_token = res_rev.json()["access_token"]

    return {
        "apex": {"token": apex_token, "inst_id": apex_inst_id},
        "poly": {"token": poly_token, "inst_id": poly_inst_id},
        "reviewer": {"token": reviewer_token},
    }


def test_apaar_format_only_validation():
    """
    Safeguard / Revision 3:
    - Implement documented format validation only (12 numeric digits).
    - Do NOT invent a checksum algorithm.
    - Format validity is strictly distinct from external verification.
    """
    # 1. Valid 12 digits
    status, clean, masked, blind_idx = validate_apaar_format("987654321012")
    assert status == "FORMAT_VALID"
    assert clean == "987654321012"
    assert masked == "XXXX-XXXX-1012"
    assert len(blind_idx) == 64

    # 2. Valid with hyphens / spaces
    status_hyphen, clean_h, masked_h, _ = validate_apaar_format("9876-5432-1012")
    assert status_hyphen == "FORMAT_VALID"
    assert clean_h == "987654321012"
    assert masked_h == "XXXX-XXXX-1012"

    # 3. Missing APAAR (Must not reject record)
    status_miss, clean_m, masked_m, _ = validate_apaar_format(None)
    assert status_miss == "MISSING_APAAR"
    assert clean_m is None
    assert masked_m is None

    # 4. Invalid Format (alphanumeric or wrong length)
    status_inv, _, _, _ = validate_apaar_format("12345ABC9012")
    assert status_inv == "INVALID_FORMAT"

    status_short, _, _, _ = validate_apaar_format("12345")
    assert status_short == "INVALID_FORMAT"


def test_list_students_tenancy(tokens):
    """
    Safeguard 3:
    - Apex Admin sees only Apex students.
    - Reviewer can see all students across institutions.
    """
    # Apex Admin
    res_apex = client.get(
        "/api/v1/students",
        headers={"Authorization": f"Bearer {tokens['apex']['token']}"},
    )
    assert res_apex.status_code == 200
    data_apex = res_apex.json()
    assert data_apex["total"] >= 15  # Seeded Apex students
    for item in data_apex["items"]:
        assert item["institution_id"] == tokens["apex"]["inst_id"]

    # AICTE Reviewer
    res_rev = client.get(
        "/api/v1/students",
        headers={"Authorization": f"Bearer {tokens['reviewer']['token']}"},
    )
    assert res_rev.status_code == 200
    data_rev = res_rev.json()
    assert data_rev["total"] >= data_apex["total"]


def test_student_timeline_reconstruction(tokens):
    """
    PRD Module 3 / Milestone 2:
    - Student timeline reconstructs admission episode, multi-year observations, and transfer events.
    """
    # List students to get ID of Karthik Subramanian (transfer student)
    res = client.get(
        "/api/v1/students?search=Karthik",
        headers={"Authorization": f"Bearer {tokens['apex']['token']}"},
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    student_id = items[0]["id"]

    # Fetch timeline
    res_tl = client.get(
        f"/api/v1/students/{student_id}/timeline",
        headers={"Authorization": f"Bearer {tokens['apex']['token']}"},
    )
    assert res_tl.status_code == 200
    tl = res_tl.json()

    assert tl["identity"]["full_name"] == "Karthik Subramanian"
    assert "XXXX-XXXX-" in tl["identity"]["masked_apaar"]
    assert len(tl["institutions_enrolled"]) >= 1

    # Check timeline events include ADMISSION and TRANSFER
    event_types = [e["type"] for e in tl["timeline"]]
    assert "ADMISSION" in event_types
    assert "TRANSFER" in event_types


def test_multi_version_annual_observations(tokens):
    """
    Safeguard / Revision 1:
    - Multiple annual roster observations for the same student, programme, and academic year
      can be saved across multiple submission revisions without unique constraint collisions.
    """
    db = SessionLocal()
    try:
        ident = db.execute(select(StudentIdentity)).scalars().first()
        prog = db.execute(select(Programme)).scalars().first()
        inst_id = prog.institution_id

        # Insert observation version 1
        obs1 = AnnualRosterObservation(
            student_identity_id=ident.id,
            institution_id=inst_id,
            programme_id=prog.id,
            academic_year="2024-25",
            student_status="ACTIVE",
            observation_metadata={"version": 1, "note": "Initial submission observation"},
        )
        db.add(obs1)
        db.commit()

        # Insert observation version 2 (same student, programme, academic year)
        obs2 = AnnualRosterObservation(
            student_identity_id=ident.id,
            institution_id=inst_id,
            programme_id=prog.id,
            academic_year="2024-25",
            student_status="ACTIVE",
            observation_metadata={"version": 2, "note": "Revised submission observation"},
        )
        db.add(obs2)
        db.commit()

        # Verify both observations exist simultaneously
        all_obs = db.execute(
            select(AnnualRosterObservation).where(
                AnnualRosterObservation.student_identity_id == ident.id,
                AnnualRosterObservation.academic_year == "2024-25",
            )
        ).scalars().all()

        assert len(all_obs) >= 2
    finally:
        db.close()


def test_register_student_endpoint(tokens):
    """Verify registering a student via API endpoint with tenancy protection."""
    # Fetch CSE programme ID for Apex
    res_prog = client.get(
        f"/api/v1/institutions/{tokens['apex']['inst_id']}/programmes",
        headers={"Authorization": f"Bearer {tokens['apex']['token']}"},
    )
    assert res_prog.status_code == 200
    cse_prog_id = res_prog.json()[0]["id"]

    import uuid
    suffix = uuid.uuid4().hex[:6]
    payload = {
        "institution_student_id": f"TEST_ROLL_{suffix}",
        "full_name": "Test Student Automated",
        "programme_id": cse_prog_id,
        "academic_year": "2024-25",
        "admission_date": "2024-08-01",
        "apaar_id": "999988887777",
        "date_of_birth": "2006-01-01",
        "gender": "F",
        "admission_category": "REGULAR",
        "supernumerary_status": False,
        "nri_status": False,
    }

    res_post = client.post(
        "/api/v1/students",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['apex']['token']}"},
    )
    assert res_post.status_code == 201
    created = res_post.json()
    assert created["full_name"] == "Test Student Automated"
    assert created["masked_apaar_reference"] == "XXXX-XXXX-7777"
    assert created["identity_status"] == "FORMAT_VALID"
    assert created["institution_id"] == tokens["apex"]["inst_id"]


def test_cross_institution_two_institutions_tenancy(tokens):
    """
    Verification Item 5:
    Test all student endpoints using at least two institutions.
    Verify object-level authorization (IDOR rejection):
    - Apex Admin CANNOT read Polytechnic students or timelines.
    - Polytechnic Admin CAN read Polytechnic students.
    """
    db = SessionLocal()
    poly_inst_id = tokens["poly"]["inst_id"]
    try:
        # Find or create a student exclusively in Polytechnic
        poly_rec = db.execute(
            select(InstitutionStudentRecord).where(InstitutionStudentRecord.institution_id == poly_inst_id)
        ).first()

        if not poly_rec:
            # Create a programme for polytechnic if needed
            prog = db.execute(select(Programme).where(Programme.institution_id == poly_inst_id)).scalars().first()
            if not prog:
                prog = Programme(
                    institution_id=poly_inst_id,
                    programme_code="DIP_CSE",
                    programme_name="Diploma in CSE",
                    qualification_level="DIPLOMA",
                    duration_years=3,
                )
                db.add(prog)
                db.commit()

            ident, rec, ep = IdentityService.register_student(
                db=db,
                institution_id=poly_inst_id,
                programme_id=prog.id,
                institution_student_id="POLY_STUDENT_001",
                full_name="Poly Exclusive Student",
                academic_year="2024-25",
                admission_date=date(2024, 8, 1),
                raw_apaar="777788889999",
            )
            db.commit()
            poly_student_id = ident.id
        else:
            poly_student_id = poly_rec[0].student_identity_id

        # 1. Apex Admin queries Polytechnic student detail -> 403 Forbidden
        res_detail = client.get(
            f"/api/v1/students/{poly_student_id}",
            headers={"Authorization": f"Bearer {tokens['apex']['token']}"},
        )
        assert res_detail.status_code == 403
        assert "Tenancy Violation" in res_detail.json()["detail"]

        # 2. Apex Admin queries Polytechnic student timeline -> 403 Forbidden
        res_tl = client.get(
            f"/api/v1/students/{poly_student_id}/timeline",
            headers={"Authorization": f"Bearer {tokens['apex']['token']}"},
        )
        assert res_tl.status_code == 403
        assert "Tenancy Violation" in res_tl.json()["detail"]

        # 3. Polytechnic Admin queries own student -> 200 OK
        res_poly_ok = client.get(
            f"/api/v1/students/{poly_student_id}",
            headers={"Authorization": f"Bearer {tokens['poly']['token']}"},
        )
        assert res_poly_ok.status_code == 200
        assert res_poly_ok.json()["institution_id"] == poly_inst_id

        # 4. Polytechnic Admin queries own student timeline -> 200 OK
        res_poly_tl = client.get(
            f"/api/v1/students/{poly_student_id}/timeline",
            headers={"Authorization": f"Bearer {tokens['poly']['token']}"},
        )
        assert res_poly_tl.status_code == 200
    finally:
        db.close()


def test_weak_attributes_same_name_do_not_merge(tokens):
    """
    Verification Item 1:
    - Similar or identical names alone MUST NEVER trigger automatic identity merges.
    """
    db = SessionLocal()
    try:
        apex_id = tokens["apex"]["inst_id"]
        prog = db.execute(select(Programme).where(Programme.institution_id == apex_id)).scalars().first()

        name = "Identical Name Student"
        # Register first student without APAAR
        s1_ident, s1_rec, _ = IdentityService.register_student(
            db=db,
            institution_id=apex_id,
            programme_id=prog.id,
            institution_student_id="SAME_NAME_01",
            full_name=name,
            academic_year="2024-25",
            admission_date=date(2024, 8, 1),
            raw_apaar=None,
        )
        db.commit()

        # Register second student with same name without APAAR
        s2_ident, s2_rec, _ = IdentityService.register_student(
            db=db,
            institution_id=apex_id,
            programme_id=prog.id,
            institution_student_id="SAME_NAME_02",
            full_name=name,
            academic_year="2024-25",
            admission_date=date(2024, 8, 1),
            raw_apaar=None,
        )
        db.commit()

        # Verify two completely distinct global identities were created
        assert s1_ident.id != s2_ident.id
        assert s1_ident.internal_student_uuid != s2_ident.internal_student_uuid
    finally:
        db.close()


def test_multi_institution_binding_same_apaar(tokens):
    """
    Verification Item 1 & 2:
    - Global student identities are independent of institution-specific records.
    - The same student can have multiple institution-specific records linking to ONE global identity.
    """
    db = SessionLocal()
    try:
        apex_id = tokens["apex"]["inst_id"]
        poly_id = tokens["poly"]["inst_id"]
        apex_prog = db.execute(select(Programme).where(Programme.institution_id == apex_id)).scalars().first()
        poly_prog = db.execute(select(Programme).where(Programme.institution_id == poly_id)).scalars().first()

        shared_apaar = "555566667777"

        # 1. Enrolled at Apex
        ident_apex, rec_apex, _ = IdentityService.register_student(
            db=db,
            institution_id=apex_id,
            programme_id=apex_prog.id,
            institution_student_id="APEX_SHARED_01",
            full_name="Cross Enrolled Student",
            academic_year="2023-24",
            admission_date=date(2023, 8, 1),
            raw_apaar=shared_apaar,
        )
        db.commit()

        # 2. Later observed / enrolled at Polytechnic
        ident_poly, rec_poly, _ = IdentityService.register_student(
            db=db,
            institution_id=poly_id,
            programme_id=poly_prog.id,
            institution_student_id="POLY_SHARED_02",
            full_name="Cross Enrolled Student",
            academic_year="2024-25",
            admission_date=date(2024, 8, 1),
            raw_apaar=shared_apaar,
        )
        db.commit()

        # Same global identity anchor
        assert ident_apex.id == ident_poly.id
        assert ident_apex.internal_student_uuid == ident_poly.internal_student_uuid

        # Two distinct institution records
        assert rec_apex.id != rec_poly.id
        assert str(rec_apex.institution_id) == str(apex_id)
        assert str(rec_poly.institution_id) == str(poly_id)

        # Timeline shows both institutions
        tl = IdentityService.get_student_timeline(db, ident_apex.id)
        inst_names = [inst["institution_name"] for inst in tl["institutions_enrolled"]]
        assert len(inst_names) == 2
    finally:
        db.close()

