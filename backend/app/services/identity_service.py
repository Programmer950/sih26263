"""Student Identity & Longitudinal Trajectory Service."""

import re
import uuid
from datetime import date, datetime, timezone
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.core.security import (
    compute_blind_index,
    encrypt_sensitive_field,
    decrypt_sensitive_field,
)
from app.models import (
    StudentIdentity,
    InstitutionStudentRecord,
    AdmissionEpisode,
    AnnualRosterObservation,
    TransferEvent,
    Programme,
    Institution,
)

APAAR_NUMERIC_REGEX = re.compile(r"^\d{12}$")


def validate_apaar_format(raw_apaar: Optional[str]) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """
    Validates documented APAAR format (12-digit numeric).
    Strict Rule: Documented format validation ONLY. No invented checksum algorithms.
    
    Returns: (identity_status, normalized_12_digits, masked_reference, blind_index)
    """
    if not raw_apaar or not raw_apaar.strip():
        return "MISSING_APAAR", None, None, None

    sanitized = raw_apaar.strip().replace("-", "").replace(" ", "")

    if not APAAR_NUMERIC_REGEX.match(sanitized):
        return "INVALID_FORMAT", sanitized, f"INVALID-{sanitized[:4]}...", None

    masked = f"XXXX-XXXX-{sanitized[-4:]}"
    blind_idx = compute_blind_index(sanitized)
    return "FORMAT_VALID", sanitized, masked, blind_idx


