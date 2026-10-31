"""Reconciliation Runs API Router."""

import uuid
import math
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, and_

from app.core.database import get_db
from app.core.permissions import get_current_user, TenantGuard
from app.models import (
    User,
    ReconciliationRun,
    ReconciliationResultItem,
    StudentIdentity,
)
from app.schemas.reconciliation import (
    ReconciliationRunCreateRequest,
    ReconciliationRunResponse,
    PaginatedReconciliationRunsResponse,
    ResultItemDetail,
    PaginatedResultItemsResponse,
)
from app.schemas.unified_reconciliation import (
    UnifiedReconciliationRequest,
    UnifiedReconciliationResponse,
    DuplicateConflictItem,
)
from app.schemas.aggregate import (
    AggregateDeclarationCreate,
    AggregateDeclarationResponse,
    AggregateReconciliationRequest,
    AggregateReconciliationResult,
)
from app.services.reconciliation_service import ReconciliationService
from app.services.unified_reconciliation_service import UnifiedReconciliationService
from app.services.duplicate_service import DuplicateService
from app.services.aggregate_reconciliation_service import AggregateReconciliationService

logger = logging.getLogger("apaar_setu.reconciliation")

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


@router.post("/runs", response_model=ReconciliationRunResponse, status_code=status.HTTP_201_CREATED)
def create_reconciliation_run(
    req: ReconciliationRunCreateRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Executes a formal reconciliation run on a candidate snapshot.
    Persists immutable run results for all 8 student classifications.
    Creates or links discrepancy cases according to the case-creation policy.
    Supports request idempotency via Idempotency-Key header.
    """
    run = ReconciliationService.execute_run(
        db=db,
        req=req,
        actor=current_user,
        idempotency_key=idempotency_key,
    )
    return ReconciliationRunResponse(
        id=run.id,
        institution_id=run.institution_id,
        programme_id=run.programme_id,
        academic_year=run.academic_year,
        candidate_snapshot_id=run.candidate_snapshot_id,
        candidate_snapshot_hash=run.candidate_snapshot_hash,
        baseline_snapshot_id=run.baseline_snapshot_id,
        baseline_snapshot_hash=run.baseline_snapshot_hash,
        run_type=run.run_type,
        execution_status=run.execution_status,
        engine_version=run.engine_version,
        rules_version=run.rules_version,
        result_fingerprint=run.result_fingerprint,
        summary_counts=run.summary_counts or {},
        initiated_by_user_id=run.initiated_by_user_id,
        created_at=run.created_at,
    )


@router.get("/runs", response_model=PaginatedReconciliationRunsResponse)
def list_reconciliation_runs(
    institution_id: Optional[uuid.UUID] = Query(None),
    programme_id: Optional[uuid.UUID] = Query(None),
    academic_year: Optional[str] = Query(None),
    execution_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    guard: TenantGuard = Depends(),
    db: Session = Depends(get_db),
):
    """
    Lists reconciliation runs with tenant isolation and optional filtering.
    """
    effective_inst_id = guard.scope_institution_id(institution_id)

    query = select(ReconciliationRun)
    filters = []

    if effective_inst_id:
        filters.append(ReconciliationRun.institution_id == effective_inst_id)
    if programme_id:
        filters.append(ReconciliationRun.programme_id == programme_id)
    if academic_year:
        filters.append(ReconciliationRun.academic_year == academic_year)
    if execution_status:
        filters.append(ReconciliationRun.execution_status == execution_status)

    if filters:
        query = query.where(and_(*filters))

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    offset = (page - 1) * limit
    runs = db.execute(query.order_by(desc(ReconciliationRun.created_at)).offset(offset).limit(limit)).scalars().all()

    items = [
        ReconciliationRunResponse(
            id=r.id,
            institution_id=r.institution_id,
            programme_id=r.programme_id,
            academic_year=r.academic_year,
            candidate_snapshot_id=r.candidate_snapshot_id,
            candidate_snapshot_hash=r.candidate_snapshot_hash,
            baseline_snapshot_id=r.baseline_snapshot_id,
            baseline_snapshot_hash=r.baseline_snapshot_hash,
            run_type=r.run_type,
            execution_status=r.execution_status,
            engine_version=r.engine_version,
            rules_version=r.rules_version,
            result_fingerprint=r.result_fingerprint,
            summary_counts=r.summary_counts or {},
            initiated_by_user_id=r.initiated_by_user_id,
            created_at=r.created_at,
        )
        for r in runs
    ]

    pages = math.ceil(total / limit) if total > 0 else 1
    return PaginatedReconciliationRunsResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/runs/{id}", response_model=ReconciliationRunResponse)
def get_reconciliation_run(
    id: uuid.UUID,
    guard: TenantGuard = Depends(),
    db: Session = Depends(get_db),
):
    """
    Retrieves detailed execution overview of a single reconciliation run.
    """
    run = db.get(ReconciliationRun, id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reconciliation run {id} not found.",
        )

    if guard.role_name == "INSTITUTION_ADMIN" and run.institution_id != guard.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenancy Violation: Access to reconciliation run for external institution forbidden.",
        )

    return ReconciliationRunResponse(
        id=run.id,
        institution_id=run.institution_id,
        programme_id=run.programme_id,
        academic_year=run.academic_year,
        candidate_snapshot_id=run.candidate_snapshot_id,
        candidate_snapshot_hash=run.candidate_snapshot_hash,
        baseline_snapshot_id=run.baseline_snapshot_id,
        baseline_snapshot_hash=run.baseline_snapshot_hash,
        run_type=run.run_type,
        execution_status=run.execution_status,
        engine_version=run.engine_version,
        rules_version=run.rules_version,
        result_fingerprint=run.result_fingerprint,
        summary_counts=run.summary_counts or {},
        initiated_by_user_id=run.initiated_by_user_id,
        created_at=run.created_at,
    )


@router.get("/runs/{id}/results", response_model=PaginatedResultItemsResponse)
@router.get("/runs/{id}/items", response_model=PaginatedResultItemsResponse)
def get_run_results(
    id: uuid.UUID,
    classification: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    guard: TenantGuard = Depends(),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated student-level reconciliation result items for all 8 categories.
    """
    run = db.get(ReconciliationRun, id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reconciliation run {id} not found.",
        )

    if guard.role_name == "INSTITUTION_ADMIN" and run.institution_id != guard.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenancy Violation: Access to reconciliation run for external institution forbidden.",
        )

    query = select(ReconciliationResultItem, StudentIdentity).join(
        StudentIdentity, ReconciliationResultItem.student_identity_id == StudentIdentity.id
    ).where(ReconciliationResultItem.reconciliation_run_id == run.id)

    if classification:
        query = query.where(ReconciliationResultItem.classification == classification)

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    offset = (page - 1) * limit
    rows = db.execute(
        query.order_by(
            ReconciliationResultItem.candidate_row_number.asc().nulls_last(),
            StudentIdentity.full_name.asc(),
        ).offset(offset).limit(limit)
    ).all()

    items = [
        ResultItemDetail(
            id=item.id,
            reconciliation_run_id=item.reconciliation_run_id,
            student_identity_id=item.student_identity_id,
            student_name=student.full_name,
            masked_apaar=student.masked_apaar_reference,
            classification=item.classification,
            review_priority=item.review_priority,
            system_explanation=item.system_explanation,
            is_case_eligible=item.is_case_eligible,
            discrepancy_case_id=item.discrepancy_case_id,
            candidate_row_number=item.candidate_row_number,
            baseline_row_number=item.baseline_row_number,
            candidate_submission_id=item.candidate_submission_id,
            baseline_submission_id=item.baseline_submission_id,
            created_at=item.created_at,
        )
        for item, student in rows
    ]

    pages = math.ceil(total / limit) if total > 0 else 1
    return PaginatedResultItemsResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post("/unified", response_model=UnifiedReconciliationResponse, status_code=status.HTTP_200_OK)
