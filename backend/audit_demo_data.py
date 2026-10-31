import sys, os
sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models import (
    Institution,
    Programme,
    ApprovalConfiguration,
    AdmissionEpisode,
    AnnualRosterObservation,
    RosterSnapshot,
    SourceSubmission,
    DiscrepancyCase,
    InstitutionStudentRecord,
    StudentIdentity,
    TransferEvent,
)

db = SessionLocal()

print("--- ALL INSTITUTIONS WITH 'APEX', 'POLY', 'KAV' ---")
for inst in db.query(Institution).filter(
    (Institution.institution_code.ilike("%APEX%"))
    | (Institution.institution_code.ilike("%POLY%"))
    | (Institution.institution_code.ilike("%KAV%"))
    | (Institution.name.ilike("%Apex%"))
    | (Institution.name.ilike("%Polytechnic%"))
    | (Institution.name.ilike("%Kaveri%"))
).all():
    print(f"ID: {inst.id} | Code: {inst.institution_code} | Name: {inst.name} | Category: {inst.category}")

print("\n--- PROGRAMMES FOR EACH OF THESE ---")
for inst in db.query(Institution).filter(
    (Institution.institution_code.in_(["INST-APEX-001", "INST-POLY-002", "INST-KAV-003", "INST-KAVERI-003"]))
).all():
    print(f"\nInstitution {inst.institution_code} ({inst.name}):")
    progs = db.query(Programme).filter_by(institution_id=inst.id).all()
    for p in progs:
        ep_count = db.query(AdmissionEpisode).filter_by(programme_id=p.id).count()
        obs_count = db.query(AnnualRosterObservation).filter_by(programme_id=p.id).count()
        snap_count = db.query(RosterSnapshot).filter_by(programme_id=p.id).count()
        sub_count = db.query(SourceSubmission).filter_by(programme_id=p.id).count()
        appr = db.query(ApprovalConfiguration).filter_by(programme_id=p.id).all()
        appr_str = ", ".join([f"{a.academic_year}: {a.approved_intake}" for a in appr])
        print(f"  [{p.programme_code}] {p.programme_name} (ID: {p.id}) -> Eps: {ep_count}, Obs: {obs_count}, Snaps: {snap_count}, Subs: {sub_count}, Appr: [{appr_str}]")

db.close()
