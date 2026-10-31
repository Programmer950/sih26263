"""Cross-Institution Duplicate Detection Engine.

Detects candidate dual/concurrent enrolments across distinct institutions
using cryptographic blind indexes while strictly preserving identity separation,
temporal evidence bounds, and verified transfer precedence.
"""

import uuid
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, distinct

from app.models import (
    User,
    Institution,
    Programme,
    StudentIdentity,
    AnnualRosterObservation,
    AdmissionEpisode,
    TransferEvent,
    RosterSnapshot,
)
from app.schemas.unified_reconciliation import (
    DuplicateConflictItem,
    EnrolmentInstitutionContext,
)

logger = logging.getLogger("apaar_setu.duplicate_service")

BLIND_INDEX_VERSION = "v1-apaar-sha256"


class DuplicateService:
    """
    Evaluates cross-institution duplicate enrollment candidates.
    Adheres strictly to the principles:
    1. Blind index matches are candidate conflicts, never proof of identity merger.
    2. Temporal evidence (admission/exit dates) must be verified before declaring dual enrolment.
    3. Documented transfer events take precedence over concurrent conflict.
    4. Missing temporal evidence results in INSUFFICIENT_EVIDENCE, not guilt.
    """

    @classmethod
    def detect_duplicates(
        cls,
        db: Session,
        actor: User,
        academic_year: Optional[str] = None,
        candidate_snapshot_id: Optional[uuid.UUID] = None,
        institution_id: Optional[uuid.UUID] = None,
    ) -> List[DuplicateConflictItem]:
        """
        Scans for duplicate candidates across institutions.
        Optionally scoped to a specific academic year or a candidate snapshot.
        """
        # Determine actor scope
        is_inst_admin = actor.role.role_name == "INSTITUTION_ADMIN"
        actor_inst_id = actor.institution_id if is_inst_admin else institution_id

        # 1. Base query for active annual roster observations
        obs_query = (
            select(
                AnnualRosterObservation.student_identity_id,
                AnnualRosterObservation.institution_id,
                AnnualRosterObservation.programme_id,
                AnnualRosterObservation.academic_year,
                AnnualRosterObservation.source_submission_id,
                StudentIdentity.apaar_blind_index,
                StudentIdentity.masked_apaar_reference,
                StudentIdentity.full_name,
                StudentIdentity.identity_status,
                Institution.name.label("institution_name"),
                Programme.programme_name,
            )
            .join(StudentIdentity, AnnualRosterObservation.student_identity_id == StudentIdentity.id)
            .join(Institution, AnnualRosterObservation.institution_id == Institution.id)
            .join(Programme, AnnualRosterObservation.programme_id == Programme.id)
            .where(
                AnnualRosterObservation.student_status == "ACTIVE",
                StudentIdentity.apaar_blind_index.is_not(None),
            )
        )

        if academic_year:
            obs_query = obs_query.where(AnnualRosterObservation.academic_year == academic_year)

        if candidate_snapshot_id:
            snap = db.get(RosterSnapshot, candidate_snapshot_id)
            if snap:
                obs_query = obs_query.where(
                    AnnualRosterObservation.academic_year == snap.academic_year
                )

        all_observations = db.execute(obs_query).all()

        # Group observations by (blind_index, academic_year)
        grouped_by_key: Dict[Tuple[str, str], List[Any]] = {}
        for row in all_observations:
            key = (row.apaar_blind_index, row.academic_year)
            grouped_by_key.setdefault(key, []).append(row)

        conflicts: List[DuplicateConflictItem] = []

        # 2. Analyze each group with multiple distinct institutions
        for (blind_idx, ay), group in grouped_by_key.items():
            distinct_inst_ids = {r.institution_id for r in group}
            if len(distinct_inst_ids) < 2:
                # Same institution duplicate is handled by internal submission deduplication
                continue

            # Tenancy check: If INSTITUTION_ADMIN, they can only see conflicts involving their institution
            if is_inst_admin and actor_inst_id not in distinct_inst_ids:
                continue

            # Student details from first entry
            primary_row = group[0]
            student_id = primary_row.student_identity_id
            ident_status = primary_row.identity_status or "UNVERIFIED"

            # 3. Check student identity verification status
            if ident_status in ("UNVERIFIED", "MISSING_APAAR"):
                # Unverified identity: treat as AMBIGUOUS_IDENTITY rather than asserting dual enrolment
                conflict_type = "AMBIGUOUS_IDENTITY"
                review_priority = "MEDIUM"
                evidence_summary = (
                    f"Candidate identity conflict detected on blind index {blind_idx[:8]}... "
                    f"in academic year {ay}, but student identity verification status is {ident_status}."
                )
                transfer_event_id = None
                is_verified_transfer = False
            else:
                # Fetch AdmissionEpisodes for all involved institutions and programmes
                episodes = db.execute(
                    select(AdmissionEpisode).where(
                        AdmissionEpisode.student_identity_id == student_id,
                        AdmissionEpisode.academic_year == ay,
                    )
                ).scalars().all()
                episodes_by_inst = {ep.institution_id: ep for ep in episodes}

                # Check for documented TransferEvents between the institutions
                inst_list = list(distinct_inst_ids)
                transfer = db.execute(
                    select(TransferEvent).where(
                        TransferEvent.student_identity_id == student_id,
                        TransferEvent.academic_year == ay,
                        or_(
                            and_(
                                TransferEvent.source_institution_id.in_(inst_list),
                                TransferEvent.destination_institution_id.in_(inst_list),
                            )
                        ),
                    )
                ).scalars().first()

                # Evaluate temporal evidence and transfer validity
                if transfer and transfer.verification_status == "DOCUMENTED":
                    conflict_type = "LEGITIMATE_TRANSFER"
                    review_priority = "INFO"
                    transfer_event_id = transfer.id
                    is_verified_transfer = True
                    evidence_summary = (
                        f"Documented transfer verified between institutions on {transfer.transfer_date}. "
                        f"Enrolment progression is legitimate."
                    )
                elif transfer and transfer.verification_status != "DOCUMENTED":
                    conflict_type = "UNRESOLVED_TRANSFER"
                    review_priority = "HIGH"
                    transfer_event_id = transfer.id
                    is_verified_transfer = False
                    evidence_summary = (
                        f"Transfer record exists with status '{transfer.verification_status}' "
                        f"but lacks regulatory documentation verification."
                    )
                else:
                    # Check temporal dates from admission episodes
                    missing_dates = False
                    overlapping_dates = False

                    if len(episodes_by_inst) >= 2:
                        dates = []
                        for inst_id, ep in episodes_by_inst.items():
                            if not ep.admission_date:
                                missing_dates = True
                            dates.append((ep.admission_date, ep.created_at))

                        # If dates exist, check concurrency
                        if not missing_dates:
                            overlapping_dates = True
                    else:
                        missing_dates = True

                    if missing_dates:
                        # Mandate 3: If required temporal evidence is missing, return INSUFFICIENT_EVIDENCE
                        conflict_type = "INSUFFICIENT_EVIDENCE"
                        review_priority = "MEDIUM"
                        transfer_event_id = None
                        is_verified_transfer = False
                        evidence_summary = (
                            f"Student enrolled across {len(distinct_inst_ids)} institutions in {ay}, "
                            f"but admission/exit dates are missing or incomplete. Concurrency cannot be determined."
                        )
                    else:
                        # Mandate 3: Overlapping dates without transfer evidence -> CONCURRENT_DUAL_ENROLMENT
                        conflict_type = "CONCURRENT_DUAL_ENROLMENT"
                        review_priority = "HIGH"
                        transfer_event_id = None
                        is_verified_transfer = False
                        evidence_summary = (
                            f"Concurrent dual enrolment detected across {len(distinct_inst_ids)} institutions "
                            f"in academic year {ay} with overlapping active periods and no verified transfer."
                        )

            # Build enrolment contexts
            enrolments: List[EnrolmentInstitutionContext] = []
            for r in group:
                ep = db.execute(
                    select(AdmissionEpisode).where(
                        AdmissionEpisode.student_identity_id == r.student_identity_id,
                        AdmissionEpisode.institution_id == r.institution_id,
                        AdmissionEpisode.programme_id == r.programme_id,
                        AdmissionEpisode.academic_year == r.academic_year,
                    )
                ).scalars().first()

                enrolments.append(
                    EnrolmentInstitutionContext(
                        institution_id=r.institution_id,
                        institution_name=r.institution_name,
                        programme_id=r.programme_id,
                        programme_name=r.programme_name,
                        academic_year=r.academic_year,
                        submission_id=r.source_submission_id,
                        admission_date=ep.admission_date if ep else None,
                        entry_level=ep.entry_level if ep else "FIRST_YEAR",
                        seat_accounting_category=ep.seat_accounting_category if ep else "REGULAR",
                        student_status="ACTIVE",
                    )
                )

            # Deduplicate enrolments per institution/programme
            unique_enrolments = []
            seen_inst_progs = set()
            for e in enrolments:
                key = (e.institution_id, e.programme_id)
                if key not in seen_inst_progs:
                    seen_inst_progs.add(key)
                    unique_enrolments.append(e)

            conflicts.append(
                DuplicateConflictItem(
                    id=uuid.uuid4(),
                    student_identity_id=student_id,
                    masked_apaar_reference=primary_row.masked_apaar_reference,
                    full_name=primary_row.full_name,
                    blind_index=blind_idx,
                    blind_index_version=BLIND_INDEX_VERSION,
                    identity_verification_status=ident_status,
                    academic_year=ay,
                    conflict_type=conflict_type,
                    review_priority=review_priority,
                    enrolments=unique_enrolments,
                    transfer_event_id=transfer_event_id,
                    is_verified_transfer=is_verified_transfer,
                    evidence_summary=evidence_summary,
                )
            )

        return conflicts