class IdentityService:
    @staticmethod
    def register_student(
        db: Session,
        institution_id: uuid.UUID,
        programme_id: uuid.UUID,
        institution_student_id: str,
        full_name: str,
        academic_year: str,
        admission_date: date,
        raw_apaar: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        gender: Optional[str] = None,
        admission_category: str = "REGULAR",
        supernumerary_status: bool = False,
        nri_status: bool = False,
        source_submission_id: Optional[uuid.UUID] = None,
    ) -> Tuple[StudentIdentity, InstitutionStudentRecord, AdmissionEpisode]:
        """
        Creates or links a global StudentIdentity, associates with an InstitutionStudentRecord,
        creates an AdmissionEpisode, and records an initial AnnualRosterObservation.
        """
        status_val, clean_apaar, masked_apaar, blind_idx = validate_apaar_format(raw_apaar)

        # 1. Resolve or Create StudentIdentity
        identity = None
        if blind_idx:
            identity = db.execute(
                select(StudentIdentity).where(StudentIdentity.apaar_blind_index == blind_idx)
            ).scalar_one_or_none()

        if identity is None:
            encrypted_ref = encrypt_sensitive_field(clean_apaar) if clean_apaar and status_val == "FORMAT_VALID" else None
            identity = StudentIdentity(
                internal_student_uuid=uuid.uuid4(),
                encrypted_apaar_reference=encrypted_ref,
                masked_apaar_reference=masked_apaar,
                apaar_blind_index=blind_idx,
                full_name=full_name.strip(),
                date_of_birth=date_of_birth,
                gender=gender,
                identity_status=status_val,
            )
            db.add(identity)
            db.flush()

        # 2. InstitutionStudentRecord (Roll Number / Reg No)
        inst_record = db.execute(
            select(InstitutionStudentRecord).where(
                InstitutionStudentRecord.institution_id == institution_id,
                InstitutionStudentRecord.institution_student_id == institution_student_id.strip(),
            )
        ).scalar_one_or_none()

        if inst_record is None:
            inst_record = InstitutionStudentRecord(
                student_identity_id=identity.id,
                institution_id=institution_id,
                institution_student_id=institution_student_id.strip(),
                programme_id=programme_id,
                status="ENROLLED",
            )
            db.add(inst_record)
            db.flush()

        # 3. Discrete AdmissionEpisode
        episode = AdmissionEpisode(
            student_identity_id=identity.id,
            institution_id=institution_id,
            programme_id=programme_id,
            academic_year=academic_year,
            admission_date=admission_date,
            admission_category=admission_category,
            supernumerary_status=supernumerary_status,
            nri_status=nri_status,
            source_submission_id=source_submission_id,
        )
        db.add(episode)
        db.flush()

        # 4. AnnualRosterObservation
        obs = AnnualRosterObservation(
            student_identity_id=identity.id,
            institution_id=institution_id,
            programme_id=programme_id,
            academic_year=academic_year,
            student_status="ACTIVE",
            source_submission_id=source_submission_id,
            observation_metadata={
                "intake_type": admission_category,
                "recorded_roll_no": institution_student_id.strip(),
            },
        )
        db.add(obs)
        db.flush()

        return identity, inst_record, episode

    @staticmethod
    def get_student_timeline(db: Session, student_identity_id: uuid.UUID) -> Dict[str, Any]:
        """
        Reconstructs the longitudinal academic trajectory for an individual student.
        """
        identity = db.execute(
            select(StudentIdentity).where(StudentIdentity.id == student_identity_id)
        ).scalar_one_or_none()

        if not identity:
            return None

        # Institution Records
        inst_records = db.execute(
            select(InstitutionStudentRecord, Institution, Programme)
            .join(Institution, InstitutionStudentRecord.institution_id == Institution.id)
            .join(Programme, InstitutionStudentRecord.programme_id == Programme.id)
            .where(InstitutionStudentRecord.student_identity_id == identity.id)
        ).all()

        # Admission Episodes
        admissions = db.execute(
            select(AdmissionEpisode, Institution, Programme)
            .join(Institution, AdmissionEpisode.institution_id == Institution.id)
            .join(Programme, AdmissionEpisode.programme_id == Programme.id)
            .where(AdmissionEpisode.student_identity_id == identity.id)
            .order_by(AdmissionEpisode.admission_date.asc())
        ).all()

        # Annual Roster Observations
        observations = db.execute(
            select(AnnualRosterObservation, Institution, Programme)
            .join(Institution, AnnualRosterObservation.institution_id == Institution.id)
            .join(Programme, AnnualRosterObservation.programme_id == Programme.id)
            .where(AnnualRosterObservation.student_identity_id == identity.id)
            .order_by(AnnualRosterObservation.academic_year.asc(), AnnualRosterObservation.observation_timestamp.asc())
        ).all()

        # Transfers
        transfers = db.execute(
            select(TransferEvent)
            .where(TransferEvent.student_identity_id == identity.id)
            .order_by(TransferEvent.transfer_date.asc())
        ).scalars().all()

        events = []
        for adm, inst, prog in admissions:
            events.append({
                "type": "ADMISSION",
                "date": adm.admission_date.isoformat(),
                "academic_year": adm.academic_year,
                "institution": inst.name,
                "programme": prog.programme_name,
                "category": adm.admission_category,
                "supernumerary": adm.supernumerary_status,
                "description": f"Enrolled via {adm.admission_category} quota",
            })

        for obs, inst, prog in observations:
            events.append({
                "type": "ANNUAL_OBSERVATION",
                "timestamp": obs.observation_timestamp.isoformat(),
                "academic_year": obs.academic_year,
                "institution": inst.name,
                "programme": prog.programme_name,
                "status": obs.student_status,
                "description": f"Observed in active annual roster ({obs.student_status})",
            })

        for tr in transfers:
            events.append({
                "type": "TRANSFER",
                "date": tr.transfer_date.isoformat(),
                "academic_year": tr.academic_year,
                "status": tr.verification_status,
                "description": f"Inter-institutional transfer ({tr.verification_status})",
            })

        # Sort timeline events chronologically
        events.sort(key=lambda x: x.get("date") or x.get("timestamp") or "")

        return {
            "identity": {
                "id": str(identity.id),
                "internal_student_uuid": str(identity.internal_student_uuid),
                "full_name": identity.full_name,
                "masked_apaar": identity.masked_apaar_reference or "NOT PROVIDED",
                "identity_status": identity.identity_status,
                "date_of_birth": identity.date_of_birth.isoformat() if identity.date_of_birth else None,
                "gender": identity.gender,
            },
            "institutions_enrolled": [
                {
                    "institution_name": inst.name,
                    "institution_code": inst.institution_code,
                    "programme_name": prog.programme_name,
                    "student_id": rec.institution_student_id,
                    "status": rec.status,
                }
                for rec, inst, prog in inst_records
            ],
            "timeline": events,
        }

