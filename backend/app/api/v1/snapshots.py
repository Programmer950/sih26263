"""Snapshots API Router for Authoritative Promotion, Lifecycle Management, and Reconciliation."""

import uuid
import math
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, and_

from app.core.database import get_db
from app.core.permissions import get_current_user, require_roles, TenantGuard
from app.models import User, RosterSnapshot, SourceSubmission
from app.schemas.snapshot import (
    SnapshotSummary,
    PaginatedSnapshotsResponse,
    SnapshotDetailResponse,
    SnapshotPromoteRequest,
    SnapshotPromoteResponse,
    SnapshotComparisonResponse,
)
from app.services.snapshot_service import SnapshotService
from app.services.comparison_service import ComparisonService
from app.services.export_service import ExportService

logger = logging.getLogger("apaar_setu.snapshots")

router = APIRouter(prefix="/snapshots", tags=["Snapshots"])


@router.get("", response_model=PaginatedSnapshotsResponse)
def list_snapshots(
    institution_id: Optional[uuid.UUID] = Query(None, description="Filter by Institution UUID"),
    programme_id: Optional[uuid.UUID] = Query(None, description="Filter by Programme UUID"),
    academic_year: Optional[str] = Query(None, description="Filter by Academic Year (e.g. 2024-25)"),
    is_authoritative: Optional[bool] = Query(None, description="Filter by authoritative status"),
    lifecycle_status: Optional[str] = Query(None, description="Filter by lifecycle status (ACTIVE, SUPERSEDED)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    guard: TenantGuard = Depends(),
    db: Session = Depends(get_db),
):
    """
    Lists roster snapshots with multi-tenant scoping and filtering.
    Institution Administrators are strictly restricted to their own institution.
    """
    effective_inst_id = guard.scope_institution_id(institution_id)

    query = select(RosterSnapshot)
    filters = []

    if effective_inst_id:
        filters.append(RosterSnapshot.institution_id == effective_inst_id)
    if programme_id:
        filters.append(RosterSnapshot.programme_id == programme_id)
    if academic_year:
        filters.append(RosterSnapshot.academic_year == academic_year)
    if is_authoritative is not None:
        filters.append(RosterSnapshot.is_authoritative == is_authoritative)
    if lifecycle_status:
        filters.append(RosterSnapshot.lifecycle_status == lifecycle_status)

    if filters:
        query = query.where(and_(*filters))

    # Total count query
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    # Paginate and order by created_at DESC
    offset = (page - 1) * limit
    paged_query = query.order_by(desc(RosterSnapshot.created_at)).offset(offset).limit(limit)
    snapshots = db.execute(paged_query).scalars().all()

    items = [
        SnapshotSummary(
            id=s.id,
            institution_id=s.institution_id,
            programme_id=s.programme_id,
            academic_year=s.academic_year,
            source_submission_id=s.source_submission_id,
            completeness_status=s.completeness_status,
            lifecycle_status=s.lifecycle_status,
            is_authoritative=s.is_authoritative,
            declared_headcount=s.declared_headcount,
            observed_headcount=s.observed_headcount,
            snapshot_canonicalization_version=s.snapshot_canonicalization_version,
            snapshot_hash=s.snapshot_hash,
            effective_from=s.effective_from,
            created_at=s.created_at,
            superseded_by_snapshot_id=s.superseded_by_snapshot_id,
            superseded_at=s.superseded_at,
        )
        for s in snapshots
    ]

    pages = math.ceil(total / limit) if total > 0 else 1

    return PaginatedSnapshotsResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/{id}", response_model=SnapshotDetailResponse)
def get_snapshot(
    id: uuid.UUID,
    guard: TenantGuard = Depends(),
    db: Session = Depends(get_db),
):
    """
    Retrieves detailed metadata, lifecycle state, and source submission provenance for a single snapshot.
    Enforces object-level tenancy checks.
    """
    snapshot = db.get(RosterSnapshot, id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot {id} not found.",
        )

    if guard.role_name == "INSTITUTION_ADMIN" and snapshot.institution_id != guard.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenancy Violation: Access to snapshot for external institution forbidden.",
        )

    submission = db.get(SourceSubmission, snapshot.source_submission_id)

    return SnapshotDetailResponse(
        id=snapshot.id,
        institution_id=snapshot.institution_id,
        programme_id=snapshot.programme_id,
        academic_year=snapshot.academic_year,
        source_submission_id=snapshot.source_submission_id,
        completeness_status=snapshot.completeness_status,
        lifecycle_status=snapshot.lifecycle_status,
        is_authoritative=snapshot.is_authoritative,
        declared_headcount=snapshot.declared_headcount,
        observed_headcount=snapshot.observed_headcount,
        snapshot_canonicalization_version=snapshot.snapshot_canonicalization_version,
        snapshot_hash=snapshot.snapshot_hash,
        snapshot_metadata=snapshot.snapshot_metadata or {},
        effective_from=snapshot.effective_from,
        created_at=snapshot.created_at,
        created_by_user_id=snapshot.created_by_user_id,
        superseded_by_snapshot_id=snapshot.superseded_by_snapshot_id,
        superseded_at=snapshot.superseded_at,
        source_submission_filename=submission.original_filename if submission else None,
        source_submission_fingerprint=submission.file_fingerprint if submission else None,
    )


