import sys, os
sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models import Institution, Programme, ApprovalConfiguration, AdmissionEpisode, AnnualRosterObservation, RosterSnapshot

db = SessionLocal()
print("=== DEMO INSTITUTIONS & PROGRAMMES ===")
demo_codes = ["INST-APEX-001", "INST-POLY-002", "INST-KAV-003"]
for code in demo_codes:
    inst = db.query(Institution).filter_by(institution_code=code).first()
    if not inst:
        print(f"Institution {code} not found!")
        continue
    progs = db.query(Programme).filter_by(institution_id=inst.id).all()
    print(f"\nInstitution: {inst.institution_code} - {inst.name} (ID: {inst.id}) -> Total Programmes: {len(progs)}")
    for p in progs:
        approvals = db.query(ApprovalConfiguration).filter_by(programme_id=p.id).all()
        obs_count = db.query(AnnualRosterObservation).filter_by(programme_id=p.id).count()
        ep_count = db.query(AdmissionEpisode).filter_by(programme_id=p.id).count()
        snap_count = db.query(RosterSnapshot).filter_by(programme_id=p.id).count()
        appr_info = [(a.academic_year, a.approved_intake) for a in approvals]
        print(f"  Prog: {p.programme_code} | {p.programme_name} | Approvals: {appr_info} | Obs: {obs_count} | Ep: {ep_count} | Snaps: {snap_count}")

# Check any programmes with ARCH_
arch_progs = db.query(Programme).filter(Programme.programme_code.like("ARCH_%")).all()
print(f"\nTotal programmes with 'ARCH_%': {len(arch_progs)}")
for p in arch_progs[:5]:
    inst = db.get(Institution, p.institution_id)
    print(f"  {p.programme_code} at {inst.institution_code if inst else 'None'}: {p.programme_name}")

db.close()

