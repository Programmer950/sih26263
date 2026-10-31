import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.core.database import SessionLocal
from app.models import (
    Institution,
    Programme,
    ApprovalConfiguration,
    StudentIdentity,
    InstitutionStudentRecord,
    AdmissionEpisode,
    AnnualRosterObservation,
    TransferEvent,
    SourceSubmission,
    RosterSnapshot,
    DiscrepancyCase,
    DiscrepancyCaseDecision,
    AuditEvent,
    User,
)
from app.services.comparison_service import ComparisonService
from app.services.duplicate_service import DuplicateService
from sqlalchemy import func

db = SessionLocal()

print("=" * 70)
print("1. PROGRAMME COUNT & DISTINCT PROGRAMMES BY INSTITUTION")
print("=" * 70)

demo_inst_codes = ["INST-APEX-001", "INST-POLY-002", "INST-KAVERI-003"]
institutions = db.query(Institution).filter(Institution.institution_code.in_(demo_inst_codes)).all()

for inst in institutions:
    progs = db.query(Programme).filter_by(institution_id=inst.id).all()
    names = [p.programme_name for p in progs]
    codes = [p.programme_code for p in progs]
    has_dups = len(names) != len(set(names))
    print(f"\nInstitution: {inst.institution_code} - {inst.name}")
    print(f"  Total Programmes: {len(progs)}")
    print(f"  Distinct Names Count: {len(set(names))}")
    print(f"  Duplicate Program Names Exist: {has_dups}")
    print("  Curated Programmes Catalogue:")
    for p in progs:
        # Check active approval config for 2024-25
        appr_24 = db.query(ApprovalConfiguration).filter_by(
            programme_id=p.id, academic_year="2024-25", status="ACTIVE"
        ).first()
        appr_25 = db.query(ApprovalConfiguration).filter_by(
            programme_id=p.id, academic_year="2025-26", status="ACTIVE"
        ).first()
        intake_24 = appr_24.approved_intake if appr_24 else "N/A"
        intake_25 = appr_25.approved_intake if appr_25 else "N/A"
        students = db.query(InstitutionStudentRecord).filter_by(programme_id=p.id).count()
        print(f"    [{p.programme_code:10s}] {p.programme_name:48s} | Level: {p.qualification_level:7s} | Intake (24-25 / 25-26): {intake_24} / {intake_25} | Enrolled: {students}")

print("\n" + "=" * 70)
print("2. CHECK FOR DUPLICATE PROGRAMME IDENTITIES & ARCH_ RESIDUE")
print("=" * 70)
arch_count = db.query(Programme).filter(Programme.programme_code.like("ARCH_%")).count()
print(f"Total 'ARCH_%' programmes across entire database: {arch_count}")

# Check duplicate programme codes within any institution
dup_codes_query = (
    db.query(Programme.institution_id, Programme.programme_code, func.count(Programme.id))
    .group_by(Programme.institution_id, Programme.programme_code)
    .having(func.count(Programme.id) > 1)
    .all()
)
print(f"Duplicate (institution_id, programme_code) pairs: {len(dup_codes_query)}")

# Check duplicate active approval configurations
dup_apprs = (
    db.query(ApprovalConfiguration.institution_id, ApprovalConfiguration.programme_id, ApprovalConfiguration.academic_year, func.count(ApprovalConfiguration.id))
    .filter(ApprovalConfiguration.status == "ACTIVE")
    .group_by(ApprovalConfiguration.institution_id, ApprovalConfiguration.programme_id, ApprovalConfiguration.academic_year)
    .having(func.count(ApprovalConfiguration.id) > 1)
    .all()
)
print(f"Duplicate active ApprovalConfigurations: {len(dup_apprs)}")

# Check orphaned student records
orphaned_recs = db.query(InstitutionStudentRecord).filter(
    ~InstitutionStudentRecord.programme_id.in_(db.query(Programme.id))
).count()
print(f"Orphaned InstitutionStudentRecord records: {orphaned_recs}")

orphaned_eps = db.query(AdmissionEpisode).filter(
    ~AdmissionEpisode.programme_id.in_(db.query(Programme.id))
).count()
print(f"Orphaned AdmissionEpisode records: {orphaned_eps}")

orphaned_obs = db.query(AnnualRosterObservation).filter(
    ~AnnualRosterObservation.programme_id.in_(db.query(Programme.id))
).count()
print(f"Orphaned AnnualRosterObservation records: {orphaned_obs}")

print("\n" + "=" * 70)
print("3. MANDATORY APEX CSE 120-STUDENT LONGITUDINAL COHORT SCENARIO")
print("=" * 70)
apex = db.query(Institution).filter_by(institution_code="INST-APEX-001").first()
cse = db.query(Programme).filter_by(programme_code="CSE", institution_id=apex.id).first()
admin = db.query(User).filter_by(email="admin@apex.edu.in").first()

base_snap = (
    db.query(RosterSnapshot)
    .filter_by(programme_id=cse.id, academic_year="2024-25", is_authoritative=True)
    .first()
)
cand_snap = (
    db.query(RosterSnapshot)
    .filter_by(programme_id=cse.id, academic_year="2025-26", is_authoritative=True)
    .first()
)

if base_snap and cand_snap:
    res = ComparisonService.compare_snapshots(
        db, candidate_id=cand_snap.id, current_user=admin, baseline_id=base_snap.id
    )
    print("Baseline Snapshot ID:", res.baseline_snapshot_id)
    print("Candidate Snapshot ID:", res.candidate_snapshot_id)
    print("Academic Year:", res.academic_year)
    print("\nSummary Reconciliation Metrics:")
    for k, v in res.summary_metrics.items():
        print(f"  {k:28s}: {v}")
    print("\nTotal Reconciled Records:", len(res.records))
else:
    print("Apex CSE snapshots not found!", base_snap, cand_snap)

print("\n" + "=" * 70)
print("4. CROSS-INSTITUTION DUPLICATE DETECTION")
print("=" * 70)
reviewer = db.query(User).filter_by(email="reviewer@aicte.gov.in").first()
try:
    dups = DuplicateService.detect_duplicates(db, actor=reviewer, academic_year="2024-25")
    print(f"Duplicate conflicts detected for 2024-25: {len(dups)}")
    for idx, d in enumerate(dups[:5], 1):
        print(f"  [{idx}] Student: {d.full_name} | APAAR: {d.masked_apaar_reference}")
        print(f"      Conflict Type: {d.conflict_type} | Priority: {d.review_priority}")
        print(f"      Enrolments Count: {len(d.enrolments)} | Verified Transfer: {d.is_verified_transfer}")
except Exception as e:
    print("Duplicate detection call note:", e)

print("\n" + "=" * 70)
print("5. OPERATIONAL DISCREPANCY CASES")
print("=" * 70)
for case in db.query(DiscrepancyCase).all():
    print(f"  Case {case.case_number}: [{case.scope_type}] {case.classification} | Status: {case.case_status} | Priority: {case.review_priority}")

db.close()
