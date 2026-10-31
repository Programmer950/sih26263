"""
APAAR SETU — Synthetic Demonstration CSV Pack Importer
Reads and ingests all records from APAAR_SETU_Synthetic_Demo_CSV_Pack:
  1. programme_catalog.csv -> Institutions, Programmes & Approved Intake Configurations
  2. apex_cse_baseline_2024_25.csv -> Authoritative Baseline Snapshot (120 records)
  3. apex_cse_candidate_2025_26.csv -> Candidate Snapshot (120 records)
  4. national_polytechnic_roster_2024_25.csv -> Supporting Polytechnic Snapshot (24 records)
  5. kaveri_university_roster_2025_26.csv -> Supporting Kaveri Snapshot (23 records)
  6. transfer_event_support.csv -> 3 Documented Transfer Events
  7. Deterministic Reconciliation Run & Discrepancy Case Generation
"""

import os
import sys
import csv
import uuid
import logging
from datetime import datetime, date, timezone
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from app.core.database import SessionLocal
from app.models import (
    User,
    Institution,
    Programme,
    ApprovalConfiguration,
    StudentIdentity,
    InstitutionStudentRecord,
    AnnualRosterObservation,
    RosterSnapshot,
    SourceSubmission,
    SubmissionPreview,
    TransferEvent,
    ReconciliationRun,
    DiscrepancyCase,
    AuditEvent,
)
from app.services.storage_service import StorageService
from app.services.preview_service import PreviewService
from app.services.ingestion_service import IngestionService
from app.services.reconciliation_service import ReconciliationService
from app.services.intake_service import IntakeService
from app.services.identity_service import validate_apaar_format
from app.schemas.submission import ConfirmRequest
from app.schemas.reconciliation import ReconciliationRunCreateRequest
from app.schemas.approval import IntakeReconciliationRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("apaar_setu.csv_pack_importer")

CSV_PACK_DIR = Path(__file__).resolve().parent.parent.parent / "APAAR_SETU_Synthetic_Demo_CSV_Pack"


