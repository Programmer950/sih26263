"""
Script to register an Institution and its Academic Programmes with Approved Intake in APAAR SETU.
Can be used via CLI flags or interactively.
"""

import sys
import os
import argparse
import uuid
from pathlib import Path
from datetime import date

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.database import SessionLocal
from app.models import Institution, Programme, ApprovalConfiguration


def register_institution(
    institution_code: str,
    name: str,
    category: str,
    state: str,
    district: str,
    pincode: str = None,
    contact_email: str = None,
    programmes_data: list = None,
):
    """
    Registers an institution and optional programmes.
    programmes_data: list of dicts with:
      code, name, level (UG/PG/DIPLOMA), duration (int), intake (int), academic_year (str)
    """
    db: Session = SessionLocal()
    try:
        code_clean = institution_code.strip().upper()
        existing = db.execute(
            select(Institution).where(func.upper(Institution.institution_code) == code_clean)
        ).scalar_one_or_none()

        if existing:
            inst = existing
            print(f"[INFO] Institution '{code_clean}' already exists (ID: {inst.id}). Using existing record.")
        else:
            inst = Institution(
                id=uuid.uuid4(),
                institution_code=code_clean,
                name=name.strip(),
                category=category.strip().upper(),
                approval_status="APPROVED",
                state=state.strip(),
                district=district.strip(),
                pincode=pincode.strip() if pincode else "400001",
                address=f"Campus Road, {district}, {state}",
                contact_email=contact_email.strip() if contact_email else f"contact@{code_clean.lower()}.ac.in",
            )
            db.add(inst)
            db.commit()
            db.refresh(inst)
            print(f"[SUCCESS] Registered Institution: {inst.name} ({inst.institution_code}) [ID: {inst.id}]")

        # Now add programmes if provided
        if programmes_data:
            for pdata in programmes_data:
                p_code = pdata["code"].strip().upper()
                p_name = pdata["name"].strip()
                p_level = pdata.get("level", "UG").strip().upper()
                p_duration = int(pdata.get("duration", 4))
                p_intake = int(pdata.get("intake", 120)) if pdata.get("intake") else None
                p_year = pdata.get("academic_year", "2024-25")

                existing_p = db.execute(
                    select(Programme).where(
                        Programme.institution_id == inst.id,
                        func.upper(Programme.programme_code) == p_code,
                    )
                ).scalar_one_or_none()

                if existing_p:
                    prog = existing_p
                    print(f"  - Programme '{p_code}' already exists (ID: {prog.id})")
                else:
                    prog = Programme(
                        id=uuid.uuid4(),
                        institution_id=inst.id,
                        programme_code=p_code,
                        programme_name=p_name,
                        qualification_level=p_level,
                        duration_years=p_duration,
                        status="ACTIVE",
                    )
                    db.add(prog)
                    db.commit()
                    db.refresh(prog)
                    print(f"  [SUCCESS] Added Programme: {prog.programme_name} ({prog.programme_code})")

                # Add approval config if intake specified
                if p_intake:
                    existing_cfg = db.execute(
                        select(ApprovalConfiguration).where(
                            ApprovalConfiguration.programme_id == prog.id,
                            ApprovalConfiguration.academic_year == p_year,
                            ApprovalConfiguration.status == "ACTIVE",
                        )
                    ).scalar_one_or_none()

                    if not existing_cfg:
                        cfg = ApprovalConfiguration(
                            id=uuid.uuid4(),
                            institution_id=inst.id,
                            programme_id=prog.id,
                            academic_year=p_year,
                            approved_intake=p_intake,
                            supernumerary_quota_percentage=15.00,
                            lateral_entry_quota_percentage=10.00,
                            approval_reference=f"AICTE-{p_year}-{code_clean}-{p_code}",
                            effective_from=date(int(p_year.split("-")[0]), 6, 1),
                            effective_to=date(int(p_year.split("-")[0]) + 1, 5, 31),
                            configuration_version=1,
                            status="ACTIVE",
                        )
                        db.add(cfg)
                        db.commit()
                        print(f"    [SUCCESS] Approved Intake for {p_year}: {p_intake} seats (Ref: {cfg.approval_reference})")
                    else:
                        print(f"    - Approved Intake already set for {p_year}: {existing_cfg.approved_intake} seats")

        print("\nAll done! You can now select this institution and programme in the Data Submissions page.")
        return inst
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to register institution: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Register an institution and academic programmes in APAAR SETU.")
    parser.add_argument("--code", type=str, help="Institution code (e.g. AIT)")
    parser.add_argument("--name", type=str, help="Full Institution Name (e.g. Apex Institute of Technology)")
    parser.add_argument("--category", type=str, default="ENGINEERING", help="Category (ENGINEERING, POLYTECHNIC, UNIVERSITY, etc.)")
    parser.add_argument("--state", type=str, default="Maharashtra", help="State (e.g. Maharashtra)")
    parser.add_argument("--district", type=str, default="Pune", help="District (e.g. Pune)")
    parser.add_argument("--pincode", type=str, default="411001", help="Pincode")
    parser.add_argument("--email", type=str, help="Contact Email")
    parser.add_argument(
        "--programmes",
        type=str,
        help="Comma-separated programmes in format: CODE:NAME:LEVEL:DURATION:INTAKE:ACADEMIC_YEAR (e.g. 'CSE:Computer Science and Engineering:UG:4:120:2024-25,IT:Information Technology:UG:4:60:2024-25')",
    )

    parser.add_argument(
        "--demo-catalogue",
        action="store_true",
        help="Instantly registers the 3 standard curated demonstration institutions (AIT, NP, KU) with realistic programmes and statutory intake capacities.",
    )

    args = parser.parse_args()

    if args.demo_catalogue:
        print("Registering standard curated demo catalogue (Apex Institute of Technology, National Polytechnic, Kaveri University)...")
        demo_institutions = [
            {
                "code": "AIT",
                "name": "Apex Institute of Technology",
                "category": "ENGINEERING",
                "state": "Maharashtra",
                "district": "Pune",
                "pincode": "411001",
                "email": "registrar@apextech.ac.in",
                "programmes": [
                    {"code": "CSE", "name": "B.Tech Computer Science and Engineering", "level": "UG", "duration": 4, "intake": 180, "academic_year": "2024-25"},
                    {"code": "IT", "name": "B.Tech Information Technology", "level": "UG", "duration": 4, "intake": 120, "academic_year": "2024-25"},
                    {"code": "ECE", "name": "B.Tech Electronics and Communication Engineering", "level": "UG", "duration": 4, "intake": 120, "academic_year": "2024-25"},
                    {"code": "EEE", "name": "B.Tech Electrical and Electronics Engineering", "level": "UG", "duration": 4, "intake": 60, "academic_year": "2024-25"},
                    {"code": "ME", "name": "B.Tech Mechanical Engineering", "level": "UG", "duration": 4, "intake": 120, "academic_year": "2024-25"},
                    {"code": "BARCH", "name": "B.Arch Architecture", "level": "UG", "duration": 5, "intake": 80, "academic_year": "2024-25"},
                    {"code": "MBA", "name": "Master of Business Administration", "level": "PG", "duration": 2, "intake": 60, "academic_year": "2024-25"},
                ],
            },
            {
                "code": "NP",
                "name": "National Polytechnic",
                "category": "POLYTECHNIC",
                "state": "Karnataka",
                "district": "Bengaluru",
                "pincode": "560001",
                "email": "admin@natpoly.edu.in",
                "programmes": [
                    {"code": "DIP-CSE", "name": "Diploma in Computer Engineering", "level": "DIPLOMA", "duration": 3, "intake": 120, "academic_year": "2024-25"},
                    {"code": "DIP-ME", "name": "Diploma in Mechanical Engineering", "level": "DIPLOMA", "duration": 3, "intake": 90, "academic_year": "2024-25"},
                    {"code": "DIP-CE", "name": "Diploma in Civil Engineering", "level": "DIPLOMA", "duration": 3, "intake": 60, "academic_year": "2024-25"},
                    {"code": "DIP-EC", "name": "Diploma in Electronics Engineering", "level": "DIPLOMA", "duration": 3, "intake": 60, "academic_year": "2024-25"},
                ],
            },
            {
                "code": "KU",
                "name": "Kaveri University",
                "category": "UNIVERSITY",
                "state": "Tamil Nadu",
                "district": "Chennai",
                "pincode": "600001",
                "email": "dean.admissions@kaveri.edu.in",
                "programmes": [
                    {"code": "CSE", "name": "B.Tech Computer Science and Engineering", "level": "UG", "duration": 4, "intake": 240, "academic_year": "2024-25"},
                    {"code": "AIDS", "name": "B.Tech Artificial Intelligence and Data Science", "level": "UG", "duration": 4, "intake": 120, "academic_year": "2024-25"},
                    {"code": "BBA", "name": "Bachelor of Business Administration", "level": "UG", "duration": 3, "intake": 120, "academic_year": "2024-25"},
                    {"code": "MBA", "name": "Master of Business Administration", "level": "PG", "duration": 2, "intake": 120, "academic_year": "2024-25"},
                    {"code": "BSC-CS", "name": "B.Sc Computer Science", "level": "UG", "duration": 3, "intake": 60, "academic_year": "2024-25"},
                ],
            },
        ]

        for item in demo_institutions:
            print(f"\n--- Registering {item['name']} ({item['code']}) ---")
            register_institution(
                institution_code=item["code"],
                name=item["name"],
                category=item["category"],
                state=item["state"],
                district=item["district"],
                pincode=item["pincode"],
                contact_email=item["email"],
                programmes_data=item["programmes"],
            )
        print("\n[SUCCESS] All curated demo institutions and programmes registered successfully!")
        return

    if not args.code or not args.name:
        print("=" * 60)
        print(" APAAR SETU — Quick Institution & Programme Registration")
        print("=" * 60)
        print("Usage example:")
        print("  python backend/scripts/register_institution.py \\")
        print("    --code AIT \\")
        print("    --name \"Apex Institute of Technology\" \\")
        print("    --category ENGINEERING \\")
        print("    --state Maharashtra \\")
        print("    --district Pune \\")
        print("    --programmes \"CSE:B.Tech Computer Science and Engineering:UG:4:120:2024-25,IT:B.Tech Information Technology:UG:4:60:2024-25\"\n")
        sys.exit(1)

    progs = []
    if args.programmes:
        for item in args.programmes.split(","):
            parts = item.strip().split(":")
            if len(parts) >= 2:
                p_dict = {
                    "code": parts[0].strip(),
                    "name": parts[1].strip(),
                    "level": parts[2].strip() if len(parts) > 2 else "UG",
                    "duration": int(parts[3].strip()) if len(parts) > 3 else 4,
                    "intake": int(parts[4].strip()) if len(parts) > 4 else 120,
                    "academic_year": parts[5].strip() if len(parts) > 5 else "2024-25",
                }
                progs.append(p_dict)

    register_institution(
        institution_code=args.code,
        name=args.name,
        category=args.category,
        state=args.state,
        district=args.district,
        pincode=args.pincode,
        contact_email=args.email,
        programmes_data=progs,
    )


if __name__ == "__main__":
    main()
