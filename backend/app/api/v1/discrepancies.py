"""Discrepancies API Router for Investigation Cases, Dossiers, and Decisions."""

import uuid
import math
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, and_

from app.core.database import get_db
from app.core.permissions import get_current_user, TenantGuard
from app.models import (
    User,
    DiscrepancyCase,
    DiscrepancyCaseDecision,
    StudentIdentity,
    ReconciliationResultItem,
)
from app.schemas.reconciliation import (
    DiscrepancyCaseDetail,
    PaginatedDiscrepancyCasesResponse,
    CaseDecisionCreateRequest,
    DiscrepancyCaseDecisionItem,
)
from app.services.discrepancy_service import DiscrepancyService

logger = logging.getLogger("apaar_setu.discrepancies")

router = APIRouter(prefix="/discrepancies", tags=["Discrepancies"])


@router.get("/cases", response_model=PaginatedDiscrepancyCasesResponse)
def list_discrepancy_cases(
    institution_id: Optional[uuid.UUID] = Query(None),
    programme_id: Optional[uuid.UUID] = Query(None),
    academic_year: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    review_priority: Optional[str] = Query(None),
    case_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    guard: TenantGuard = Depends(),
    db: Session = Depends(get_db),
):
    """
    Lists discrepancy investigation cases with multi-tenant scoping and filtering.
    """
    effective_inst_id = guard.scope_institution_id(institution_id)

    query = select(DiscrepancyCase, StudentIdentity).join(
        StudentIdentity, DiscrepancyCase.student_identity_id == StudentIdentity.id
    )
    filters = []

    if effective_inst_id:
        filters.append(DiscrepancyCase.institution_id == effective_inst_id)
    if programme_id:
        filters.append(DiscrepancyCase.programme_id == programme_id)
    if academic_year:
        filters.append(DiscrepancyCase.academic_year == academic_year)
    if classification:
        filters.append(DiscrepancyCase.classification == classification)
    if review_priority:
        filters.append(DiscrepancyCase.review_priority == review_priority)
    if case_status:
        filters.append(DiscrepancyCase.case_status == case_status)

    if filters:
        query = query.where(and_(*filters))

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    offset = (page - 1) * limit
    rows = db.execute(
        query.order_by(desc(DiscrepancyCase.updated_at)).offset(offset).limit(limit)
    ).all()

    items = []
    for case, student in rows:
        # Fetch latest system explanation
        latest_item = db.execute(
            select(ReconciliationResultItem).where(
                ReconciliationResultItem.discrepancy_case_id == case.id
            ).order_by(desc(ReconciliationResultItem.created_at))
        ).scalars().first()

        items.append(
            DiscrepancyCaseDetail(
                id=case.id,
                case_number=case.case_number,
                institution_id=case.institution_id,
                programme_id=case.programme_id,
                academic_year=case.academic_year,
                student_identity_id=case.student_identity_id,
                student_name=student.full_name,
                masked_apaar=student.masked_apaar_reference,
                classification=case.classification,
                review_priority=case.review_priority,
                case_status=case.case_status,
                occurrence_count=case.occurrence_count,
                system_explanation=latest_item.system_explanation if latest_item else "",
                initial_reconciliation_run_id=case.initial_reconciliation_run_id,
                latest_reconciliation_run_id=case.latest_reconciliation_run_id,
                linked_prior_case_id=case.linked_prior_case_id,
                created_at=case.created_at,
                updated_at=case.updated_at,
                decisions=[],
            )
        )

    pages = math.ceil(total / limit) if total > 0 else 1
    return PaginatedDiscrepancyCasesResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/cases/{id}", response_model=DiscrepancyCaseDetail)
def get_discrepancy_case(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves full discrepancy case dossier with side-by-side observation evidence
    and complete chronological decision history.
    """
    return DiscrepancyService.get_case_detail(db=db, case_id=id, actor=current_user)


@router.post("/cases/{id}/decisions", response_model=DiscrepancyCaseDecisionItem)
def record_case_decision(
    id: uuid.UUID,
    req: CaseDecisionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Executes a controlled decision on a discrepancy case.
    Validates role permissions, state transitions, and mandatory regulatory justification.
    Updates case status transactionally and appends to immutable decision history.
    """
    decision = DiscrepancyService.record_decision(
        db=db,
        case_id=id,
        req=req,
        actor=current_user,
    )
    return DiscrepancyCaseDecisionItem(
        id=decision.id,
        from_status=decision.from_status,
        to_status=decision.to_status,
        action=decision.action,
        mandatory_reason=decision.mandatory_reason,
        evidence_references=decision.evidence_references or {},
        decided_by_user_id=decision.decided_by_user_id,
        decided_by_name=current_user.name,
        created_at=decision.created_at,
    )


@router.get("/cases/{id}/history", response_model=List[DiscrepancyCaseDecisionItem])
def get_case_decision_history(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the complete immutable chronological decision log for a case.
    """
    detail = DiscrepancyService.get_case_detail(db=db, case_id=id, actor=current_user)
    return detail.decisions

