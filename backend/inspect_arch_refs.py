import sys, os
sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models import (
    Programme,
    AdmissionEpisode,
    AnnualRosterObservation,
    RosterSnapshot,
    SourceSubmission,
    DiscrepancyCase,
    ApprovalConfiguration,
)

db = SessionLocal()
arch_progs = db.query(Programme).filter(Programme.programme_code.like("ARCH_%")).all()
print(f"Total ARCH_ programmes: {len(arch_progs)}")

for p in arch_progs:
    eps = db.query(AdmissionEpisode).filter_by(programme_id=p.id).count()
    obs = db.query(AnnualRosterObservation).filter_by(programme_id=p.id).count()
    snaps = db.query(RosterSnapshot).filter_by(programme_id=p.id).count()
    subs = db.query(SourceSubmission).filter_by(programme_id=p.id).count()
    cases = db.query(DiscrepancyCase).filter_by(programme_id=p.id).count()
    apprs = db.query(ApprovalConfiguration).filter_by(programme_id=p.id).count()
    print(f"{p.programme_code}: eps={eps}, obs={obs}, snaps={snaps}, subs={subs}, cases={cases}, apprs={apprs}")

db.close()

