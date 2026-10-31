"""Regulatory Approval and Intake Verification API Router."""

import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.permissions import get_current_user, require_roles
from app.models import (
    User,
    ApprovalConfiguration,
    IntakeReconciliationSummary,
)
from app.schemas.approval import (
    ApprovalConfigurationCreate,
    ApprovalConfigurationAmend,
    ApprovalConfigurationRevoke,
    ApprovalConfigurationResponse,
    IntakeReconciliationRequest,
    IntakeReconciliationSummaryResponse,
)
from app.services.approval_service import ApprovalService
from app.services.intake_service import IntakeService

logger = logging.getLogger("apaar_setu.approvals_api")

router = APIRouter(prefix="/approvals", tags=["Regulatory Approvals & Intake"])


@router.post(
    "/configurations",
    response_model=ApprovalConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_approval_configuration(
    req: ApprovalConfigurationCreate,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "REGULATORY_REVIEWER")),
    db: Session = Depends(get_db),
):
    """
    Creates Version 1 of a statutory approval configuration with category allocation quotas.
    Restricted to authorised regulatory roles: SYSTEM_ADMIN and REGULATORY_REVIEWER.
    """
    return ApprovalService.create_configuration(db=db, req=req, actor=current_user)


@router.post(
    "/configurations/{config_id}/amend",
    response_model=ApprovalConfigurationResponse,
)
def amend_approval_configuration(
    config_id: uuid.UUID,
    req: ApprovalConfigurationAmend,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "REGULATORY_REVIEWER")),
    db: Session = Depends(get_db),
):
    """
    Amends an active configuration by superseding it and generating Version N+1.
    Requires mandatory justification and acquires transaction-scoped row locks.
    Restricted to authorised regulatory roles: SYSTEM_ADMIN and REGULATORY_REVIEWER.
    """
    return ApprovalService.amend_configuration(
        db=db,
        config_id=config_id,
        req=req,
        actor=current_user,
    )


@router.post(
    "/configurations/{config_id}/revoke",
    response_model=ApprovalConfigurationResponse,
)
def revoke_approval_configuration(
    config_id: uuid.UUID,
    req: ApprovalConfigurationRevoke,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "REGULATORY_REVIEWER")),
    db: Session = Depends(get_db),
):
    """
    Revokes an active configuration with mandatory regulatory justification.
    Restricted to authorised regulatory roles: SYSTEM_ADMIN and REGULATORY_REVIEWER.
    """
    return ApprovalService.revoke_configuration(
        db=db,
        config_id=config_id,
        req=req,
        actor=current_user,
    )


@router.get(
    "/configurations",
    response_model=List[ApprovalConfigurationResponse],
)
def list_approval_configurations(
    institution_id: Optional[uuid.UUID] = Query(None),
    programme_id: Optional[uuid.UUID] = Query(None),
    academic_year: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "REGULATORY_REVIEWER", "INSTITUTION_ADMIN")),
    db: Session = Depends(get_db),
):
    """
    Lists statutory approval configurations with role-based multi-tenancy scoping.
    """
    return ApprovalService.list_configurations(
        db=db,
        actor=current_user,
        institution_id=institution_id,
        programme_id=programme_id,
        academic_year=academic_year,
        status_filter=status_filter,
    )


@router.get(
    "/configurations/history",
    response_model=List[ApprovalConfigurationResponse],
)
def get_configuration_history(
    institution_id: uuid.UUID = Query(...),
    programme_id: uuid.UUID = Query(...),
    academic_year: str = Query(...),
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "REGULATORY_REVIEWER", "INSTITUTION_ADMIN")),
    db: Session = Depends(get_db),
):
    """
    Retrieves full version lineage of configurations for an academic year, ordered by version descending.
    """
    return ApprovalService.get_configuration_history(
        db=db,
        institution_id=institution_id,
        programme_id=programme_id,
        academic_year=academic_year,
        actor=current_user,
    )


@router.get(
    "/configurations/{config_id}",
    response_model=ApprovalConfigurationResponse,
)
def get_approval_configuration_by_id(
    config_id: uuid.UUID,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "REGULATORY_REVIEWER", "INSTITUTION_ADMIN")),
    db: Session = Depends(get_db),
):
    """
    Retrieves single approval configuration by ID.
    """
    config = db.get(ApprovalConfiguration, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval configuration {config_id} not found.",
        )
    if current_user.role.role_name == "INSTITUTION_ADMIN" and config.institution_id != current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenancy Violation: Access to approval configuration for external institution forbidden.",
        )
    return config


@router.post(
    "/intake/verify",
    response_model=IntakeReconciliationSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def verify_intake_compliance(
    req: IntakeReconciliationRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "REGULATORY_REVIEWER", "INSTITUTION_ADMIN")),
    db: Session = Depends(get_db),
):
    """
    Executes formal regulatory intake reconciliation against applicable approval configurations.
    Enforces multi-dimensional classification, anti-double-counting, versioned rounding,
    segregated lateral entry, and collective programme-level discrepancy case generation.
    """
    return IntakeService.verify_intake_for_snapshot(
        db=db,
        req=req,
        actor=current_user,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/intake/summary/{run_id}",
    response_model=IntakeReconciliationSummaryResponse,
)
def get_intake_summary_for_run(
    run_id: uuid.UUID,
    current_user: User = Depends(require_roles("SYSTEM_ADMIN", "REGULATORY_REVIEWER", "INSTITUTION_ADMIN")),
    db: Session = Depends(get_db),
):
    """
    Retrieves the intake reconciliation summary for a given reconciliation run.
    """
    summary = db.execute(
        select(IntakeReconciliationSummary).where(
            IntakeReconciliationSummary.reconciliation_run_id == run_id
        )
    ).scalar_one_or_none()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intake reconciliation summary for run {run_id} not found.",
        )

    # Tenancy check
    run = summary.reconciliation_run
    if current_user.role.role_name == "INSTITUTION_ADMIN" and run.institution_id != current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenancy Violation: Access to reconciliation run for external institution forbidden.",
        )

    cat_breakdown = summary.category_breakdown_json.get("categories", [])
    unclass_count = summary.category_breakdown_json.get("unclassified_count", 0)

    return IntakeReconciliationSummaryResponse(
        id=summary.id,
        reconciliation_run_id=summary.reconciliation_run_id,
        approval_configuration_id=summary.approval_configuration_id,
        approval_configuration_version=summary.approval_configuration_version,
        compliance_status=summary.compliance_status,
        regular_approved_intake=summary.regular_approved_intake,
        regular_enrolled_count=summary.regular_enrolled_count,
        regular_variance=summary.regular_variance,
        supernumerary_total_cap=summary.supernumerary_total_cap,
        supernumerary_enrolled_count=summary.supernumerary_enrolled_count,
        supernumerary_variance=summary.supernumerary_variance,
        lateral_entry_approved_cap=summary.lateral_entry_approved_cap,
        lateral_entry_enrolled_count=summary.lateral_entry_enrolled_count,
        lateral_entry_variance=summary.lateral_entry_variance,
        unclassified_count=unclass_count,
        category_breakdown=cat_breakdown,
        category_breakdown_json=summary.category_breakdown_json,
        discrepancy_cases_created=[],
        created_at=summary.created_at,
    )

