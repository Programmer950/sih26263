"""Student Repository API Controllers with Tenancy Enforcement."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from typing import Optional
import uuid
import math

from app.core.database import get_db
from app.core.permissions import get_current_user, TenantGuard
from app.models import (
    StudentIdentity,
    InstitutionStudentRecord,
    AdmissionEpisode,
    AnnualRosterObservation,
    Programme,
    Institution,
    User,
)
from app.services.identity_service import IdentityService
from app.schemas.student import (
    StudentRegisterRequest,
    StudentSummary,
    PaginatedStudentsResponse,
    StudentTimelineResponse,
)

router = APIRouter(prefix="/students", tags=["Student Repository"])


@router.get("", response_model=PaginatedStudentsResponse)
def list_students(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    institution_id: Optional[uuid.UUID] = None,
    programme_id: Optional[uuid.UUID] = None,
    academic_year: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    tenant: TenantGuard = Depends(TenantGuard),
    db: Session = Depends(get_db),
):
    """
    Lists student records with strict multi-tenancy enforcement.
    Institution Administrators are strictly isolated to their own institution.
    """
    # 1. Enforce tenancy
    scoped_inst_id = tenant.scope_institution_id(institution_id)

    # Base query joining record, identity, programme, institution
    query = (
        select(InstitutionStudentRecord, StudentIdentity, Programme, Institution)
        .join(StudentIdentity, InstitutionStudentRecord.student_identity_id == StudentIdentity.id)
        .join(Programme, InstitutionStudentRecord.programme_id == Programme.id)
        .join(Institution, InstitutionStudentRecord.institution_id == Institution.id)
    )

    if scoped_inst_id:
        query = query.where(InstitutionStudentRecord.institution_id == scoped_inst_id)

    if programme_id:
        query = query.where(InstitutionStudentRecord.programme_id == programme_id)

    if status_filter:
        query = query.where(InstitutionStudentRecord.status == status_filter.upper())

    if search:
        pattern = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(StudentIdentity.full_name).like(pattern),
                func.lower(InstitutionStudentRecord.institution_student_id).like(pattern),
                func.lower(StudentIdentity.masked_apaar_reference).like(pattern),
            )
        )

    # Count total
    total_count = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0

    # Pagination
    offset = (page - 1) * limit
    rows = db.execute(
        query.order_by(StudentIdentity.full_name.asc()).offset(offset).limit(limit)
    ).all()

    items = []
    for inst_rec, ident, prog, inst in rows:
        # Determine latest observation academic year
        latest_obs_year = db.execute(
            select(AnnualRosterObservation.academic_year)
            .where(
                AnnualRosterObservation.student_identity_id == ident.id,
                AnnualRosterObservation.institution_id == inst.id,
            )
            .order_by(AnnualRosterObservation.academic_year.desc())
        ).scalars().first() or "2024-25"

        items.append(
            StudentSummary(
                id=ident.id,
                internal_student_uuid=ident.internal_student_uuid,
                full_name=ident.full_name,
                masked_apaar_reference=ident.masked_apaar_reference,
                identity_status=ident.identity_status,
                institution_id=inst.id,
                institution_name=inst.name,
                institution_student_id=inst_rec.institution_student_id,
                programme_id=prog.id,
                programme_code=prog.programme_code,
                programme_name=prog.programme_name,
                status=inst_rec.status,
                latest_academic_year=latest_obs_year,
            )
        )

    return PaginatedStudentsResponse(
        items=items,
        total=total_count,
        page=page,
        limit=limit,
        pages=math.ceil(total_count / limit) if total_count > 0 else 1,
    )


@router.get("/{student_id}", response_model=StudentSummary)
def get_student(
    student_id: uuid.UUID,
    tenant: TenantGuard = Depends(TenantGuard),
    db: Session = Depends(get_db),
):
    """
    Retrieves a single student record with strict object-level tenancy authorization.
    """
    scoped_inst_id = tenant.scope_institution_id()

    # Query matching student
    query = (
        select(InstitutionStudentRecord, StudentIdentity, Programme, Institution)
        .join(StudentIdentity, InstitutionStudentRecord.student_identity_id == StudentIdentity.id)
        .join(Programme, InstitutionStudentRecord.programme_id == Programme.id)
        .join(Institution, InstitutionStudentRecord.institution_id == Institution.id)
        .where(StudentIdentity.id == student_id)
    )

    if scoped_inst_id:
        query = query.where(InstitutionStudentRecord.institution_id == scoped_inst_id)

    row = db.execute(query).first()
    if not row:
        # Check if student exists in another institution to return 403 vs 404
        exists_elsewhere = db.execute(
            select(InstitutionStudentRecord).where(
                InstitutionStudentRecord.student_identity_id == student_id
            )
        ).first()

        if exists_elsewhere and scoped_inst_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Specified student is not associated with your institution.",
            )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student record not found.",
        )

    inst_rec, ident, prog, inst = row

    latest_obs_year = db.execute(
        select(AnnualRosterObservation.academic_year)
        .where(
            AnnualRosterObservation.student_identity_id == ident.id,
            AnnualRosterObservation.institution_id == inst.id,
        )
        .order_by(AnnualRosterObservation.academic_year.desc())
    ).scalars().first() or "2024-25"

    return StudentSummary(
        id=ident.id,
        internal_student_uuid=ident.internal_student_uuid,
        full_name=ident.full_name,
        masked_apaar_reference=ident.masked_apaar_reference,
        identity_status=ident.identity_status,
        institution_id=inst.id,
        institution_name=inst.name,
        institution_student_id=inst_rec.institution_student_id,
        programme_id=prog.id,
        programme_code=prog.programme_code,
        programme_name=prog.programme_name,
        status=inst_rec.status,
        latest_academic_year=latest_obs_year,
    )



@router.get("/{student_id}/timeline", response_model=StudentTimelineResponse)
def get_student_timeline(
    student_id: uuid.UUID,
    tenant: TenantGuard = Depends(TenantGuard),
    db: Session = Depends(get_db),
):
    """
    Reconstructs the longitudinal academic trajectory for an individual student.
    Enforces tenancy boundary: institution administrators cannot view timelines of students
    not associated with their institution.
    """
    scoped_inst_id = tenant.scope_institution_id()
    if scoped_inst_id:
        # Check student belongs to this institution
        record = db.execute(
            select(InstitutionStudentRecord).where(
                InstitutionStudentRecord.student_identity_id == student_id,
                InstitutionStudentRecord.institution_id == scoped_inst_id,
            )
        ).scalar_one_or_none()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Specified student is not associated with your institution.",
            )

    timeline_data = IdentityService.get_student_timeline(db, student_id)
    if not timeline_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student identity not found.",
        )

    return timeline_data


@router.post("", response_model=StudentSummary, status_code=status.HTTP_201_CREATED)
def register_student(
    req: StudentRegisterRequest,
    institution_id: Optional[uuid.UUID] = None,
    tenant: TenantGuard = Depends(TenantGuard),
    db: Session = Depends(get_db),
):
    """
    Registers a student record, creates discrete admission episode and annual observation.
    Enforces tenancy: Institution Admin is strictly tied to their own institution.
    """
    effective_inst_id = tenant.scope_institution_id(institution_id)
    if not effective_inst_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="institution_id parameter is required for regulatory administrators.",
        )

    # Verify programme belongs to this institution
    prog = db.execute(
        select(Programme).where(
            Programme.id == req.programme_id,
            Programme.institution_id == effective_inst_id,
        )
    ).scalar_one_or_none()
    if not prog:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specified programme does not exist for this institution.",
        )

    # Check duplicate roll number in same institution
    dup = db.execute(
        select(InstitutionStudentRecord).where(
            InstitutionStudentRecord.institution_id == effective_inst_id,
            InstitutionStudentRecord.institution_student_id == req.institution_student_id.strip(),
        )
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student ID '{req.institution_student_id}' is already registered in this institution.",
        )

    identity, inst_record, episode = IdentityService.register_student(
        db=db,
        institution_id=effective_inst_id,
        programme_id=req.programme_id,
        institution_student_id=req.institution_student_id,
        full_name=req.full_name,
        academic_year=req.academic_year,
        admission_date=req.admission_date,
        raw_apaar=req.apaar_id,
        date_of_birth=req.date_of_birth,
        gender=req.gender,
        admission_category=req.admission_category,
        supernumerary_status=req.supernumerary_status,
        nri_status=req.nri_status,
    )

    db.commit()

    inst = db.execute(select(Institution).where(Institution.id == effective_inst_id)).scalar_one()

    return StudentSummary(
        id=identity.id,
        internal_student_uuid=identity.internal_student_uuid,
        full_name=identity.full_name,
        masked_apaar_reference=identity.masked_apaar_reference,
        identity_status=identity.identity_status,
        institution_id=inst.id,
        institution_name=inst.name,
        institution_student_id=inst_record.institution_student_id,
        programme_id=prog.id,
        programme_code=prog.programme_code,
        programme_name=prog.programme_name,
        status=inst_record.status,
        latest_academic_year=req.academic_year,
    )

