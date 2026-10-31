"""Verification Service for Authorised Student Verification and Secure QR Tokens."""

import uuid
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_
from fastapi import HTTPException, status

from app.models import (
    User,
    StudentIdentity,
    Institution,
    Programme,
    AnnualRosterObservation,
    AdmissionEpisode,
    InstitutionStudentRecord,
    VerificationRequest,
    AuditEvent,
)
from app.schemas.verification import (
    VerificationRequestCreate,
    VerificationRequestResponse,
    DisclosedStudentRecord,
    QRVerificationResponse,
)
from app.core.security import compute_blind_index
from app.services.identity_service import validate_apaar_format
from app.services.snapshot_service import SnapshotService

logger = logging.getLogger("apaar_setu.verification")


class VerificationService:
    """
    Manages authorized external student background verification journeys,
    minimal disclosure whitelisting, cryptographic token generation, and QR resolution.
    """

    @classmethod
    def request_verification(
        cls,
        db: Session,
        req: VerificationRequestCreate,
        actor: User,
    ) -> VerificationRequestResponse:
        """
        Executes external verification request:
        1. Validates consent confirmation and non-empty stated purpose.
        2. Resolves student identity via blind index, masked reference, or institutional ID.
        3. Enforces minimal field disclosure whitelist.
        4. Issues CSPRNG unpredictable verification token and QR verification payload.
        5. Logs hash-chained audit event into immutable ledger.
        """
        if not req.consent_confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Consent confirmation is required for external verification.",
            )

        if not req.stated_purpose or not req.stated_purpose.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification purpose cannot be blank or whitespace only.",
            )

        sanitized_apaar = req.apaar_id.strip().replace("-", "").replace(" ", "")
        student: Optional[StudentIdentity] = None

        # 1. Look up student by blind index or masked reference or institutional identifier
        if len(sanitized_apaar) >= 12:
            blind_idx = compute_blind_index(sanitized_apaar)
            student = db.execute(
                select(StudentIdentity).where(
                    or_(
                        StudentIdentity.apaar_blind_index == blind_idx,
                        StudentIdentity.masked_apaar_reference == f"XXXX-XXXX-{sanitized_apaar[-4:]}",
                    )
                )
            ).scalars().first()

        if not student:
            # Check by institutional student id
            inst_rec = db.execute(
                select(InstitutionStudentRecord).where(
                    InstitutionStudentRecord.institution_student_id == req.apaar_id.strip()
                )
            ).scalars().first()
            if inst_rec:
                student = db.get(StudentIdentity, inst_rec.student_identity_id)

        ref_id = f"VER-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:8].upper()}"

        if not student:
            # Student not found -> safe response without data leakage
            return VerificationRequestResponse(
                verification_reference=ref_id,
                status="NOT_FOUND",
                message="Student record not found for the provided identifier.",
                disclosed_record=None,
            )

        # 2. Resolve institution and programme enrolment context
        obs = db.execute(
            select(AnnualRosterObservation).where(
                AnnualRosterObservation.student_identity_id == student.id,
                AnnualRosterObservation.student_status == "ACTIVE",
            ).order_by(AnnualRosterObservation.observation_timestamp.desc())
        ).scalars().first()

        inst: Optional[Institution] = None
        prog: Optional[Programme] = None
        ay: str = "2024-25"

        if obs:
            inst = db.get(Institution, obs.institution_id)
            prog = db.get(Programme, obs.programme_id)
            ay = obs.academic_year
        else:
            ep = db.execute(
                select(AdmissionEpisode).where(
                    AdmissionEpisode.student_identity_id == student.id
                ).order_by(AdmissionEpisode.created_at.desc())
            ).scalars().first()
            if ep:
                inst = db.get(Institution, ep.institution_id)
                prog = db.get(Programme, ep.programme_id)
                ay = ep.academic_year

        inst_name = inst.name if inst else "Affiliated Institution"
        prog_name = prog.programme_name if prog else "Accredited Academic Programme"

        # 3. Minimal Field Disclosure Whitelist
        disclosed = DisclosedStudentRecord(
            student_name=student.full_name,
            masked_apaar=student.masked_apaar_reference or f"XXXX-XXXX-{sanitized_apaar[-4:]}",
            institution_name=inst_name,
            programme_name=prog_name,
            academic_year=ay,
            enrolment_status="ACTIVE",
            supported_status="ENROLLED",
        )

        # 4. Generate CSPRNG token & token hash
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        qr_payload = f"/api/v1/verification/qr/{token}"

        # 5. Persist VerificationRequest
        v_req = VerificationRequest(
            verification_reference=ref_id,
            token=token,
            token_hash=token_hash,
            student_identity_id=student.id,
            requester_user_id=actor.id,
            organization_name=req.organization_name or actor.role.role_name,
            verifier_name=req.verifier_name or actor.email,
            stated_purpose=req.stated_purpose,
            consent_confirmed=True,
            status="VERIFIED",
            disclosed_record_json=disclosed.model_dump(),
            expires_at=expires_at,
        )
        db.add(v_req)
        db.flush()

        # 6. Record Cryptographically Chained AuditEvent
        SnapshotService.record_chained_audit_event(
            db=db,
            actor_id=actor.id,
            action="STUDENT_VERIFICATION_REQUESTED",
            entity_type="VERIFICATION_REQUEST",
            entity_id=v_req.id,
            metadata_payload={
                "verification_reference": ref_id,
                "stated_purpose": req.stated_purpose,
                "masked_apaar": disclosed.masked_apaar,
                "status": "VERIFIED",
            },
        )
        db.commit()

        return VerificationRequestResponse(
            verification_reference=ref_id,
            status="VERIFIED",
            token=token,
            qr_payload=qr_payload,
            disclosed_record=disclosed,
            expires_at=expires_at,
        )

    @classmethod
    def verify_qr_token(cls, db: Session, token: str) -> QRVerificationResponse:
        """
        Public / Verifier QR verification endpoint.
        Validates token integrity, expiry, and revocation with minimal disclosure.
        """
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        v_req = db.execute(
            select(VerificationRequest).where(
                or_(
                    VerificationRequest.token == token,
                    VerificationRequest.token_hash == token_hash,
                )
            )
        ).scalars().first()

        if not v_req:
            return QRVerificationResponse(
                valid=False,
                status="INVALID",
                reason="INVALID_OR_UNKNOWN_TOKEN",
                disclosed_record=None,
            )

        if v_req.status == "REVOKED" or v_req.revoked_at is not None:
            return QRVerificationResponse(
                valid=False,
                status="REVOKED",
                reason="VERIFICATION_TOKEN_REVOKED",
                verification_reference=v_req.verification_reference,
                disclosed_record=None,
            )

        now_utc = datetime.now(timezone.utc)
        if v_req.expires_at < now_utc:
            return QRVerificationResponse(
                valid=False,
                status="EXPIRED",
                reason="VERIFICATION_TOKEN_EXPIRED",
                verification_reference=v_req.verification_reference,
                disclosed_record=None,
            )

        disclosed = DisclosedStudentRecord(**v_req.disclosed_record_json)
        return QRVerificationResponse(
            valid=True,
            status="VERIFIED",
            verification_reference=v_req.verification_reference,
            disclosed_record=disclosed,
            verified_at=v_req.created_at,
        )

