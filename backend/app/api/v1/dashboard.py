"""Regulatory & Institutional Dashboard API Router."""

import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models import User
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    ReportExportRequest,
)
from app.services.dashboard_service import DashboardService

logger = logging.getLogger("apaar_setu.dashboard_api")

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse, status_code=status.HTTP_200_OK)
def get_dashboard_summary(
    institution_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves live dashboard summary KPIs:
    - Scoped to own institution for INSTITUTION_ADMIN.
    - System-wide for REGULATORY_REVIEWER and SYSTEM_ADMIN.
    - Zero-division safe, dynamic discrepancy count tracking.
    """
    return DashboardService.get_summary(
        db=db,
        actor=current_user,
        institution_id=institution_id,
    )


@router.get("/reports/export")
def export_report_csv(
    report_type: str = Query("INSTITUTION_ENROLMENT"),
    academic_year: Optional[str] = Query(None),
    institution_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Exports certified reproducible CSV reports with formula-injection defusing.
    """
    req = ReportExportRequest(
        report_type=report_type,
        academic_year=academic_year,
        institution_id=institution_id,
        format="csv",
    )
    return DashboardService.generate_report_stream(
        db=db,
        actor=current_user,
        req=req,
    )

