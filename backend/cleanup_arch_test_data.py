import sys, os
sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models import (
    Programme,
    AdmissionEpisode,
    AnnualRosterObservation,
    RosterSnapshot,
    SourceSubmission,
    SourceSubmissionRecord,
    SubmissionPreview,
    ApprovalConfiguration,
    ReconciliationRun,
    DiscrepancyCase,
)

db = SessionLocal()
arch_progs = db.query(Programme).filter(Programme.programme_code.like("ARCH_%")).all()
print(f"Found {len(arch_progs)} ARCH_% programmes to clean up.")

total_obs = 0
total_snaps = 0
total_subs = 0
total_records = 0
total_previews = 0
total_eps = 0

for p in arch_progs:
    # 1. Observations
    obs = db.query(AnnualRosterObservation).filter_by(programme_id=p.id).delete(synchronize_session=False)
    total_obs += obs

    # 2. Discrepancies if any
    db.query(DiscrepancyCase).filter(DiscrepancyCase.programme_id == p.id).delete(synchronize_session=False)

    # 3. Snapshots and Reconciliation runs
    snaps = db.query(RosterSnapshot).filter_by(programme_id=p.id).all()
    snap_ids = [s.id for s in snaps]
    if snap_ids:
        db.query(ReconciliationRun).filter(
            (ReconciliationRun.candidate_snapshot_id.in_(snap_ids))
            | (ReconciliationRun.baseline_snapshot_id.in_(snap_ids))
        ).delete(synchronize_session=False)
        for s in snaps:
            db.delete(s)
            total_snaps += 1

    # 3. Submissions
    subs = db.query(SourceSubmission).filter_by(programme_id=p.id).all()
    sub_ids = [s.id for s in subs]
    if sub_ids:
        prevs = db.query(SubmissionPreview).filter(SubmissionPreview.submission_id.in_(sub_ids)).delete(synchronize_session=False)
        total_previews += prevs
        recs = db.query(SourceSubmissionRecord).filter(SourceSubmissionRecord.submission_id.in_(sub_ids)).delete(synchronize_session=False)
        total_records += recs
        for s in subs:
            db.delete(s)
            total_subs += 1

    # 4. Episodes, Student Records, and Approvals
    eps = db.query(AdmissionEpisode).filter_by(programme_id=p.id).delete(synchronize_session=False)
    total_eps += eps
    from app.models import InstitutionStudentRecord
    db.query(InstitutionStudentRecord).filter_by(programme_id=p.id).delete(synchronize_session=False)
    db.query(ApprovalConfiguration).filter_by(programme_id=p.id).delete(synchronize_session=False)

    # 5. Programme itself
    db.delete(p)

db.commit()
print(f"Cleaned up {len(arch_progs)} ARCH_ programmes: deleted {total_obs} obs, {total_snaps} snaps, {total_subs} subs, {total_records} records, {total_previews} previews, {total_eps} eps.")

# Verify remaining programmes at Apex
from app.models import Institution
apex = db.query(Institution).filter_by(institution_code="INST-APEX-001").first()
remaining = db.query(Programme).filter_by(institution_id=apex.id).all()
print(f"Remaining programmes at Apex: {[p.programme_code for p in remaining]}")

db.close()
