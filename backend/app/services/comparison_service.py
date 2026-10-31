"""Comparison Service for Deterministic Snapshot Reconciliation and Discrepancy Classification."""

import uuid
import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from fastapi import HTTPException, status

from app.models import (
    User,
    RosterSnapshot,
    AnnualRosterObservation,
    StudentIdentity,
    SourceSubmissionRecord,
    AdmissionEpisode,
    TransferEvent,
)
from app.schemas.snapshot import (
    SnapshotComparisonResponse,
    ComparisonRecordItem,
)

logger = logging.getLogger("apaar_setu.comparison")


def parse_academic_year_start(academic_year: Optional[str]) -> Optional[int]:
    """Extracts start year integer from academic year format (e.g. '2024-25' -> 2024, '2024' -> 2024)."""
    if not academic_year or not isinstance(academic_year, str):
        return None
    try:
        parts = academic_year.strip().split("-")
        val = int(parts[0].strip())
        return val if 1900 <= val <= 2200 else None
    except (ValueError, IndexError):
        return None


class ComparisonService:
    """
    Deterministic Snapshot Comparison Engine.
    Reconciles candidate snapshot records against an authoritative or specified baseline snapshot.
    Classifies student trajectories into:
      - ADDED
      - CONTINUING
      - WITHDRAWN
      - DOCUMENTED_TRANSFER
      - UNEXPLAINED_APPEARANCE
      - UNEXPLAINED_DISAPPEARANCE
      - AMBIGUOUS_IDENTITY
      - INSUFFICIENT_EVIDENCE
    Adheres strictly to the principle of explainable, non-punitive discrepancy analysis.
    """

    @classmethod
    def resolve_baseline(
        cls,
        db: Session,
        candidate: RosterSnapshot,
        baseline_id: Optional[uuid.UUID] = None,
    ) -> Optional[RosterSnapshot]:
        """
        Resolves the baseline snapshot:
        1. If explicit baseline_id provided, fetch and validate:
           - Must exist.
           - Cannot be candidate snapshot itself.
           - Must belong to same institution.
           - Must belong to same programme.
           - Academic year cannot be chronologically later than candidate academic year.
        2. Otherwise, look for current authoritative snapshot for same institution, programme, year (excluding candidate).
        3. If none, look for most recent strictly prior authoritative snapshot for same institution and programme.
        """
        if baseline_id:
            if baseline_id == candidate.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot compare a snapshot against itself as baseline.",
                )
            baseline = db.get(RosterSnapshot, baseline_id)
            if not baseline:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Specified baseline snapshot {baseline_id} not found.",
                )
            if baseline.institution_id != candidate.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cross-institution snapshot comparison is not permitted.",
                )
            if baseline.programme_id != candidate.programme_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cross-programme snapshot comparison is not permitted.",
                )

            # Chronological validation
            cand_start = parse_academic_year_start(candidate.academic_year)
            base_start = parse_academic_year_start(baseline.academic_year)
            if cand_start is not None and base_start is not None and base_start > cand_start:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Chronological Violation: Baseline academic year ({baseline.academic_year}) cannot be chronologically later than candidate academic year ({candidate.academic_year}).",
                )

            return baseline

        # Auto-resolve: look for active authoritative snapshot for same context (different snapshot id)
        same_year_auth = db.execute(
            select(RosterSnapshot).where(
                RosterSnapshot.institution_id == candidate.institution_id,
                RosterSnapshot.programme_id == candidate.programme_id,
                RosterSnapshot.academic_year == candidate.academic_year,
                RosterSnapshot.is_authoritative == True,
                RosterSnapshot.id != candidate.id,
            )
        ).scalars().first()

        if same_year_auth:
            return same_year_auth

        # Look for authoritative snapshot in prior academic years
        prior_auths = db.execute(
            select(RosterSnapshot).where(
                RosterSnapshot.institution_id == candidate.institution_id,
                RosterSnapshot.programme_id == candidate.programme_id,
                RosterSnapshot.is_authoritative == True,
                RosterSnapshot.id != candidate.id,
            )
        ).scalars().all()

        cand_start = parse_academic_year_start(candidate.academic_year)
        eligible_priors = []
        for a in prior_auths:
            a_start = parse_academic_year_start(a.academic_year)
            if cand_start is not None and a_start is not None:
                if a_start < cand_start:
                    eligible_priors.append((a_start, a))
            elif a.academic_year != candidate.academic_year:
                eligible_priors.append((0, a))

        if eligible_priors:
            eligible_priors.sort(key=lambda x: (x[0], x[1].observed_headcount or 0), reverse=True)
            return eligible_priors[0][1]

        return None

    @classmethod
    def compare_snapshots(
        cls,
        db: Session,
        candidate_id: uuid.UUID,
        current_user: User,
        baseline_id: Optional[uuid.UUID] = None,
    ) -> SnapshotComparisonResponse:
        """
        Performs full deterministic comparison between candidate snapshot and resolved baseline.
        Enforces tenant authorization and provides complete provenance for each record item.
        """
        # 1. Fetch Candidate Snapshot
        candidate = db.get(RosterSnapshot, candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate snapshot {candidate_id} not found.",
            )

        # 2. Tenancy Isolation
        if current_user.role.role_name == "INSTITUTION_ADMIN" and candidate.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Access to candidate snapshot for external institution forbidden.",
            )

        # 3. Resolve Baseline Snapshot
        baseline = cls.resolve_baseline(db=db, candidate=candidate, baseline_id=baseline_id)
        if baseline and current_user.role.role_name == "INSTITUTION_ADMIN" and baseline.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Access to baseline snapshot for external institution forbidden.",
            )

        # 4. Fetch Observations and Identities for Candidate
        candidate_rows = db.execute(
            select(AnnualRosterObservation, StudentIdentity, SourceSubmissionRecord)
            .join(StudentIdentity, AnnualRosterObservation.student_identity_id == StudentIdentity.id)
            .outerjoin(SourceSubmissionRecord, AnnualRosterObservation.source_record_id == SourceSubmissionRecord.id)
            .where(AnnualRosterObservation.source_submission_id == candidate.source_submission_id)
        ).all()

        # Map candidate by student_identity_id
        candidate_map: Dict[uuid.UUID, Tuple[AnnualRosterObservation, StudentIdentity, Optional[SourceSubmissionRecord]]] = {
            obs.student_identity_id: (obs, ident, rec)
            for obs, ident, rec in candidate_rows
        }

        # 5. Fetch Observations and Identities for Baseline
        baseline_map: Dict[uuid.UUID, Tuple[AnnualRosterObservation, StudentIdentity, Optional[SourceSubmissionRecord]]] = {}
        if baseline:
            baseline_rows = db.execute(
                select(AnnualRosterObservation, StudentIdentity, SourceSubmissionRecord)
                .join(StudentIdentity, AnnualRosterObservation.student_identity_id == StudentIdentity.id)
                .outerjoin(SourceSubmissionRecord, AnnualRosterObservation.source_record_id == SourceSubmissionRecord.id)
                .where(AnnualRosterObservation.source_submission_id == baseline.source_submission_id)
            ).all()

            baseline_map = {
                obs.student_identity_id: (obs, ident, rec)
                for obs, ident, rec in baseline_rows
            }

        # 6. Gather all involved student identity IDs
        all_student_ids = list(set(candidate_map.keys()) | set(baseline_map.keys()))

        # 7. Fetch Auxiliary Verification Records (AdmissionEpisodes and TransferEvents)
        admissions_list = []
        transfers_list = []
        if all_student_ids:
            admissions_list = db.execute(
                select(AdmissionEpisode).where(
                    AdmissionEpisode.student_identity_id.in_(all_student_ids),
                    AdmissionEpisode.institution_id == candidate.institution_id,
                    AdmissionEpisode.programme_id == candidate.programme_id,
                )
            ).scalars().all()

            transfers_list = db.execute(
                select(TransferEvent).where(
                    TransferEvent.student_identity_id.in_(all_student_ids),
                    or_(
                        TransferEvent.source_institution_id == candidate.institution_id,
                        TransferEvent.destination_institution_id == candidate.institution_id,
                    ),
                )
            ).scalars().all()

        admissions_by_student: Dict[uuid.UUID, AdmissionEpisode] = {
            adm.student_identity_id: adm for adm in admissions_list
        }
        transfers_by_student: Dict[uuid.UUID, TransferEvent] = {
            tr.student_identity_id: tr for tr in transfers_list
        }

        # 8. Deterministic Classification
        records: List[ComparisonRecordItem] = []
        counts = {
            "ADDED": 0,
            "CONTINUING": 0,
            "WITHDRAWN": 0,
            "DOCUMENTED_TRANSFER": 0,
            "UNEXPLAINED_APPEARANCE": 0,
            "UNEXPLAINED_DISAPPEARANCE": 0,
            "AMBIGUOUS_IDENTITY": 0,
            "INSUFFICIENT_EVIDENCE": 0,
        }

        # Process all candidates first (ordered deterministically by candidate row_number, full_name, and student_identity_id)
        sorted_cand_items = sorted(
            candidate_map.items(),
            key=lambda x: (x[1][2].row_number if x[1][2] else 0, x[1][1].full_name, str(x[0])),
        )

        processed_ids = set()

        for st_id, (c_obs, c_ident, c_rec) in sorted_cand_items:
            processed_ids.add(st_id)
            b_tuple = baseline_map.get(st_id)
            b_obs = b_tuple[0] if b_tuple else None
            b_rec = b_tuple[2] if b_tuple else None

            classification, explanation = cls._classify_candidate_student(
                st_id=st_id,
                ident=c_ident,
                c_obs=c_obs,
                b_obs=b_obs,
                has_baseline=(baseline is not None and len(baseline_map) > 0),
                admission=admissions_by_student.get(st_id),
                transfer=transfers_by_student.get(st_id),
                institution_id=candidate.institution_id,
            )

            counts[classification] += 1
            records.append(
                ComparisonRecordItem(
                    student_identity_id=c_ident.id,
                    internal_student_uuid=c_ident.internal_student_uuid,
                    student_name=c_ident.full_name,
                    masked_apaar=c_ident.masked_apaar_reference,
                    classification=classification,
                    explanation=explanation,
                    source_status_baseline=b_obs.student_status if b_obs else None,
                    source_status_candidate=c_obs.student_status,
                    source_row_baseline=b_rec.row_number if b_rec else None,
                    source_row_candidate=c_rec.row_number if c_rec else None,
                    provenance={
                        "candidate_observation_id": str(c_obs.id),
                        "candidate_submission_id": str(candidate.source_submission_id) if candidate.source_submission_id else None,
                        "baseline_observation_id": str(b_obs.id) if b_obs else None,
                        "baseline_submission_id": str(baseline.source_submission_id) if (baseline and b_obs) else None,
                        "identity_status": c_ident.identity_status,
                    },
                )
            )

        # Process baseline students absent from candidate (Disappearances / Transfers)
        sorted_base_items = sorted(
            baseline_map.items(),
            key=lambda x: (x[1][2].row_number if x[1][2] else 0, x[1][1].full_name, str(x[0])),
        )

        for st_id, (b_obs, b_ident, b_rec) in sorted_base_items:
            if st_id in processed_ids:
                continue

            classification, explanation = cls._classify_absent_student(
                st_id=st_id,
                ident=b_ident,
                b_obs=b_obs,
                transfer=transfers_by_student.get(st_id),
                institution_id=candidate.institution_id,
            )

            counts[classification] += 1
            records.append(
                ComparisonRecordItem(
                    student_identity_id=b_ident.id,
                    internal_student_uuid=b_ident.internal_student_uuid,
                    student_name=b_ident.full_name,
                    masked_apaar=b_ident.masked_apaar_reference,
                    classification=classification,
                    explanation=explanation,
                    source_status_baseline=b_obs.student_status,
                    source_status_candidate=None,
                    source_row_baseline=b_rec.row_number if b_rec else None,
                    source_row_candidate=None,
                    provenance={
                        "candidate_observation_id": None,
                        "candidate_submission_id": None,
                        "baseline_observation_id": str(b_obs.id),
                        "baseline_submission_id": str(baseline.source_submission_id) if baseline else None,
                        "identity_status": b_ident.identity_status,
                    },
                )
            )

        summary_metrics = {
            **counts,
            "TOTAL_CANDIDATE": len(candidate_map),
            "TOTAL_BASELINE": len(baseline_map),
            "TOTAL_RECORDS": len(records),
        }

        return SnapshotComparisonResponse(
            candidate_snapshot_id=candidate.id,
            baseline_snapshot_id=baseline.id if baseline else None,
            institution_id=candidate.institution_id,
            programme_id=candidate.programme_id,
            academic_year=candidate.academic_year,
            summary_metrics=summary_metrics,
            records=records,
        )

    @classmethod
    def _classify_candidate_student(
        cls,
        st_id: uuid.UUID,
        ident: StudentIdentity,
        c_obs: AnnualRosterObservation,
        b_obs: Optional[AnnualRosterObservation],
        has_baseline: bool,
        admission: Optional[AdmissionEpisode],
        transfer: Optional[TransferEvent],
        institution_id: uuid.UUID,
    ) -> Tuple[str, str]:
        """
        Determines the classification and explainable rationale for a candidate student.
        """
        # 1. Identity Ambiguity Check
        if ident.identity_status in ("MISSING_APAAR", "UNVERIFIED", "DISPUTED"):
            return (
                "AMBIGUOUS_IDENTITY",
                f"Student identity lacks authoritative APAAR binding (status: {ident.identity_status}). Identity cannot be confirmed longitudinally without ambiguity.",
            )

        # 2. Documented Transfer Check
        if transfer and transfer.verification_status == "DOCUMENTED":
            if transfer.destination_institution_id == institution_id:
                return (
                    "DOCUMENTED_TRANSFER",
                    f"Student enrollment verified via documented inter-institutional transfer (TransferEvent {transfer.id}).",
                )

        # 3. Present in Both Baseline and Candidate
        if b_obs is not None:
            if c_obs.student_status in ("WITHDRAWN", "DROPOUT", "INACTIVE", "DISCONTINUED"):
                return (
                    "WITHDRAWN",
                    f"Student explicitly designated as {c_obs.student_status} in candidate roster observation.",
                )
            return (
                "CONTINUING",
                "Student actively enrolled across both baseline and candidate roster snapshots.",
            )

        # 4. Present Only in Candidate
        if not has_baseline:
            if admission:
                return (
                    "ADDED",
                    f"Initial cohort enrollment confirmed via AdmissionEpisode {admission.id} ({admission.admission_category}).",
                )
            return (
                "INSUFFICIENT_EVIDENCE",
                "Baseline roster unavailable for comparative reconciliation; student has no linked admission record. Baseline establishment required.",
            )

        # Has baseline, but student is new
        if admission:
            return (
                "ADDED",
                f"New cohort enrollment verified via AdmissionEpisode {admission.id} ({admission.admission_category}).",
            )

        return (
            "UNEXPLAINED_APPEARANCE",
            "Student appears on candidate roster without prior baseline presence or recorded admission/transfer episode. Pending administrative reconciliation (not an inference of non-compliance).",
        )

    @classmethod
    def _classify_absent_student(
        cls,
        st_id: uuid.UUID,
        ident: StudentIdentity,
        b_obs: AnnualRosterObservation,
        transfer: Optional[TransferEvent],
        institution_id: uuid.UUID,
    ) -> Tuple[str, str]:
        """
        Determines the classification and explainable rationale for a baseline student absent from candidate.
        """
        if transfer and transfer.verification_status == "DOCUMENTED":
            if transfer.source_institution_id == institution_id:
                return (
                    "DOCUMENTED_TRANSFER",
                    f"Student departure accounted for by documented outbound transfer (TransferEvent {transfer.id}).",
                )

        if b_obs.student_status in ("WITHDRAWN", "DROPOUT", "GRADUATED", "COMPLETED", "INACTIVE"):
            return (
                "WITHDRAWN",
                f"Student previously marked as {b_obs.student_status} in baseline roster.",
            )

        if ident.identity_status in ("MISSING_APAAR", "UNVERIFIED", "DISPUTED"):
            return (
                "AMBIGUOUS_IDENTITY",
                f"Historical baseline student identity is ambiguous ({ident.identity_status}), precluding longitudinal confirmation.",
            )

        return (
            "UNEXPLAINED_DISAPPEARANCE",
            "Student was present in baseline snapshot but is absent from candidate roster without documented transfer or withdrawal. Institutional verification required (not an inference of non-compliance).",
        )

