"""Comprehensive Database Seeder for APAAR SETU Demonstration Environment.

Implements realistic synthetic data enrichment across:
- 3 distinct institutions with complete institutional profiles
- Curated, realistic institutional programme catalogues with distinct programmes
- Plausible, varied approved intake configurations across 3 consecutive academic years
- Diverse, believable Indian student profiles with authentic regional naming patterns
- Strictly preserves the mandatory 120-student Apex CSE longitudinal scenario
- Vertical lateral entry (Diploma to Degree) and inter-institution transfers
- Cross-institution dual enrolment candidates
- Missing and unverified APAAR examples
- Pre-persisted submissions and authoritative roster snapshots for all institutions
- Pre-seeded operational discrepancy cases and reasoned regulatory decisions
- Append-only cryptographically chained audit events
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import uuid
import hashlib
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, update

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.services.identity_service import IdentityService, validate_apaar_format
from app.services.snapshot_service import SnapshotService
from app.models import (
    Role,
    Institution,
    Programme,
    ApprovalConfiguration,
    User,
    StudentIdentity,
    InstitutionStudentRecord,
    AdmissionEpisode,
    AnnualRosterObservation,
    TransferEvent,
    SourceSubmission,
    SourceSubmissionRecord,
    SubmissionPreview,
    RosterSnapshot,
    AggregateEnrolmentDeclaration,
    ReconciliationRun,
    DiscrepancyCase,
    DiscrepancyCaseDecision,
    AuditEvent,
)

# Diverse, non-celebrity realistic Indian names with regional distribution
NAMES_MALE = [
    ("Aarav", "Sharma"), ("Arjun", "Patel"), ("Vikram", "Iyer"), ("Rohan", "Kulkarni"),
    ("Siddharth", "Pillai"), ("Dhruv", "Mehta"), ("Varun", "Deshmukh"), ("Pranav", "Joshi"),
    ("Nikhil", "Gupta"), ("Manish", "Shenoy"), ("Kartik", "Venkatesh"), ("Harsh", "Trivedi"),
    ("Gaurav", "Pandey"), ("Akash", "Reddy"), ("Anand", "Chatterjee"), ("Rajesh", "Nair"),
    ("Deepak", "Mishra"), ("Amit", "Saxena"), ("Rahul", "Chopra"), ("Sameer", "Banerjee"),
    ("Dev", "Gowda"), ("Yash", "Chavan"), ("Kunal", "Shah"), ("Tanmay", "Bhat"),
    ("Abhishek", "Dutta"), ("Vivek", "Sengupta"), ("Sanjay", "Kamath"), ("Chetan", "Nayak"),
    ("Tushar", "Pawar"), ("Praveen", "Menon"), ("Kishore", "Subramanian"), ("Naveen", "Barman"),
    ("Ashwin", "Sundaram"), ("Koushik", "Murthy"), ("Sachin", "Shinde"), ("Souvik", "Mukherjee"),
    ("Arnab", "Bose"), ("Debayan", "Roy"), ("Vikas", "Yadav"), ("Balaji", "Rao"),
    ("Senthil", "Kumar"), ("Vignesh", "Balasubramaniam"), ("Basavaraj", "Patil"), ("Harish", "Dubey"),
]

NAMES_FEMALE = [
    ("Diya", "Mukherjee"), ("Ananya", "Rao"), ("Riya", "Deshmukh"), ("Sneha", "Patel"),
    ("Tanvi", "Kulkarni"), ("Meera", "Hegde"), ("Pooja", "Sundaram"), ("Shreya", "Joshi"),
    ("Kavya", "Nair"), ("Isha", "Verma"), ("Neha", "Chaudhary"), ("Priya", "Subramanian"),
    ("Aditi", "Bose"), ("Divya", "Menon"), ("Swati", "Gupta"), ("Rashmi", "Shinde"),
    ("Shruti", "Kamath"), ("Anjali", "Banerjee"), ("Sonal", "Shah"), ("Sunita", "Mishra"),
    ("Preeti", "Chatterjee"), ("Radhika", "Reddy"), ("Deepa", "Shenoy"), ("Nandini", "Bhat"),
    ("Pallavi", "Choudhury"), ("Rupa", "Dutta"), ("Vidya", "Nayak"), ("Malini", "Venkatesh"),
    ("Shalini", "Pillai"), ("Keerthi", "Gowda"), ("Sowmya", "Iyer"), ("Bhavana", "Mehta"),
    ("Meenakshi", "Pawar"), ("Madhavi", "Bhattacharya"), ("Poulami", "Sengupta"), ("Sharmila", "Roy"),
    ("Archana", "Saxena"), ("Geeta", "Trivedi"), ("Nisha", "Pandey"), ("Nithya", "Murthy"),
    ("Kiran", "Yadav"), ("Simran", "Bhasin"), ("Radha", "Chopra"), ("Aarti", "Sharma"),
]


def generate_apaar(seed_idx: int) -> str:
    """Generates a valid 12-digit numeric APAAR reference."""
    return f"{100000000000 + seed_idx}"


def clean_legacy_programmes(db: Session):
    """Safely cleans up any legacy test-generated programmes matching ARCH_%, ISO_TEST_%, or duplicate DIP-MECH."""
    # Clean up legacy unx rolls if present
    for unx_roll in ["25CSE-UNX01", "25CSE-UNX02", "25CSE-UNX03"]:
        rec = db.query(InstitutionStudentRecord).filter_by(institution_student_id=unx_roll).first()
        if rec:
            db.query(AnnualRosterObservation).filter_by(student_identity_id=rec.student_identity_id).delete(synchronize_session=False)
            db.delete(rec)

    legacy_progs = db.query(Programme).filter(
        or_(
            Programme.programme_code.like("ARCH_%"),
            Programme.programme_code.like("ISO_TEST_%"),
            Programme.programme_code == "DIP-MECH",
        )
    ).all()
    for lp in legacy_progs:
        lp_uid = lp.id
        db.query(AnnualRosterObservation).filter_by(programme_id=lp_uid).delete(synchronize_session=False)
        db.query(RosterSnapshot).filter_by(programme_id=lp_uid).delete(synchronize_session=False)
        subs = db.query(SourceSubmission.id).filter_by(programme_id=lp_uid).all()
        sub_ids = [s[0] for s in subs]
        if sub_ids:
            db.query(SubmissionPreview).filter(SubmissionPreview.submission_id.in_(sub_ids)).delete(synchronize_session=False)
            db.query(SourceSubmissionRecord).filter(SourceSubmissionRecord.submission_id.in_(sub_ids)).delete(synchronize_session=False)
        db.query(SourceSubmission).filter_by(programme_id=lp_uid).delete(synchronize_session=False)
        db.query(AdmissionEpisode).filter_by(programme_id=lp_uid).delete(synchronize_session=False)
        db.query(InstitutionStudentRecord).filter_by(programme_id=lp_uid).delete(synchronize_session=False)
        db.query(ApprovalConfiguration).filter_by(programme_id=lp_uid).delete(synchronize_session=False)
        db.query(DiscrepancyCase).filter_by(programme_id=lp_uid).delete(synchronize_session=False)
        db.delete(lp)
    db.flush()


def seed_database():
    db: Session = SessionLocal()
    try:
        print("[SEED] Starting comprehensive demonstration database initialization...")

        # ---------------------------------------------------------------------------
        # 0. Clean Legacy Test-Generated Program Records
        # ---------------------------------------------------------------------------
        clean_legacy_programmes(db)

        # ---------------------------------------------------------------------------
        # 1. Fixed Roles
        # ---------------------------------------------------------------------------
        roles_data = [
            {"role_name": "SYSTEM_ADMIN", "description": "System Administrator with full platform governance", "permissions": {"all": True}},
            {"role_name": "REGULATORY_REVIEWER", "description": "AICTE Regulatory Reviewer with cross-institution oversight", "permissions": {"review": True}},
            {"role_name": "INSTITUTION_ADMIN", "description": "Institution Administrator with institution-scoped rights", "permissions": {"manage": True}},
            {"role_name": "STUDENT_VERIFIER", "description": "External Verifier for authorised verification", "permissions": {"verify": True}},
        ]
        roles_map = {}
        for r in roles_data:
            existing = db.execute(select(Role).where(Role.role_name == r["role_name"])).scalar_one_or_none()
            if not existing:
                role = Role(role_name=r["role_name"], description=r["description"], permissions=r["permissions"])
                db.add(role)
                db.flush()
                roles_map[r["role_name"]] = role
            else:
                roles_map[r["role_name"]] = existing

        # ---------------------------------------------------------------------------
        # 2. Demonstration Institutions (Rich Institutional Profiles)
        # ---------------------------------------------------------------------------
        inst_data = [
            {
                "code": "INST-APEX-001",
                "name": "Apex Institute of Technology",
                "category": "ENGINEERING",
                "state": "Maharashtra",
                "district": "Pune",
                "pincode": "411057",
                "address": "Survey No. 42/1, Marunji Road, Hinjawadi Phase 2, Pune, Maharashtra 411057 (Autonomous Private Engineering Institution - AICTE Permanent Approval)",
                "contact_email": "registrar@apex.edu.in",
            },
            {
                "code": "INST-POLY-002",
                "name": "National Polytechnic College",
                "category": "POLYTECHNIC",
                "state": "Karnataka",
                "district": "Mysuru",
                "pincode": "570006",
                "address": "Post Box No. 14, Manasagangothri, Mysuru, Karnataka 570006 (Government-Aided Polytechnic - Directorate of Technical Education)",
                "contact_email": "principal@polytechnic.edu.in",
            },
            {
                "code": "INST-KAVERI-003",
                "name": "Kaveri University of Science",
                "category": "UNIVERSITY",
                "state": "Tamil Nadu",
                "district": "Coimbatore",
                "pincode": "641004",
                "address": "Avinashi Road, Peelamedu, Coimbatore, Tamil Nadu 641004 (State University established under State Legislature Act)",
                "contact_email": "coe@kaveri.edu.in",
            },
        ]
        inst_map = {}
        for i in inst_data:
            existing = db.execute(select(Institution).where(Institution.institution_code == i["code"])).scalar_one_or_none()
            if not existing:
                inst = Institution(
                    institution_code=i["code"],
                    name=i["name"],
                    category=i["category"],
                    approval_status="APPROVED",
                    state=i["state"],
                    district=i["district"],
                    pincode=i["pincode"],
                    address=i["address"],
                    contact_email=i["contact_email"],
                )
                db.add(inst)
                db.flush()
                inst_map[i["code"]] = inst
            else:
                existing.name = i["name"]
                existing.address = i["address"]
                existing.pincode = i["pincode"]
                existing.contact_email = i["contact_email"]
                inst_map[i["code"]] = existing

        # ---------------------------------------------------------------------------
        # 3. Curated Institutional Programme Catalogue & Varied Approvals
        # ---------------------------------------------------------------------------
        programmes_config = [
            # Apex Institute of Technology (Engineering & Architecture)
            {"inst": "INST-APEX-001", "code": "CSE", "name": "Computer Science and Engineering", "level": "UG", "duration": 4, "intake": 120, "lateral": 10.0, "super": 15.0},
            {"inst": "INST-APEX-001", "code": "IT", "name": "Information Technology", "level": "UG", "duration": 4, "intake": 60, "lateral": 10.0, "super": 15.0},
            {"inst": "INST-APEX-001", "code": "ECE", "name": "Electronics and Communication Engineering", "level": "UG", "duration": 4, "intake": 60, "lateral": 10.0, "super": 15.0},
            {"inst": "INST-APEX-001", "code": "EEE", "name": "Electrical and Electronics Engineering", "level": "UG", "duration": 4, "intake": 60, "lateral": 10.0, "super": 15.0},
            {"inst": "INST-APEX-001", "code": "MECH", "name": "Mechanical Engineering", "level": "UG", "duration": 4, "intake": 60, "lateral": 10.0, "super": 15.0},
            {"inst": "INST-APEX-001", "code": "BARCH", "name": "Bachelor of Architecture", "level": "UG", "duration": 5, "intake": 40, "lateral": 0.0, "super": 10.0},
            {"inst": "INST-APEX-001", "code": "MBA", "name": "Master of Business Administration", "level": "PG", "duration": 2, "intake": 60, "lateral": 0.0, "super": 10.0},

            # National Polytechnic College (Technical Diplomas)
            {"inst": "INST-POLY-002", "code": "DIP-CSE", "name": "Diploma in Computer Engineering", "level": "DIPLOMA", "duration": 3, "intake": 60, "lateral": 0.0, "super": 10.0},
            {"inst": "INST-POLY-002", "code": "DIP-ME", "name": "Diploma in Mechanical Engineering", "level": "DIPLOMA", "duration": 3, "intake": 60, "lateral": 0.0, "super": 10.0},
            {"inst": "INST-POLY-002", "code": "DIP-CE", "name": "Diploma in Civil Engineering", "level": "DIPLOMA", "duration": 3, "intake": 40, "lateral": 0.0, "super": 10.0},
            {"inst": "INST-POLY-002", "code": "DIP-EC", "name": "Diploma in Electronics Engineering", "level": "DIPLOMA", "duration": 3, "intake": 40, "lateral": 0.0, "super": 10.0},

            # Kaveri University of Science (Degree & Post-Graduate)
            {"inst": "INST-KAVERI-003", "code": "CSE", "name": "B.Tech Computer Science and Engineering", "level": "UG", "duration": 4, "intake": 120, "lateral": 10.0, "super": 15.0},
            {"inst": "INST-KAVERI-003", "code": "AIDS", "name": "B.Tech Artificial Intelligence and Data Science", "level": "UG", "duration": 4, "intake": 60, "lateral": 10.0, "super": 15.0},
            {"inst": "INST-KAVERI-003", "code": "BSC-CS", "name": "Bachelor of Science in Computer Science", "level": "UG", "duration": 3, "intake": 50, "lateral": 0.0, "super": 10.0},
            {"inst": "INST-KAVERI-003", "code": "BCA", "name": "Bachelor of Computer Applications", "level": "UG", "duration": 3, "intake": 40, "lateral": 0.0, "super": 10.0},
            {"inst": "INST-KAVERI-003", "code": "BBA", "name": "Bachelor of Business Administration", "level": "UG", "duration": 3, "intake": 60, "lateral": 0.0, "super": 10.0},
            {"inst": "INST-KAVERI-003", "code": "MBA", "name": "Master of Business Administration", "level": "PG", "duration": 2, "intake": 60, "lateral": 0.0, "super": 10.0},
        ]

        prog_map = {}
        for p in programmes_config:
            inst = inst_map[p["inst"]]
            key = f"{p['inst']}:{p['code']}"
            existing_p = db.execute(
                select(Programme).where(Programme.institution_id == inst.id, Programme.programme_code == p["code"])
            ).scalar_one_or_none()
            if not existing_p:
                prog = Programme(
                    institution_id=inst.id,
                    programme_code=p["code"],
                    programme_name=p["name"],
                    qualification_level=p["level"],
                    duration_years=p["duration"],
                    status="ACTIVE",
                )
                db.add(prog)
                db.flush()
                prog_map[key] = prog
            else:
                existing_p.programme_name = p["name"]
                existing_p.qualification_level = p["level"]
                existing_p.duration_years = p["duration"]
                existing_p.status = "ACTIVE"
                prog_map[key] = existing_p

            # Ensure 3 consecutive years of approval configurations exist with varied, realistic intake
            target_prog = prog_map[key]
            for year in ["2023-24", "2024-25", "2025-26"]:
                start_yr = int(year.split("-")[0])
                existing_appr = db.execute(
                    select(ApprovalConfiguration).where(
                        ApprovalConfiguration.institution_id == inst.id,
                        ApprovalConfiguration.programme_id == target_prog.id,
                        ApprovalConfiguration.academic_year == year,
                        ApprovalConfiguration.status == "ACTIVE",
                    )
                ).scalar_one_or_none()

                if not existing_appr:
                    appr = ApprovalConfiguration(
                        institution_id=inst.id,
                        programme_id=target_prog.id,
                        academic_year=year,
                        approved_intake=p["intake"],
                        supernumerary_quota_percentage=p.get("super", 15.0),
                        lateral_entry_quota_percentage=p.get("lateral", 10.0),
                        approval_reference=f"AICTE/EOA/{year}/{p['code']}",
                        effective_from=date(start_yr, 7, 1),
                        effective_to=date(start_yr + 1, 6, 30),
                        configuration_version=1,
                        status="ACTIVE",
                    )
                    db.add(appr)
                else:
                    existing_appr.approved_intake = p["intake"]
                    existing_appr.supernumerary_quota_percentage = p.get("super", 15.0)
                    existing_appr.lateral_entry_quota_percentage = p.get("lateral", 10.0)



        poly_inst = inst_map["INST-POLY-002"]

        # ---------------------------------------------------------------------------
        # 4. User Accounts
        # ---------------------------------------------------------------------------
        users_data = [
            {"email": "sysadmin@aicte.gov.in", "role": "SYSTEM_ADMIN", "inst": None, "first": "System", "last": "Admin", "pass": "SysAdmin#2026!"},
            {"email": "reviewer@aicte.gov.in", "role": "REGULATORY_REVIEWER", "inst": None, "first": "Regulatory", "last": "Reviewer", "pass": "Reviewer#2026!"},
            {"email": "admin@apex.edu.in", "role": "INSTITUTION_ADMIN", "inst": "INST-APEX-001", "first": "Apex", "last": "Admin", "pass": "ApexAdmin#2026!"},
            {"email": "admin@polytechnic.edu.in", "role": "INSTITUTION_ADMIN", "inst": "INST-POLY-002", "first": "Polytechnic", "last": "Admin", "pass": "PolyAdmin#2026!"},
            {"email": "admin@kaveri.edu.in", "role": "INSTITUTION_ADMIN", "inst": "INST-KAVERI-003", "first": "Kaveri", "last": "Admin", "pass": "KaveriAdmin#2026!"},
        ]
        user_map = {}
        for u in users_data:
            existing = db.execute(select(User).where(User.email == u["email"])).scalar_one_or_none()
            inst_obj = inst_map[u["inst"]] if u["inst"] else None
            role_obj = roles_map[u["role"]]
            if not existing:
                user = User(
                    email=u["email"],
                    password_hash=hash_password(u["pass"]),
                    first_name=u["first"],
                    last_name=u["last"],
                    role_id=role_obj.id,
                    institution_id=inst_obj.id if inst_obj else None,
                    is_active=True,
                )
                db.add(user)
                db.flush()
                user_map[u["email"]] = user
            else:
                existing.first_name = u["first"]
                existing.last_name = u["last"]
                existing.role_id = role_obj.id
                existing.institution_id = inst_obj.id if inst_obj else None
                user_map[u["email"]] = existing

        # ---------------------------------------------------------------------------
        # 5. Mandatory Apex CSE 120-Student Scenario (Strictly Preserved)
        # Baseline 2024-25: 120 | Candidate 2025-26: 120 | Continuing: 115
        # Lateral Entry In: 2 | Unexplained Appearance: 3 | Outbound Transfer: 1 | Departures: 4
        # Total Unique Students: Exactly 125
        # ---------------------------------------------------------------------------
        apex_inst = inst_map["INST-APEX-001"]
        apex_cse = prog_map["INST-APEX-001:CSE"]
        apex_user = user_map["admin@apex.edu.in"]
        kaveri_inst = inst_map["INST-KAVERI-003"]
        kaveri_bsc = prog_map["INST-KAVERI-003:BSC-CS"]

        print("[SEED] Generating 120-Student Longitudinal Cohort Scenario for Apex CSE...")

        # 5.0 Ensure Authoritative SourceSubmissions exist specifically for the 120 scenario
        sub_base = db.execute(
            select(SourceSubmission).where(
                SourceSubmission.institution_id == apex_inst.id,
                SourceSubmission.programme_id == apex_cse.id,
                SourceSubmission.academic_year == "2024-25",
                SourceSubmission.total_rows_count == 120,
                SourceSubmission.submission_status == "COMMITTED",
            )
        ).scalars().first()

        if not sub_base:
            sub_base = SourceSubmission(
                institution_id=apex_inst.id,
                programme_id=apex_cse.id,
                academic_year="2024-25",
                submission_type="ANNUAL_ROSTER",
                submission_status="COMMITTED",
                original_filename="apex_cse_2024_25_baseline_roster.csv",
                storage_key="seed/apex_cse_2024_25_baseline_roster.csv",
                file_fingerprint="f78bc0981e4b1a8d4c321ef0021a8b9c1d2e3f4a5b6c7d8e9f0123456789abcd",
                file_size_bytes=14200,
                total_rows_count=120,
                valid_rows_count=120,
                uploaded_by_user_id=apex_user.id,
            )
            db.add(sub_base)
            db.flush()

        sub_cand = db.execute(
            select(SourceSubmission).where(
                SourceSubmission.institution_id == apex_inst.id,
                SourceSubmission.programme_id == apex_cse.id,
                SourceSubmission.academic_year == "2025-26",
                SourceSubmission.total_rows_count == 120,
                SourceSubmission.submission_status == "COMMITTED",
            )
        ).scalars().first()

        if not sub_cand:
            sub_cand = SourceSubmission(
                institution_id=apex_inst.id,
                programme_id=apex_cse.id,
                academic_year="2025-26",
                submission_type="ANNUAL_ROSTER",
                submission_status="COMMITTED",
                original_filename="apex_cse_2025_26_candidate_roster.csv",
                storage_key="seed/apex_cse_2025_26_candidate_roster.csv",
                file_fingerprint="e89cd1092f5c2b9e5d432fa1132b9c0d2e3f4a5b6c7d8e9f0123456789bcde",
                file_size_bytes=14250,
                total_rows_count=120,
                valid_rows_count=120,
                uploaded_by_user_id=apex_user.id,
            )
            db.add(sub_cand)
            db.flush()

        continuing_identities = []

        # 5.1 Continuing Students: Exactly 115 Students (24CSE001 to 24CSE115)
        for idx in range(1, 116):
            roll = f"24CSE{idx:03d}"
            apaar = generate_apaar(2000000 + idx)

            is_male = (idx % 2 == 1)
            f_list = NAMES_MALE if is_male else NAMES_FEMALE
            fn, ln = f_list[idx % len(f_list)]
            name = f"{fn} {ln}"

            # Quota distribution (General, EWS, TFW, Supernumerary)
            if idx <= 90:
                adm_cat = "REGULAR"
                seat_cat = "SANCTIONED_REGULAR"
                channel = "STATE_COUNSELLING"
                nat_cat = "DOMICILE"
            elif idx <= 100:
                adm_cat = "EWS"
                seat_cat = "SUPERNUMERARY"
                channel = "STATE_COUNSELLING"
                nat_cat = "DOMICILE"
            elif idx <= 105:
                adm_cat = "TFWS"
                seat_cat = "SUPERNUMERARY"
                channel = "STATE_COUNSELLING"
                nat_cat = "DOMICILE"
            else:
                adm_cat = "PIO_FN"
                seat_cat = "FOREIGN_NATIONAL"
                channel = "DIRECT_ADMISSION"
                nat_cat = "FOREIGN_NATIONAL"

            existing_rec = db.execute(
                select(InstitutionStudentRecord).where(
                    InstitutionStudentRecord.institution_id == apex_inst.id,
                    InstitutionStudentRecord.institution_student_id == roll,
                )
            ).scalar_one_or_none()

            if not existing_rec:
                ident, rec, ep = IdentityService.register_student(
                    db=db,
                    institution_id=apex_inst.id,
                    programme_id=apex_cse.id,
                    institution_student_id=roll,
                    full_name=name,
                    academic_year="2024-25",
                    admission_date=date(2024, 7, 15),
                    raw_apaar=apaar,
                    date_of_birth=date(2005, 1 + (idx % 12), 1 + (idx % 28)),
                    gender="M" if is_male else "F",
                    admission_category=adm_cat,
                    supernumerary_status=(idx > 105),
                    source_submission_id=sub_base.id,
                )
                ep.nationality_category = nat_cat
                ep.admission_channel = channel
                ep.seat_accounting_category = seat_cat
                ep.entry_level = "FIRST_YEAR"

                obs_25 = AnnualRosterObservation(
                    student_identity_id=ident.id,
                    institution_id=apex_inst.id,
                    programme_id=apex_cse.id,
                    academic_year="2025-26",
                    student_status="ACTIVE",
                    source_submission_id=sub_cand.id,
                    observation_metadata={"roll_no": roll, "year_of_study": 2, "remarks": "Promoted to 2nd Year CSE"},
                )
                db.add(obs_25)
                continuing_identities.append(ident)
            else:
                ident = db.execute(select(StudentIdentity).where(StudentIdentity.id == existing_rec.student_identity_id)).scalar_one()
                ident.full_name = name
                status_v, _, masked_v, blind_v = validate_apaar_format(apaar)
                ident.identity_status = status_v
                ident.masked_apaar_reference = masked_v
                ident.apaar_blind_index = blind_v

                continuing_identities.append(ident)

                # Ensure 2024-25 baseline observation is explicitly linked to sub_base
                obs_24 = db.execute(
                    select(AnnualRosterObservation).where(
                        AnnualRosterObservation.student_identity_id == ident.id,
                        AnnualRosterObservation.institution_id == apex_inst.id,
                        AnnualRosterObservation.academic_year == "2024-25",
                    )
                ).scalars().first()
                if not obs_24:
                    obs_24 = AnnualRosterObservation(
                        student_identity_id=ident.id,
                        institution_id=apex_inst.id,
                        programme_id=apex_cse.id,
                        academic_year="2024-25",
                        student_status="ACTIVE",
                        source_submission_id=sub_base.id,
                        observation_metadata={"roll_no": roll, "year_of_study": 1},
                    )
                    db.add(obs_24)
                else:
                    obs_24.source_submission_id = sub_base.id
                    obs_24.student_status = "ACTIVE"

                # Ensure 2025-26 candidate observation is explicitly linked to sub_cand
                obs_25 = db.execute(
                    select(AnnualRosterObservation).where(
                        AnnualRosterObservation.student_identity_id == ident.id,
                        AnnualRosterObservation.institution_id == apex_inst.id,
                        AnnualRosterObservation.academic_year == "2025-26",
                    )
                ).scalars().first()
                if obs_25:
                    obs_25.source_submission_id = sub_cand.id
                    obs_25.student_status = "ACTIVE"
                else:
                    obs_25 = AnnualRosterObservation(
                        student_identity_id=ident.id,
                        institution_id=apex_inst.id,
                        programme_id=apex_cse.id,
                        academic_year="2025-26",
                        student_status="ACTIVE",
                        source_submission_id=sub_cand.id,
                        observation_metadata={"roll_no": roll, "year_of_study": 2, "remarks": "Promoted to 2nd Year CSE"},
                    )
                    db.add(obs_25)

        # 5.2 Baseline Departures: Exactly 5 Students (24CSE116 to 24CSE120)
        # 1 documented outbound transfer + 4 withdrawals
        departures_config = [
            ("24CSE116", "Manish S. Rao", "TRANSFER_OUT", "Documented Inter-University Transfer to Kaveri University B.Sc CS"),
            ("24CSE117", "Simran Bhasin", "WITHDRAWN", "Voluntary Academic Withdrawal"),
            ("24CSE118", "Devendra N. Parmar", "WITHDRAWN", "Personal Medical Withdrawal"),
            ("24CSE119", "Aarti Sharma", "WITHDRAWN", "Relocation to Other State"),
            ("24CSE120", "Naveen Barman", "WITHDRAWN", "Discontinued Studies"),
        ]

        for roll, name, exit_type, reason in departures_config:
            idx = int(roll.replace("24CSE", ""))
            apaar = generate_apaar(2000000 + idx)
            is_male = (idx % 2 == 1)

            existing_rec = db.execute(
                select(InstitutionStudentRecord).where(
                    InstitutionStudentRecord.institution_id == apex_inst.id,
                    InstitutionStudentRecord.institution_student_id == roll,
                )
            ).scalar_one_or_none()

            if not existing_rec:
                ident, rec, ep = IdentityService.register_student(
                    db=db,
                    institution_id=apex_inst.id,
                    programme_id=apex_cse.id,
                    institution_student_id=roll,
                    full_name=name,
                    academic_year="2024-25",
                    admission_date=date(2024, 7, 20),
                    raw_apaar=apaar,
                    date_of_birth=date(2005, 6, 15),
                    gender="M" if is_male else "F",
                    admission_category="REGULAR",
                    source_submission_id=sub_base.id,
                )
                if exit_type == "TRANSFER_OUT":
                    tr_out = TransferEvent(
                        student_identity_id=ident.id,
                        source_institution_id=apex_inst.id,
                        destination_institution_id=kaveri_inst.id,
                        source_programme_id=apex_cse.id,
                        destination_programme_id=kaveri_bsc.id,
                        transfer_date=date(2025, 6, 15),
                        academic_year="2024-25",
                        verification_status="DOCUMENTED",
                        transfer_reason=reason,
                    )
                    db.add(tr_out)
            else:
                ident = db.execute(select(StudentIdentity).where(StudentIdentity.id == existing_rec.student_identity_id)).scalar_one()
                ident.full_name = name

                # Ensure 2024-25 baseline observation is explicitly linked
                obs_24 = db.execute(
                    select(AnnualRosterObservation).where(
                        AnnualRosterObservation.student_identity_id == ident.id,
                        AnnualRosterObservation.institution_id == apex_inst.id,
                        AnnualRosterObservation.academic_year == "2024-25",
                    )
                ).scalars().first()
                if not obs_24:
                    obs_24 = AnnualRosterObservation(
                        student_identity_id=ident.id,
                        institution_id=apex_inst.id,
                        programme_id=apex_cse.id,
                        academic_year="2024-25",
                        student_status="ACTIVE",
                        source_submission_id=sub_base.id,
                        observation_metadata={"roll_no": roll, "remarks": exit_type},
                    )
                    db.add(obs_24)
                else:
                    obs_24.source_submission_id = sub_base.id
                    obs_24.student_status = "ACTIVE"

                # Ensure outbound transfer event is documented
                if exit_type == "TRANSFER_OUT":
                    existing_tr = db.execute(
                        select(TransferEvent).where(
                            TransferEvent.student_identity_id == ident.id,
                            TransferEvent.source_institution_id == apex_inst.id,
                        )
                    ).scalars().first()
                    if not existing_tr:
                        tr_out = TransferEvent(
                            student_identity_id=ident.id,
                            source_institution_id=apex_inst.id,
                            destination_institution_id=kaveri_inst.id,
                            source_programme_id=apex_cse.id,
                            destination_programme_id=kaveri_bsc.id,
                            transfer_date=date(2025, 6, 15),
                            academic_year="2024-25",
                            verification_status="DOCUMENTED",
                            transfer_reason=reason,
                        )
                        db.add(tr_out)
                    else:
                        existing_tr.verification_status = "DOCUMENTED"

                # Ensure candidate observation is removed if any
                db.execute(
                    update(AnnualRosterObservation)
                    .where(
                        AnnualRosterObservation.student_identity_id == ident.id,
                        AnnualRosterObservation.institution_id == apex_inst.id,
                        AnnualRosterObservation.academic_year == "2025-26",
                    )
                    .values(source_submission_id=None, student_status="WITHDRAWN")
                )

        # 5.3 Documented Transfer-In Students: Exactly 2 Students (25CSE-TR01, 25CSE-TR02)
        # Vertical mobility from National Polytechnic DIP-CSE to Apex CSE Lateral Entry Year 2
        poly_cse = prog_map["INST-POLY-002:DIP-CSE"]
        poly_user = user_map["admin@polytechnic.edu.in"]

        for t_name, t_roll, poly_roll, t_dob, t_gender in [
            ("Pooja Sundaram", "25CSE-TR01", "22DCSE014", date(2004, 3, 14), "F"),
            ("Arvind G. Nair", "25CSE-TR02", "22DCSE028", date(2004, 8, 22), "M"),
        ]:
            existing_rec = db.execute(
                select(InstitutionStudentRecord).where(
                    InstitutionStudentRecord.institution_id == apex_inst.id,
                    InstitutionStudentRecord.institution_student_id == t_roll,
                )
            ).scalar_one_or_none()

            if not existing_rec:
                t_apaar = generate_apaar(2100000 + int(t_roll.replace("25CSE-TR0", "")))
                t_ident, t_rec, t_ep = IdentityService.register_student(
                    db=db,
                    institution_id=apex_inst.id,
                    programme_id=apex_cse.id,
                    institution_student_id=t_roll,
                    full_name=t_name,
                    academic_year="2025-26",
                    admission_date=date(2025, 8, 1),
                    raw_apaar=t_apaar,
                    date_of_birth=t_dob,
                    gender=t_gender,
                    admission_category="LATERAL_ENTRY",
                    entry_level="SECOND_YEAR_LATERAL",
                    source_submission_id=sub_cand.id,
                )
                t_ep.previous_institution_code = "INST-POLY-002"
                t_ep.previous_programme_code = "DIP-CSE"

                t_event = TransferEvent(
                    student_identity_id=t_ident.id,
                    source_institution_id=poly_inst.id,
                    destination_institution_id=apex_inst.id,
                    source_programme_id=poly_cse.id,
                    destination_programme_id=apex_cse.id,
                    transfer_date=date(2025, 7, 28),
                    academic_year="2025-26",
                    verification_status="DOCUMENTED",
                    transfer_reason="AICTE Lateral Entry Diploma-to-Degree Mobility into 3rd Semester",
                )
                db.add(t_event)

                obs_cand = AnnualRosterObservation(
                    student_identity_id=t_ident.id,
                    institution_id=apex_inst.id,
                    programme_id=apex_cse.id,
                    academic_year="2025-26",
                    student_status="ACTIVE",
                    source_submission_id=sub_cand.id,
                    observation_metadata={"roll_no": t_roll, "year_of_study": 2, "entry_mode": "LATERAL_ENTRY"},
                )
                db.add(obs_cand)
            else:
                ident = db.execute(select(StudentIdentity).where(StudentIdentity.id == existing_rec.student_identity_id)).scalar_one()
                ident.full_name = t_name
                obs = db.execute(
                    select(AnnualRosterObservation).where(
                        AnnualRosterObservation.student_identity_id == ident.id,
                        AnnualRosterObservation.academic_year == "2025-26",
                        AnnualRosterObservation.institution_id == apex_inst.id,
                    )
                ).scalars().first()
                if obs:
                    obs.source_submission_id = sub_cand.id
                    obs.student_status = "ACTIVE"
                else:
                    obs_cand = AnnualRosterObservation(
                        student_identity_id=ident.id,
                        institution_id=apex_inst.id,
                        programme_id=apex_cse.id,
                        academic_year="2025-26",
                        student_status="ACTIVE",
                        source_submission_id=sub_cand.id,
                        observation_metadata={"roll_no": t_roll, "year_of_study": 2, "entry_mode": "LATERAL_ENTRY"},
                    )
                    db.add(obs_cand)

                # Ensure documented transfer event exists
                existing_tr = db.execute(
                    select(TransferEvent).where(
                        TransferEvent.student_identity_id == ident.id,
                        TransferEvent.destination_institution_id == apex_inst.id,
                    )
                ).scalars().first()
                if not existing_tr:
                    t_event = TransferEvent(
                        student_identity_id=ident.id,
                        source_institution_id=poly_inst.id,
                        destination_institution_id=apex_inst.id,
                        source_programme_id=poly_cse.id,
                        destination_programme_id=apex_cse.id,
                        transfer_date=date(2025, 7, 28),
                        academic_year="2025-26",
                        verification_status="DOCUMENTED",
                        transfer_reason="AICTE Lateral Entry Diploma-to-Degree Mobility into 3rd Semester",
                    )
                    db.add(t_event)
                else:
                    existing_tr.verification_status = "DOCUMENTED"

        # 5.4 Unexplained Appearances: Exactly 3 Students (25CSE-UN01, 25CSE-UN02, 25CSE-UN03)
        # Present on 2025-26 candidate roster WITHOUT admission episode or transfer record
        for u_name, u_roll, u_apaar in [
            ("Tanmay Bhat", "25CSE-UN01", "100223344551"),
            ("Deepa Shenoy", "25CSE-UN02", "100223344552"),
            ("Souvik Mukherjee", "25CSE-UN03", "100223344553"),
        ]:
            existing_rec = db.execute(
                select(InstitutionStudentRecord).where(
                    InstitutionStudentRecord.institution_id == apex_inst.id,
                    InstitutionStudentRecord.institution_student_id == u_roll,
                )
            ).scalar_one_or_none()

            if not existing_rec:
                status_v, _, masked_v, blind_v = validate_apaar_format(u_apaar)
                u_ident = StudentIdentity(
                    full_name=u_name,
                    identity_status="FORMAT_VALID",
                    masked_apaar_reference=masked_v,
                    apaar_blind_index=blind_v,
                    date_of_birth=date(2005, 5, 20),
                    gender="M" if "Mukherjee" in u_name or "Bhat" in u_name else "F",
                )
                db.add(u_ident)
                db.flush()

                u_rec = InstitutionStudentRecord(
                    institution_id=apex_inst.id,
                    programme_id=apex_cse.id,
                    student_identity_id=u_ident.id,
                    institution_student_id=u_roll,
                    status="ACTIVE",
                )
                db.add(u_rec)

                u_obs = AnnualRosterObservation(
                    student_identity_id=u_ident.id,
                    institution_id=apex_inst.id,
                    programme_id=apex_cse.id,
                    academic_year="2025-26",
                    student_status="ACTIVE",
                    source_submission_id=sub_cand.id,
                    observation_metadata={"roll_no": u_roll, "remarks": "Unreconciled Appearance on 2025-26 Roster"},
                )
                db.add(u_obs)
            else:
                ident = db.execute(select(StudentIdentity).where(StudentIdentity.id == existing_rec.student_identity_id)).scalar_one()
                ident.full_name = u_name
                obs = db.execute(
                    select(AnnualRosterObservation).where(
                        AnnualRosterObservation.student_identity_id == ident.id,
                        AnnualRosterObservation.academic_year == "2025-26",
                        AnnualRosterObservation.institution_id == apex_inst.id,
                    )
                ).scalars().first()
                if obs:
                    obs.source_submission_id = sub_cand.id
                    obs.student_status = "ACTIVE"
                else:
                    u_obs = AnnualRosterObservation(
                        student_identity_id=ident.id,
                        institution_id=apex_inst.id,
                        programme_id=apex_cse.id,
                        academic_year="2025-26",
                        student_status="ACTIVE",
                        source_submission_id=sub_cand.id,
                        observation_metadata={"roll_no": u_roll, "remarks": "Unreconciled Appearance on 2025-26 Roster"},
                    )
                    db.add(u_obs)

                # Ensure no baseline observation or admission episode exists
                db.execute(
                    delete_obs := select(AnnualRosterObservation).where(
                        AnnualRosterObservation.student_identity_id == ident.id,
                        AnnualRosterObservation.academic_year == "2024-25",
                    )
                )
                db.query(AnnualRosterObservation).filter(
                    AnnualRosterObservation.student_identity_id == ident.id,
                    AnnualRosterObservation.academic_year == "2024-25",
                ).delete(synchronize_session=False)

        # 5.5 Authoritative Snapshots for Apex CSE
        # Clear any conflicting authoritative flags for Apex CSE
        db.execute(
            update(RosterSnapshot)
            .where(
                RosterSnapshot.institution_id == apex_inst.id,
                RosterSnapshot.programme_id == apex_cse.id,
                RosterSnapshot.academic_year == "2024-25",
            )
            .values(is_authoritative=False)
        )
        db.flush()

        existing_snap_base = db.execute(
            select(RosterSnapshot).where(
                RosterSnapshot.institution_id == apex_inst.id,
                RosterSnapshot.programme_id == apex_cse.id,
                RosterSnapshot.academic_year == "2024-25",
                RosterSnapshot.observed_headcount == 120,
            )
        ).scalars().first()

        if not existing_snap_base:
            snap_base = RosterSnapshot(
                institution_id=apex_inst.id,
                programme_id=apex_cse.id,
                academic_year="2024-25",
                source_submission_id=sub_base.id,
                is_authoritative=True,
                declared_headcount=120,
                observed_headcount=120,
                snapshot_hash="f78bc0981e4b1a8d4c321ef0021a8b9c1d2e3f4a5b6c7d8e9f0123456789abcd",
                snapshot_metadata={"title": "Apex CSE 2024-25 Baseline Snapshot (120 Students)", "population_definition": "ALL_ENROLLED_REGULAR"},
                created_by_user_id=apex_user.id,
            )
            db.add(snap_base)
        else:
            existing_snap_base.source_submission_id = sub_base.id
            existing_snap_base.is_authoritative = True
            existing_snap_base.declared_headcount = 120
            existing_snap_base.observed_headcount = 120

        db.flush()

        db.execute(
            update(RosterSnapshot)
            .where(
                RosterSnapshot.institution_id == apex_inst.id,
                RosterSnapshot.programme_id == apex_cse.id,
                RosterSnapshot.academic_year == "2025-26",
            )
            .values(is_authoritative=False)
        )
        db.flush()

        existing_snap_cand = db.execute(
            select(RosterSnapshot).where(
                RosterSnapshot.institution_id == apex_inst.id,
                RosterSnapshot.programme_id == apex_cse.id,
                RosterSnapshot.academic_year == "2025-26",
                RosterSnapshot.observed_headcount == 120,
            )
        ).scalars().first()

        if not existing_snap_cand:
            snap_cand = RosterSnapshot(
                institution_id=apex_inst.id,
                programme_id=apex_cse.id,
                academic_year="2025-26",
                source_submission_id=sub_cand.id,
                is_authoritative=True,
                declared_headcount=120,
                observed_headcount=120,
                snapshot_hash="e89cd1092f5c2b9e5d432fa1132b9c0d2e3f4a5b6c7d8e9f0123456789bcde",
                snapshot_metadata={"title": "Apex CSE 2025-26 Candidate Snapshot (120 Students)", "population_definition": "ALL_ENROLLED_REGULAR"},
                created_by_user_id=apex_user.id,
            )
            db.add(snap_cand)
        else:
            existing_snap_cand.source_submission_id = sub_cand.id
            existing_snap_cand.is_authoritative = True
            existing_snap_cand.declared_headcount = 120
            existing_snap_cand.observed_headcount = 120

        db.flush()

        # ---------------------------------------------------------------------------
        # 6. Additional Multi-Institution Synthetic Student Records
        # Seeded across all 3 institutions with Submissions, Snapshots, and Edge Cases
        # ---------------------------------------------------------------------------
        print("[SEED] Seeding multi-institution student cohorts and cross-institution relationships...")
        kaveri_user = user_map["admin@kaveri.edu.in"]

        cohort_specs = [
            # Inst Code, Prog Code, User, Count, Roll Prefix, Filename
            # Apex Institute
            ("INST-APEX-001", "IT", apex_user, 30, "24APEX-IT-", "apex_it_2024_25_annual_roster.csv"),
            ("INST-APEX-001", "ECE", apex_user, 40, "24APEX-ECE-", "apex_ece_2024_25_annual_roster.csv"),
            ("INST-APEX-001", "EEE", apex_user, 25, "24APEX-EEE-", "apex_eee_2024_25_annual_roster.csv"),
            ("INST-APEX-001", "MECH", apex_user, 35, "24APEX-MECH-", "apex_mech_2024_25_annual_roster.csv"),
            ("INST-APEX-001", "BARCH", apex_user, 20, "24APEX-BARCH-", "apex_barch_2024_25_annual_roster.csv"),
            ("INST-APEX-001", "MBA", apex_user, 25, "24APEX-MBA-", "apex_mba_2024_25_annual_roster.csv"),

            # National Polytechnic
            ("INST-POLY-002", "DIP-CSE", poly_user, 45, "24POLY-CSE-", "poly_dcse_2024_25_annual_roster.xlsx"),
            ("INST-POLY-002", "DIP-ME", poly_user, 35, "24POLY-ME-", "poly_dme_2024_25_annual_roster.xlsx"),
            ("INST-POLY-002", "DIP-CE", poly_user, 25, "24POLY-CE-", "poly_dce_2024_25_annual_roster.xlsx"),
            ("INST-POLY-002", "DIP-EC", poly_user, 25, "24POLY-EC-", "poly_dec_2024_25_annual_roster.xlsx"),

            # Kaveri University
            ("INST-KAVERI-003", "CSE", kaveri_user, 35, "24KAV-CSE-", "kaveri_cse_2024_25_enrolment.csv"),
            ("INST-KAVERI-003", "AIDS", kaveri_user, 30, "24KAV-AIDS-", "kaveri_aids_2024_25_enrolment.csv"),
            ("INST-KAVERI-003", "BSC-CS", kaveri_user, 45, "24KAV-BSCS-", "kaveri_bsc_cs_2024_25_enrolment.csv"),
            ("INST-KAVERI-003", "BCA", kaveri_user, 40, "24KAV-BCA-", "kaveri_bca_2024_25_enrolment.csv"),
            ("INST-KAVERI-003", "BBA", kaveri_user, 30, "24KAV-BBA-", "kaveri_bba_2024_25_enrolment.csv"),
            ("INST-KAVERI-003", "MBA", kaveri_user, 25, "24KAV-MBA-", "kaveri_mba_2024_25_enrolment.csv"),
        ]

        # Intentional Cross-Institution Dual Enrolments for Duplicate Detection
        conflict_apaars = ["998877665501", "998877665502"]
        apaar_seq = 3100000

        for inst_code, prog_code, u_actor, count, roll_pfx, fname in cohort_specs:
            target_inst = inst_map[inst_code]
            target_prog = prog_map[f"{inst_code}:{prog_code}"]

            # 1. SourceSubmission for this programme's roster
            sub = db.execute(
                select(SourceSubmission).where(
                    SourceSubmission.institution_id == target_inst.id,
                    SourceSubmission.programme_id == target_prog.id,
                    SourceSubmission.academic_year == "2024-25",
                    SourceSubmission.submission_status == "COMMITTED",
                )
            ).scalars().first()

            if not sub:
                sub_hash = hashlib.sha256(f"{inst_code}:{prog_code}:2024-25".encode()).hexdigest()
                sub = SourceSubmission(
                    institution_id=target_inst.id,
                    programme_id=target_prog.id,
                    academic_year="2024-25",
                    submission_type="ANNUAL_ROSTER",
                    submission_status="COMMITTED",
                    original_filename=fname,
                    storage_key=f"seed/{fname}",
                    file_fingerprint=sub_hash,
                    file_size_bytes=count * 115,
                    total_rows_count=count,
                    valid_rows_count=count,
                    uploaded_by_user_id=u_actor.id,
                )
                db.add(sub)
                db.flush()

            # 2. Authoritative RosterSnapshot
            db.execute(
                update(RosterSnapshot)
                .where(
                    RosterSnapshot.institution_id == target_inst.id,
                    RosterSnapshot.programme_id == target_prog.id,
                    RosterSnapshot.academic_year == "2024-25",
                )
                .values(is_authoritative=False)
            )
            db.flush()

            snap = db.execute(
                select(RosterSnapshot).where(
                    RosterSnapshot.institution_id == target_inst.id,
                    RosterSnapshot.programme_id == target_prog.id,
                    RosterSnapshot.academic_year == "2024-25",
                )
            ).scalars().first()

            if not snap:
                snap = RosterSnapshot(
                    institution_id=target_inst.id,
                    programme_id=target_prog.id,
                    academic_year="2024-25",
                    source_submission_id=sub.id,
                    is_authoritative=True,
                    declared_headcount=count,
                    observed_headcount=count,
                    snapshot_hash=sub.file_fingerprint,
                    snapshot_metadata={"title": f"{target_inst.name} {target_prog.programme_code} 2024-25 Roster", "population_definition": "ALL_ENROLLED_REGULAR"},
                    created_by_user_id=u_actor.id,
                )
                db.add(snap)
            else:
                snap.source_submission_id = sub.id
                snap.is_authoritative = True
                snap.declared_headcount = count
                snap.observed_headcount = count
            db.flush()

            # 3. Seed Students for this programme
            for c_idx in range(1, count + 1):
                roll = f"{roll_pfx}{c_idx:03d}"
                apaar_seq += 1

                # Intentional Dual Enrolment linkage for the first 2 students between Polytechnic and Kaveri
                if "POLY" in inst_code and c_idx in (1, 2):
                    apaar = conflict_apaars[c_idx - 1]
                elif "KAVERI" in inst_code and "BCA" in prog_code and c_idx in (1, 2):
                    apaar = conflict_apaars[c_idx - 1]
                elif c_idx == count:
                    apaar = None  # Missing APAAR edge-case
                elif c_idx == count - 1:
                    apaar = f"9999{apaar_seq:08d}"[:12]  # Unverified APAAR format
                else:
                    apaar = generate_apaar(apaar_seq)

                is_male = (c_idx % 2 == 1)
                f_list = NAMES_MALE if is_male else NAMES_FEMALE
                fn, ln = f_list[c_idx % len(f_list)]
                st_name = f"{fn} {ln}"

                existing_rec = db.execute(
                    select(InstitutionStudentRecord).where(
                        InstitutionStudentRecord.institution_id == target_inst.id,
                        InstitutionStudentRecord.institution_student_id == roll,
                    )
                ).scalar_one_or_none()

                if not existing_rec:
                    ident, rec, ep = IdentityService.register_student(
                        db=db,
                        institution_id=target_inst.id,
                        programme_id=target_prog.id,
                        institution_student_id=roll,
                        full_name=st_name,
                        academic_year="2024-25",
                        admission_date=date(2024, 8, 10),
                        raw_apaar=apaar,
                        date_of_birth=date(2005, 1 + (c_idx % 12), 1 + (c_idx % 28)),
                        gender="M" if is_male else "F",
                        admission_category="REGULAR",
                        source_submission_id=sub.id,
                    )
                else:
                    ident = db.execute(select(StudentIdentity).where(StudentIdentity.id == existing_rec.student_identity_id)).scalar_one()
                    ident.full_name = st_name
                    if apaar:
                        status_v, _, masked_v, blind_v = validate_apaar_format(apaar)
                        ident.identity_status = status_v
                        ident.masked_apaar_reference = masked_v
                        ident.apaar_blind_index = blind_v

                    # Link observation to sub
                    obs = db.execute(
                        select(AnnualRosterObservation).where(
                            AnnualRosterObservation.student_identity_id == ident.id,
                            AnnualRosterObservation.institution_id == target_inst.id,
                            AnnualRosterObservation.programme_id == target_prog.id,
                            AnnualRosterObservation.academic_year == "2024-25",
                        )
                    ).scalars().first()
                    if obs:
                        obs.source_submission_id = sub.id
                        obs.student_status = "ACTIVE"
                    else:
                        obs = AnnualRosterObservation(
                            student_identity_id=ident.id,
                            institution_id=target_inst.id,
                            programme_id=target_prog.id,
                            academic_year="2024-25",
                            student_status="ACTIVE",
                            source_submission_id=sub.id,
                            observation_metadata={"roll_no": roll},
                        )
                        db.add(obs)

        # ---------------------------------------------------------------------------
        # 7. Historical Aggregate Declarations (Module 9 Demo Data)
        # ---------------------------------------------------------------------------
        print("[SEED] Seeding historical aggregate declarations (Module 9)...")
        declarations_data = [
            # Apex CSE 2024-25: Exact Match with 120 Roster
            {
                "inst": "INST-APEX-001", "prog": "CSE", "year": "2024-25",
                "declared": 120, "pop": "ALL_ENROLLED_REGULAR", "ref": "AICTE-MD-2024-APEX-CSE-FINAL",
                "method": "HEADCOUNT", "src": "AICTE_MANDATORY_DISCLOSURE"
            },
            # Apex CSE 2024-25 (Preliminary Census): Declared 124 (Declared Excess variance: -4)
            {
                "inst": "INST-APEX-001", "prog": "CSE", "year": "2024-25",
                "declared": 124, "pop": "ALL_ENROLLED_REGULAR", "ref": "FALL-CENSUS-2024-APEX-CSE",
                "method": "HEADCOUNT", "src": "STATE_DTE_SUBMISSION"
            },
            # Apex CSE 2024-25: Non-comparable population definition (Part Time)
            {
                "inst": "INST-APEX-001", "prog": "CSE", "year": "2024-25",
                "declared": 40, "pop": "PART_TIME_ONLY", "ref": "AICTE-PT-2024-APEX-CSE",
                "method": "CREDIT_THRESHOLD", "src": "AICTE_MANDATORY_DISCLOSURE"
            },
            # Polytechnic DIP-CSE 2024-25: Declared 45 (Exact Match)
            {
                "inst": "INST-POLY-002", "prog": "DIP-CSE", "year": "2024-25",
                "declared": 45, "pop": "ALL_ENROLLED_REGULAR", "ref": "DTE-KAR-2024-DIP-CSE",
                "method": "HEADCOUNT", "src": "ANNUAL_REPORT"
            },
            # Kaveri BSC-CS 2024-25: Declared 45 (Exact Match)
            {
                "inst": "INST-KAVERI-003", "prog": "BSC-CS", "year": "2024-25",
                "declared": 45, "pop": "ALL_ENROLLED_REGULAR", "ref": "TNDTE-2024-BSC-CS-FINAL",
                "method": "HEADCOUNT", "src": "ANNUAL_REPORT"
            },
        ]

        for d in declarations_data:
            target_inst = inst_map[d["inst"]]
            target_prog = prog_map[f"{d['inst']}:{d['prog']}"]

            existing_decl = db.execute(
                select(AggregateEnrolmentDeclaration).where(
                    AggregateEnrolmentDeclaration.institution_id == target_inst.id,
                    AggregateEnrolmentDeclaration.programme_id == target_prog.id,
                    AggregateEnrolmentDeclaration.academic_year == d["year"],
                    AggregateEnrolmentDeclaration.source_reference == d["ref"],
                )
            ).scalar_one_or_none()

            if not existing_decl:
                decl = AggregateEnrolmentDeclaration(
                    institution_id=target_inst.id,
                    programme_id=target_prog.id,
                    academic_year=d["year"],
                    declared_count=d["declared"],
                    population_definition=d["pop"],
                    student_status_definition="ACTIVE_ON_ROLL",
                    counting_methodology=d["method"],
                    reporting_source=d["src"],
                    source_reference=d["ref"],
                    declaration_date=date(2024, 9, 1),
                )
                db.add(decl)

        db.commit()

        # ---------------------------------------------------------------------------
        # 8. Operational Discrepancy Cases & Reasoned Review Decisions
        # ---------------------------------------------------------------------------
        print("[SEED] Seeding operational discrepancy cases and reviewer decisions...")

        recon_run = db.execute(select(ReconciliationRun)).scalars().first()
        if not recon_run:
            recon_run = ReconciliationRun(
                institution_id=apex_inst.id,
                programme_id=apex_cse.id,
                academic_year="2025-26",
                candidate_snapshot_id=existing_snap_cand.id if existing_snap_cand else snap_cand.id,
                candidate_snapshot_hash="e89cd1092f5c2b9e5d432fa1132b9c0d2e3f4a5b6c7d8e9f0123456789bcde",
                baseline_snapshot_id=existing_snap_base.id if existing_snap_base else snap_base.id,
                baseline_snapshot_hash="f78bc0981e4b1a8d4c321ef0021a8b9c1d2e3f4a5b6c7d8e9f0123456789abcd",
                run_fingerprint=hashlib.sha256(b"apex_cse_recon_demo").hexdigest(),
                engine_version="v1.0",
                rules_version="v1.0-rules-apaar-setu",
                summary_metrics={"CONTINUING": 115, "TOTAL_CANDIDATE": 120, "TOTAL_BASELINE": 120},
                executed_by_user_id=apex_user.id,
            )
            db.add(recon_run)
            db.flush()

        cases_specs = [
            {
                "case_number": "CASE-2025-APEX-UNX-001",
                "scope_type": "STUDENT",
                "inst": apex_inst,
                "prog": apex_cse,
                "year": "2025-26",
                "classification": "UNEXPLAINED_APPEARANCE",
                "priority": "HIGH",
                "status": "UNDER_INQUIRY",
                "context": {"student_roll": "25CSE-UN01", "details": "Sudden candidate observation on 2025-26 roster without documented admission episode."},
            },
            {
                "case_number": "CASE-2025-DUAL-ENROL-002",
                "scope_type": "STUDENT",
                "inst": poly_inst,
                "prog": poly_cse,
                "year": "2024-25",
                "classification": "CONCURRENT_DUAL_ENROLMENT",
                "priority": "HIGH",
                "status": "OPEN",
                "context": {"apaar": "998877665501", "institutions": ["National Polytechnic", "Kaveri University"], "details": "Active concurrent roster observations detected at two institutions."},
            },
            {
                "case_number": "CASE-2024-APEX-ECE-INTAKE-003",
                "scope_type": "PROGRAMME",
                "inst": apex_inst,
                "prog": prog_map["INST-APEX-001:ECE"],
                "year": "2024-25",
                "classification": "INTAKE_LIMIT_EXCEEDED",
                "priority": "HIGH",
                "status": "RESOLVED",
                "observed": 62, "limit": 60, "excess": 2,
                "context": {"approved": 60, "observed": 62, "excess": 2},
                "decision": {
                    "action": "RESOLVE_WITH_EVIDENCE",
                    "reason": "Institutional documentation confirmed: 2 excess candidates admitted under state sports quota supernumerary order DTE/SP-2024/62.",
                }
            },
            {
                "case_number": "CASE-2024-AGG-VARIANCE-004",
                "scope_type": "PROGRAMME",
                "inst": apex_inst,
                "prog": apex_cse,
                "year": "2024-25",
                "classification": "HISTORICAL_AGGREGATE_VARIANCE",
                "priority": "MEDIUM",
                "status": "RESOLVED",
                "context": {"declared": 124, "roster": 120, "variance": -4},
                "decision": {
                    "action": "RESOLVE_WITH_EVIDENCE",
                    "reason": "Preliminary census included 4 students who subsequently withdrew before October 15 census cut-off date.",
                }
            },
        ]

        reviewer_user = user_map["reviewer@aicte.gov.in"]

        for cs in cases_specs:
            existing_case = db.execute(
                select(DiscrepancyCase).where(DiscrepancyCase.case_number == cs["case_number"])
            ).scalar_one_or_none()

            if not existing_case:
                case = DiscrepancyCase(
                    case_number=cs["case_number"],
                    scope_type=cs["scope_type"],
                    institution_id=cs["inst"].id,
                    programme_id=cs["prog"].id,
                    academic_year=cs["year"],
                    observed_count=cs.get("observed"),
                    approved_limit=cs.get("limit"),
                    excess_count=cs.get("excess"),
                    classification=cs["classification"],
                    review_priority=cs["priority"],
                    case_status=cs["status"],
                    initial_reconciliation_run_id=recon_run.id,
                    latest_reconciliation_run_id=recon_run.id,
                    evidence_context_json=cs["context"],
                )
                db.add(case)
                db.flush()

                if "decision" in cs:
                    audit_ev = SnapshotService.record_chained_audit_event(
                        db=db,
                        actor_id=reviewer_user.id,
                        action="DISCREPANCY_CASE_RESOLVED",
                        entity_type="DiscrepancyCase",
                        entity_id=case.id,
                        metadata_payload={"case_number": case.case_number, "action": cs["decision"]["action"]},
                    )

                    dec = DiscrepancyCaseDecision(
                        case_id=case.id,
                        action=cs["decision"]["action"],
                        rationale_note=cs["decision"]["reason"],
                        decided_by_user_id=reviewer_user.id,
                        audit_event_id=audit_ev.id,
                    )
                    db.add(dec)

        db.commit()
        print("[SEED] Comprehensive database initialization completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"[SEED ERROR] Database seeding failed: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
