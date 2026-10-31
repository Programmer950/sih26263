"""Institution and Programme Management Routes with Tenancy Enforcement."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from typing import Optional, List
import uuid
import math

from app.core.database import get_db
from app.core.permissions import get_current_user, require_roles, TenantGuard
from app.models import Institution, Programme, ApprovalConfiguration, User
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionResponse,
    PaginatedInstitutionsResponse,
    ProgrammeCreate,
    ProgrammeResponse,
    ApprovalConfigCreate,
    ApprovalConfigResponse,
)

router = APIRouter(prefix="/institutions", tags=["Institutions & Programmes"])


@router.get("", response_model=PaginatedInstitutionsResponse)
def list_institutions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    state: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    tenant: TenantGuard = Depends(TenantGuard),
    db: Session = Depends(get_db),
):
    """
    Lists institutions with strict multi-tenancy enforcement.
    Institution Administrators are strictly restricted to their own institution.
    """
    query = select(Institution)

    # 1. Tenancy filtering
    scoped_id = tenant.scope_institution_id()
    if scoped_id is not None:
        query = query.where(Institution.id == scoped_id)
    else:
        # Reviewers & Admins can filter
        if state:
            query = query.where(func.lower(Institution.state) == state.strip().lower())
        if category:
            query = query.where(func.lower(Institution.category) == category.strip().lower())
        if search:
            search_pattern = f"%{search.strip().lower()}%"
            query = query.where(
                (func.lower(Institution.name).like(search_pattern))
                | (func.lower(Institution.institution_code).like(search_pattern))
            )

    # Count total
    total_count = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0

    # Pagination
    offset = (page - 1) * limit
    institutions = db.execute(
        query.order_by(Institution.name.asc()).offset(offset).limit(limit)
    ).scalars().all()

    # Calculate active programme counts
    inst_ids = [inst.id for inst in institutions]
    prog_counts = {}
    if inst_ids:
        counts = db.execute(
            select(Programme.institution_id, func.count(Programme.id))
            .where(Programme.institution_id.in_(inst_ids), Programme.status == "ACTIVE")
            .group_by(Programme.institution_id)
        ).all()
        prog_counts = {cid: cnt for cid, cnt in counts}

    items = [
        InstitutionResponse(
            id=inst.id,
            institution_code=inst.institution_code,
            name=inst.name,
            category=inst.category,
            approval_status=inst.approval_status,
            state=inst.state,
            district=inst.district,
            pincode=inst.pincode,
            address=inst.address,
            contact_email=inst.contact_email,
            programme_count=prog_counts.get(inst.id, 0),
            created_at=inst.created_at,
            updated_at=inst.updated_at,
        )
        for inst in institutions
    ]

    return PaginatedInstitutionsResponse(
        items=items,
        total=total_count,
        page=page,
        limit=limit,
        pages=math.ceil(total_count / limit) if total_count > 0 else 1,
    )


@router.get("/{institution_id}", response_model=InstitutionResponse)
def get_institution(
    institution_id: uuid.UUID,
    tenant: TenantGuard = Depends(TenantGuard),
    db: Session = Depends(get_db),
):
    """
    Retrieves details for a specific institution.
    Enforces tenant boundary check (Safeguard 3).
    """
    tenant.scope_institution_id(institution_id)

    inst = db.execute(
        select(Institution).where(Institution.id == institution_id)
    ).scalar_one_or_none()

    if inst is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found.",
        )

    prog_count = db.execute(
        select(func.count(Programme.id)).where(
            Programme.institution_id == inst.id, Programme.status == "ACTIVE"
        )
    ).scalar() or 0

    return InstitutionResponse(
        id=inst.id,
        institution_code=inst.institution_code,
        name=inst.name,
        category=inst.category,
        approval_status=inst.approval_status,
        state=inst.state,
        district=inst.district,
        pincode=inst.pincode,
        address=inst.address,
        contact_email=inst.contact_email,
        programme_count=prog_count,
        created_at=inst.created_at,
        updated_at=inst.updated_at,
    )


@router.post("", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
def create_institution(
    req: InstitutionCreate,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "REGULATORY_REVIEWER")),
    db: Session = Depends(get_db),
):
    """Registers a new institution (Restricted to SYSTEM_ADMIN and REGULATORY_REVIEWER)."""
    existing = db.execute(
        select(Institution).where(
            func.lower(Institution.institution_code) == req.institution_code.strip().lower()
        )
    ).scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Institution with code '{req.institution_code}' already exists.",
        )

    inst = Institution(
        institution_code=req.institution_code.strip().upper(),
        name=req.name.strip(),
        category=req.category.strip().upper(),
        approval_status="APPROVED",
        state=req.state.strip(),
        district=req.district.strip(),
        pincode=req.pincode,
        address=req.address,
        contact_email=req.contact_email,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    return InstitutionResponse(
        id=inst.id,
        institution_code=inst.institution_code,
        name=inst.name,
        category=inst.category,
        approval_status=inst.approval_status,
        state=inst.state,
        district=inst.district,
        pincode=inst.pincode,
        address=inst.address,
        contact_email=inst.contact_email,
        programme_count=0,
        created_at=inst.created_at,
        updated_at=inst.updated_at,
    )


@router.get("/{institution_id}/programmes", response_model=List[ProgrammeResponse])
def list_programmes(
    institution_id: uuid.UUID,
    academic_year: Optional[str] = None,
    tenant: TenantGuard = Depends(TenantGuard),
    db: Session = Depends(get_db),
):
    """
    Retrieves approved programmes offered by an institution with applicable approved intake.
    """
    tenant.scope_institution_id(institution_id)

    programmes = db.execute(
        select(Programme)
        .where(Programme.institution_id == institution_id)
        .order_by(Programme.programme_code.asc())
    ).scalars().all()

    results = []
    for p in programmes:
        intake = None
        year = academic_year
        if academic_year:
            config = db.execute(
                select(ApprovalConfiguration).where(
                    ApprovalConfiguration.programme_id == p.id,
                    ApprovalConfiguration.academic_year == academic_year,
                    ApprovalConfiguration.status == "ACTIVE",
                ).order_by(ApprovalConfiguration.configuration_version.desc())
            ).scalars().first()
            if config:
                intake = config.approved_intake
        else:
            # Fetch latest active config
            config = db.execute(
                select(ApprovalConfiguration).where(
                    ApprovalConfiguration.programme_id == p.id,
                    ApprovalConfiguration.status == "ACTIVE",
                ).order_by(ApprovalConfiguration.academic_year.desc(), ApprovalConfiguration.configuration_version.desc())
            ).scalars().first()
            if config:
                intake = config.approved_intake
                year = config.academic_year

        results.append(
            ProgrammeResponse(
                id=p.id,
                institution_id=p.institution_id,
                programme_code=p.programme_code,
                programme_name=p.programme_name,
                qualification_level=p.qualification_level,
                duration_years=p.duration_years,
                status=p.status,
                approved_intake=intake,
                academic_year=year,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )

    return results


@router.post("/{institution_id}/programmes", response_model=ProgrammeResponse, status_code=status.HTTP_201_CREATED)
def create_programme(
    institution_id: uuid.UUID,
    req: ProgrammeCreate,
    tenant: TenantGuard = Depends(TenantGuard),
    db: Session = Depends(get_db),
):
    """Adds a programme to the institution."""
    tenant.scope_institution_id(institution_id)

    existing = db.execute(
        select(Programme).where(
            Programme.institution_id == institution_id,
            func.lower(Programme.programme_code) == req.programme_code.strip().lower(),
        )
    ).scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Programme with code '{req.programme_code}' already exists for this institution.",
        )

    prog = Programme(
        institution_id=institution_id,
        programme_code=req.programme_code.strip().upper(),
        programme_name=req.programme_name.strip(),
        qualification_level=req.qualification_level.strip().upper(),
        duration_years=req.duration_years,
        status="ACTIVE",
    )
    db.add(prog)
    db.commit()
    db.refresh(prog)

    return ProgrammeResponse(
        id=prog.id,
        institution_id=prog.institution_id,
        programme_code=prog.programme_code,
        programme_name=prog.programme_name,
        qualification_level=prog.qualification_level,
        duration_years=prog.duration_years,
        status=prog.status,
        approved_intake=None,
        academic_year=None,
        created_at=prog.created_at,
        updated_at=prog.updated_at,
    )


@router.post(
    "/{institution_id}/programmes/{programme_id}/approval-configs",
    response_model=ApprovalConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
def configure_programme_intake(
    institution_id: uuid.UUID,
    programme_id: uuid.UUID,
    req: ApprovalConfigCreate,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "REGULATORY_REVIEWER")),
    db: Session = Depends(get_db),
):
    """
    Configures statutory intake limit and quotas versioned by academic year.
    Restricted to SYSTEM_ADMIN and REGULATORY_REVIEWER.
    """
    prog = db.execute(
        select(Programme).where(
            Programme.id == programme_id, Programme.institution_id == institution_id
        )
    ).scalar_one_or_none()

    if prog is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Programme not found for specified institution.",
        )

    # Determine next configuration version for this academic year
    latest_version = db.execute(
        select(func.max(ApprovalConfiguration.configuration_version)).where(
            ApprovalConfiguration.programme_id == programme_id,
            ApprovalConfiguration.academic_year == req.academic_year,
        )
    ).scalar() or 0

    # Demote earlier active version if necessary
    db.execute(
        select(ApprovalConfiguration).where(
            ApprovalConfiguration.programme_id == programme_id,
            ApprovalConfiguration.academic_year == req.academic_year,
            ApprovalConfiguration.status == "ACTIVE",
        )
    )

    new_config = ApprovalConfiguration(
        institution_id=institution_id,
        programme_id=programme_id,
        academic_year=req.academic_year,
        approved_intake=req.approved_intake,
        supernumerary_quota_percentage=req.supernumerary_quota_percentage,
        lateral_entry_quota_percentage=req.lateral_entry_quota_percentage,
        approval_reference=req.approval_reference,
        effective_from=req.effective_from,
        effective_to=req.effective_to,
        configuration_version=latest_version + 1,
        status="ACTIVE",
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)

    return ApprovalConfigResponse(
        id=new_config.id,
        institution_id=new_config.institution_id,
        programme_id=new_config.programme_id,
        academic_year=new_config.academic_year,
        approved_intake=new_config.approved_intake,
        supernumerary_quota_percentage=float(new_config.supernumerary_quota_percentage),
        lateral_entry_quota_percentage=float(new_config.lateral_entry_quota_percentage),
        approval_reference=new_config.approval_reference,
        effective_from=new_config.effective_from,
        effective_to=new_config.effective_to,
        configuration_version=new_config.configuration_version,
        status=new_config.status,
        created_at=new_config.created_at,
    )