def execute_unified_reconciliation(
    req: UnifiedReconciliationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Executes unified multi-engine reconciliation:
    - Longitudinal cohort reconciliation
    - Statutory intake matrix verification
    - Cross-institution duplicate detection
    """
    if current_user.role.role_name not in ("INSTITUTION_ADMIN", "REGULATORY_REVIEWER", "SYSTEM_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role not authorized to execute unified reconciliation.",
        )
    return UnifiedReconciliationService.execute_unified(
        db=db,
        req=req,
        actor=current_user,
    )


@router.get("/duplicates", response_model=List[DuplicateConflictItem])
def list_cross_institution_duplicates(
    academic_year: Optional[str] = Query(None),
    institution_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lists cross-institution duplicate enrollment conflicts.
    Accessible to SYSTEM_ADMIN, REGULATORY_REVIEWER, and INSTITUTION_ADMIN (scoped to own institution).
    """
    if current_user.role.role_name not in ("INSTITUTION_ADMIN", "REGULATORY_REVIEWER", "SYSTEM_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role not authorized to access duplicate detection records.",
        )
    return DuplicateService.detect_duplicates(
        db=db,
        actor=current_user,
        academic_year=academic_year,
        institution_id=institution_id,
    )


# ---------------------------------------------------------------------------
# PRD Module 9: Historical Aggregate-to-Roster Reconciliation Endpoints
# ---------------------------------------------------------------------------

@router.post("/aggregate/declarations", response_model=AggregateDeclarationResponse, status_code=status.HTTP_201_CREATED)
def create_aggregate_declaration(
    req: AggregateDeclarationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new historical aggregate enrolment declaration."""
    return AggregateReconciliationService.create_declaration(
        db=db,
        actor=current_user,
        data=req,
    )


@router.get("/aggregate/declarations", response_model=List[AggregateDeclarationResponse], status_code=status.HTTP_200_OK)
def list_aggregate_declarations(
    institution_id: Optional[uuid.UUID] = Query(None),
    academic_year: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists historical aggregate declarations enforcing tenant and role boundaries."""
    return AggregateReconciliationService.list_declarations(
        db=db,
        actor=current_user,
        institution_id=institution_id,
        academic_year=academic_year,
    )


@router.post("/aggregate/reconcile", response_model=AggregateReconciliationResult, status_code=status.HTTP_200_OK)
def reconcile_aggregate_enrolment(
    req: AggregateReconciliationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Executes historical aggregate-to-roster comparability verification (PRD Module 9).
    Compares declared counts against detailed roster snapshots when compatible.
    """
    target_snapshot_id = req.roster_snapshot_id or req.snapshot_id
    return AggregateReconciliationService.reconcile(
        db=db,
        actor=current_user,
        declaration_id=req.declaration_id,
        roster_snapshot_id=target_snapshot_id,
    )