@router.post("/{id}/promote", response_model=SnapshotPromoteResponse)
def promote_snapshot(
    id: uuid.UUID,
    payload: Optional[SnapshotPromoteRequest] = None,
    current_user: User = Depends(require_roles("INSTITUTION_ADMIN", "SYSTEM_ADMIN")),
    db: Session = Depends(get_db),
):
    """
    Authoritative snapshot promotion endpoint.
    Atomically supersedes the previous authoritative snapshot and promotes the candidate snapshot.
    Protected by context-scoped PostgreSQL advisory locks and chained SHA-256 audit logs.
    """
    reason = payload.reason if payload else None
    return SnapshotService.promote_snapshot(
        db=db,
        snapshot_id=id,
        actor=current_user,
        reason=reason,
    )


@router.get("/{id}/compare", response_model=SnapshotComparisonResponse)
def compare_snapshot(
    id: uuid.UUID,
    baseline_id: Optional[uuid.UUID] = Query(None, description="Explicit baseline snapshot UUID (optional)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reconciles candidate snapshot records against an authoritative or specified baseline snapshot.
    Returns deterministic, non-punitive discrepancy classifications and provenance.
    """
    return ComparisonService.compare_snapshots(
        db=db,
        candidate_id=id,
        current_user=current_user,
        baseline_id=baseline_id,
    )


@router.get("/{id}/export")
def export_snapshot_roster(
    id: uuid.UUID,
    format: str = Query("csv", pattern="^(csv|xlsx)$", description="Export file format: csv or xlsx"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Downloads snapshot roster observations as CSV or XLSX.
    Protected against spreadsheet formula injection (CWE-1236) and scoped by tenant authorization.
    """
    return ExportService.export_snapshot_roster(
        db=db,
        snapshot_id=id,
        current_user=current_user,
        export_format=format,
    )


@router.get("/{id}/compare/export")
def export_comparison_report(
    id: uuid.UUID,
    baseline_id: Optional[uuid.UUID] = Query(None, description="Explicit baseline snapshot UUID (optional)"),
    format: str = Query("csv", pattern="^(csv|xlsx)$", description="Export file format: csv or xlsx"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Downloads snapshot comparison discrepancy analysis as CSV or XLSX.
    Protected against spreadsheet formula injection (CWE-1236) and scoped by tenant authorization.
    """
    return ExportService.export_comparison_report(
        db=db,
        candidate_id=id,
        current_user=current_user,
        baseline_id=baseline_id,
        export_format=format,
    )