def import_csv_pack():
    if not CSV_PACK_DIR.exists():
        raise FileNotFoundError(f"CSV pack directory not found at: {CSV_PACK_DIR}")

    db: Session = SessionLocal()
    try:
        # 0. Get sysadmin user for system actor operations
        sysadmin = db.execute(
            select(User).join(User.role).where(func.lower(User.email) == "sysadmin@aicte.gov.in")
        ).scalar_one_or_none()

        if not sysadmin:
            # Fallback to any admin user
            sysadmin = db.execute(select(User)).scalars().first()
        if not sysadmin:
            raise RuntimeError("No system user found in database to act as ingestion actor.")

        logger.info(f"Using actor: {sysadmin.name} ({sysadmin.email}) [Role: {sysadmin.role.role_name}]")

        # ======================================================================
        # STEP 1: Institutional & Programme Catalogue
        # ======================================================================
        logger.info("\n=== STEP 1: Registering Institutional & Programme Catalogue ===")
        catalog_path = CSV_PACK_DIR / "programme_catalog.csv"
        institutions_map = {}  # code -> Institution
        programmes_map = {}    # (inst_code, prog_code) -> Programme

        # Institution metadata definitions
        inst_meta = {
            "APEX": {
                "name": "Apex Institute of Technology",
                "category": "ENGINEERING",
                "state": "Maharashtra",
                "district": "Pune",
                "pincode": "411001",
                "email": "registrar@apextech.ac.in",
            },
            "NPOLY": {
                "name": "National Polytechnic",
                "category": "POLYTECHNIC",
                "state": "Karnataka",
                "district": "Bengaluru",
                "pincode": "560001",
                "email": "admin@natpoly.edu.in",
            },
            "KAV": {
                "name": "Kaveri University",
                "category": "UNIVERSITY",
                "state": "Tamil Nadu",
                "district": "Chennai",
                "pincode": "600001",
                "email": "dean.admissions@kaveri.edu.in",
            },
        }

        with open(catalog_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            catalog_rows = list(reader)

        for row in catalog_rows:
            inst_code = row["institution_code"].strip().upper()
            inst_name = row["institution_name"].strip()
            prog_code = row["programme_code"].strip().upper()
            prog_name = row["programme_name"].strip()
            prog_level = row["programme_level"].strip().upper()
            intake = int(row["approved_intake_demo_only"].strip())

            # 1a. Ensure Institution exists
            if inst_code not in institutions_map:
                inst = db.execute(
                    select(Institution).where(func.upper(Institution.institution_code) == inst_code)
                ).scalar_one_or_none()

                if not inst:
                    meta = inst_meta.get(inst_code, {
                        "name": inst_name,
                        "category": "ENGINEERING",
                        "state": "Maharashtra",
                        "district": "Pune",
                        "pincode": "400001",
                        "email": f"contact@{inst_code.lower()}.ac.in",
                    })
                    inst = Institution(
                        id=uuid.uuid4(),
                        institution_code=inst_code,
                        name=meta["name"],
                        category=meta["category"],
                        approval_status="APPROVED",
                        state=meta["state"],
                        district=meta["district"],
                        pincode=meta["pincode"],
                        address=f"Campus Road, {meta['district']}, {meta['state']}",
                        contact_email=meta["email"],
                    )
                    db.add(inst)
                    db.flush()
                    logger.info(f"Registered Institution: {inst.name} ({inst.institution_code})")
                institutions_map[inst_code] = inst

            inst = institutions_map[inst_code]

            # 1b. Ensure Programme exists
            prog = db.execute(
                select(Programme).where(
                    Programme.institution_id == inst.id,
                    func.upper(Programme.programme_code) == prog_code,
                )
            ).scalar_one_or_none()

            if not prog:
                duration = 3 if prog_level == "DIPLOMA" else (2 if prog_level == "PG" else 4)
                prog = Programme(
                    id=uuid.uuid4(),
                    institution_id=inst.id,
                    programme_code=prog_code,
                    programme_name=prog_name,
                    qualification_level=prog_level,
                    duration_years=duration,
                    status="ACTIVE",
                )
                db.add(prog)
                db.flush()
                logger.info(f"  - Added Programme: {prog.programme_name} ({prog.programme_code})")
            programmes_map[(inst_code, prog_code)] = prog

            # 1c. Add Approved Intake Configurations (2024-25 and 2025-26)
            for year in ["2024-25", "2025-26"]:
                cfg = db.execute(
                    select(ApprovalConfiguration).where(
                        ApprovalConfiguration.programme_id == prog.id,
                        ApprovalConfiguration.academic_year == year,
                        ApprovalConfiguration.status == "ACTIVE",
                    )
                ).scalar_one_or_none()

                if not cfg:
                    start_year = int(year.split("-")[0])
                    cfg = ApprovalConfiguration(
                        id=uuid.uuid4(),
                        institution_id=inst.id,
                        programme_id=prog.id,
                        academic_year=year,
                        approved_intake=intake,
                        supernumerary_quota_percentage=15.00,
                        lateral_entry_quota_percentage=10.00,
                        approval_reference=f"AICTE-{year}-{inst_code}-{prog_code}",
                        effective_from=date(start_year, 6, 1),
                        effective_to=date(start_year + 1, 5, 31),
                        configuration_version=1,
                        status="ACTIVE",
                    )
                    db.add(cfg)
                    db.flush()
                    logger.info(f"    * Approved Intake for {year}: {intake} seats ({cfg.approval_reference})")

        # 1d. Link institutional admin user accounts
        user_inst_links = [
            ("admin@apex.edu.in", "APEX"),
            ("admin@polytechnic.edu.in", "NPOLY"),
            ("admin@kaveri.edu.in", "KAV"),
        ]
        for user_email, inst_code in user_inst_links:
            u = db.execute(select(User).where(func.lower(User.email) == user_email.lower())).scalar_one_or_none()
            if u and inst_code in institutions_map:
                u.institution_id = institutions_map[inst_code].id
                db.flush()
                logger.info(f"Linked user {u.email} to {institutions_map[inst_code].name}")

        db.commit()

        # ======================================================================
        # STEP 2: Ingest Student Rosters via Core Pipeline
        # ======================================================================
        logger.info("\n=== STEP 2: Ingesting Annual Student Rosters ===")

        roster_files = [
            {
                "file": "apex_cse_baseline_2024_25.csv",
                "inst_code": "APEX",
                "prog_code": "APEX-CSE",
                "year": "2024-25",
                "type": "ANNUAL_ROSTER",
                "label": "Apex CSE Baseline 2024-25",
            },
            {
                "file": "apex_cse_candidate_2025_26.csv",
                "inst_code": "APEX",
                "prog_code": "APEX-CSE",
                "year": "2025-26",
                "type": "ANNUAL_ROSTER",
                "label": "Apex CSE Candidate 2025-26",
            },
            {
                "file": "national_polytechnic_roster_2024_25.csv",
                "inst_code": "NPOLY",
                "prog_code": "NPOLY-DIP-CSE",
                "year": "2024-25",
                "type": "ANNUAL_ROSTER",
                "label": "National Polytechnic Diploma CSE 2024-25",
            },
            {
                "file": "kaveri_university_roster_2025_26.csv",
                "inst_code": "KAV",
                "prog_code": "KAV-CSE",
                "year": "2025-26",
                "type": "ANNUAL_ROSTER",
                "label": "Kaveri University CSE 2025-26",
            },
        ]

        snapshots_map = {}  # (inst_code, prog_code, year) -> RosterSnapshot

        for rinfo in roster_files:
            file_path = CSV_PACK_DIR / rinfo["file"]
            inst = institutions_map[rinfo["inst_code"]]
            prog = programmes_map[(rinfo["inst_code"], rinfo["prog_code"])]
            year = rinfo["year"]
            sub_type = rinfo["type"]

            logger.info(f"\nProcessing {rinfo['label']} ({rinfo['file']})...")

            # 2a. Stream save upload to storage
            with open(file_path, "rb") as f:
                storage_key, file_fingerprint, file_size, detected_mime = StorageService.save_upload_stream(
                    stream=f,
                    original_filename=rinfo["file"],
                )

            # 2b. Create SourceSubmission record
            submission = SourceSubmission(
                id=uuid.uuid4(),
                institution_id=inst.id,
                programme_id=prog.id,
                academic_year=year,
                submission_type=sub_type,
                original_filename=rinfo["file"],
                storage_key=storage_key,
                file_fingerprint=file_fingerprint,
                file_size_bytes=file_size,
                mime_type=detected_mime,
                submission_status="UPLOADED",
                uploaded_by_user_id=sysadmin.id,
            )
            db.add(submission)
            db.commit()
            db.refresh(submission)

            # 2c. Generate Full Preview with authoritative mapping
            column_mapping = {
                "student_id": "roll_number",
                "full_name": "student_name",
                "apaar_id": "apaar_id",
                "student_status": "enrolment_status",
            }
            preview, _ = PreviewService.generate_full_preview(
                db=db,
                submission=submission,
                column_mapping=column_mapping,
            )

            # 2d. Confirm & Ingest into Canonical Student Repository & Authoritative Snapshot
            confirm_req = ConfirmRequest(
                preview_id=preview.id,
                column_mapping=column_mapping,
                completeness_status="COMPLETE",
                mark_as_authoritative=True,
            )
            confirm_res = IngestionService.confirm_and_ingest(
                db=db,
                submission_id=submission.id,
                current_user=sysadmin,
                confirm_req=confirm_req,
            )

            # Fetch the generated authoritative snapshot
            snapshot = db.execute(
                select(RosterSnapshot).where(
                    RosterSnapshot.source_submission_id == submission.id
                )
            ).scalar_one()

            snapshots_map[(rinfo["inst_code"], rinfo["prog_code"], year)] = snapshot
            logger.info(
                f"[SUCCESS] Ingested {confirm_res.total_records_processed} rows -> Snapshot ID: {snapshot.id} "
                f"(Observed: {snapshot.observed_headcount}, Authoritative: {snapshot.is_authoritative})"
            )

        # ======================================================================
        # STEP 3: Create Documented Transfer Events
        # ======================================================================
        logger.info("\n=== STEP 3: Recording Documented Transfer Events ===")
        transfer_csv_path = CSV_PACK_DIR / "transfer_event_support.csv"

        with open(transfer_csv_path, "r", encoding="utf-8-sig") as f:
            t_reader = csv.DictReader(f)
            t_rows = list(t_reader)

        for trow in t_rows:
            ref = trow["event_reference"].strip()
            apaar_id = trow["apaar_id"].strip()
            src_inst_code = trow["source_institution_code"].strip().upper()
            dst_inst_code = trow["destination_institution_code"].strip().upper()
            eff_date = datetime.strptime(trow["effective_date"].strip(), "%Y-%m-%d").date()
            ev_status = trow["evidence_status"].strip().upper()

            # Find student identity by blind index
            _, _, _, blind_idx = validate_apaar_format(apaar_id)
            student_ident = db.execute(
                select(StudentIdentity).where(StudentIdentity.apaar_blind_index == blind_idx)
            ).scalar_one_or_none()

            if not student_ident:
                logger.warning(f"Could not find StudentIdentity for APAAR ID {apaar_id}")
                continue

            src_inst = institutions_map[src_inst_code]
            dst_inst = institutions_map[dst_inst_code]

            # Source and destination programmes
            src_prog_code = "NPOLY-DIP-CSE" if src_inst_code == "NPOLY" else "APEX-CSE"
            dst_prog_code = "APEX-CSE" if dst_inst_code == "APEX" else "KAV-CSE"

            src_prog = programmes_map[(src_inst_code, src_prog_code)]
            dst_prog = programmes_map[(dst_inst_code, dst_prog_code)]

            existing_te = db.execute(
                select(TransferEvent).where(
                    TransferEvent.student_identity_id == student_ident.id,
                    TransferEvent.source_institution_id == src_inst.id,
                    TransferEvent.destination_institution_id == dst_inst.id,
                )
            ).scalar_one_or_none()

            if not existing_te:
                te = TransferEvent(
                    id=uuid.uuid4(),
                    student_identity_id=student_ident.id,
                    source_institution_id=src_inst.id,
                    destination_institution_id=dst_inst.id,
                    source_programme_id=src_prog.id,
                    destination_programme_id=dst_prog.id,
                    academic_year="2025-26",
                    transfer_date=eff_date,
                    verification_status=ev_status,
                )
                db.add(te)
                db.flush()
                logger.info(
                    f"[TRANSFER] {ref}: Student '{student_ident.full_name}' "
                    f"transferred from {src_inst_code} ({src_prog_code}) to {dst_inst_code} ({dst_prog_code}) on {eff_date}"
                )

        db.commit()

        # ======================================================================
        # STEP 4: Run Reconciliation between Apex Baseline & Candidate
        # ======================================================================
        logger.info("\n=== STEP 4: Executing Deterministic Reconciliation Run ===")
        baseline_snap = snapshots_map[("APEX", "APEX-CSE", "2024-25")]
        candidate_snap = snapshots_map[("APEX", "APEX-CSE", "2025-26")]

        rec_req = ReconciliationRunCreateRequest(
            candidate_snapshot_id=candidate_snap.id,
            baseline_snapshot_id=baseline_snap.id,
            comparison_mode="EXPLAINABLE_DISCREPANCY_ANALYSIS",
            notes="Formal SIH Demonstration Comparative Reconciliation between 2024-25 Baseline and 2025-26 Candidate.",
        )
        rec_run = ReconciliationService.execute_run(
            db=db,
            req=rec_req,
            actor=sysadmin,
        )

        logger.info(f"[SUCCESS] Reconciliation Run ID: {rec_run.id}")
        logger.info(f"  - Summary Counts: {rec_run.summary_counts}")

        # Verify Discrepancy Cases generated
        cases = db.execute(
            select(DiscrepancyCase).where(DiscrepancyCase.latest_reconciliation_run_id == rec_run.id)
        ).scalars().all()

        logger.info(f"\nGenerated Discrepancy Cases ({len(cases)}):")
        for c in cases:
            ident = db.get(StudentIdentity, c.student_identity_id) if c.student_identity_id else None
            student_label = ident.full_name if ident else "N/A"
            logger.info(f"  * Case #{c.case_number} [{c.review_priority}]: {student_label} — {c.classification}")

        # ======================================================================
        # STEP 5: Run Statutory Intake Verification
        # ======================================================================
        logger.info("\n=== STEP 5: Executing Statutory Intake Reconciliation ===")
        for year, snap in [("2024-25", baseline_snap), ("2025-26", candidate_snap)]:
            intake_res = IntakeService.verify_intake_for_snapshot(
                db=db,
                req=IntakeReconciliationRequest(candidate_snapshot_id=snap.id),
                actor=sysadmin,
            )
            logger.info(
                f"  - Apex CSE {year}: Approved Intake = {intake_res.regular_approved_intake}, "
                f"Active Enrolment = {intake_res.regular_enrolled_count}, "
                f"Compliance = {intake_res.compliance_status}"
            )

        db.commit()
        logger.info("\n[COMPLETED] Synthetic Demo CSV Pack successfully ingested into APAAR SETU!")

    except Exception as e:
        db.rollback()
        logger.error(f"[ERROR] Import failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import_csv_pack()
