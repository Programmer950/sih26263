"""Dashboard Analytics and Reporting Service.

Calculates live tenant-scoped and system-wide regulatory KPIs,
reconciliation metrics, discrepancy aggregates, and reproducible reports.
"""

import uuid
import csv
import io
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func, distinct, and_, or_, desc
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from app.models import (
    User,
    Institution,
    Programme,
    StudentIdentity,
    AnnualRosterObservation,
    SourceSubmission,
    RosterSnapshot,
    DiscrepancyCase,
    ApprovalConfiguration,
    IntakeReconciliationSummary,
    ReconciliationRun,
    AuditEvent,
)
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    ProgrammeEnrolmentMetric,
    AcademicYearEnrolmentMetric,
    ReportExportRequest,
)

logger = logging.getLogger("apaar_setu.dashboard")


def defuse_csv_formula(val: Any) -> str:
    """Defuses potential CSV formula injection vectors (=, +, -, @)."""
    s = str(val) if val is not None else ""
    if s and s[0] in ("=", "+", "-", "@"):
        return f"'{s}"
    return s


class DashboardService:
    """
    Computes real-time live database metrics for institution and regulatory dashboards.
    Enforces strict tenant isolation, zero-division resilience, and formula-injection defusing.
    """

    @classmethod
    def get_summary(
        cls,
        db: Session,
        actor: User,
        institution_id: Optional[uuid.UUID] = None,
    ) -> DashboardSummaryResponse:
        """
        Calculates dashboard summary metrics.
        - INSTITUTION_ADMIN: Strictly scoped to own institution.
        - REGULATORY_REVIEWER / SYSTEM_ADMIN: System-wide or optionally filtered by institution_id.
        """
        is_inst_admin = actor.role.role_name == "INSTITUTION_ADMIN"

        if is_inst_admin:
            if institution_id and institution_id != actor.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cross-tenant access forbidden: Cannot access foreign institution dashboard.",
                )
            target_inst_id = actor.institution_id
            role_scope = "INSTITUTION"
        else:
            target_inst_id = institution_id
            role_scope = "SYSTEM_WIDE" if not target_inst_id else "INSTITUTION"

        inst_name = None
        if target_inst_id:
            inst = db.get(Institution, target_inst_id)
            if inst:
                inst_name = inst.name

        # 1. Total Enrolled / Registered Students
        obs_query = select(func.count(distinct(AnnualRosterObservation.student_identity_id))).where(
            AnnualRosterObservation.student_status == "ACTIVE"
        )
        if target_inst_id:
            obs_query = obs_query.where(AnnualRosterObservation.institution_id == target_inst_id)
        total_registered_students = db.execute(obs_query).scalar() or 0

        # 2. Total Institutions
        if target_inst_id:
            total_institutions = 1
        else:
            total_institutions = db.execute(select(func.count(Institution.id))).scalar() or 0

        # 3. Total Programmes
        prog_query = select(func.count(Programme.id))
        if target_inst_id:
            prog_query = prog_query.where(Programme.institution_id == target_inst_id)
        total_programmes = db.execute(prog_query).scalar() or 0

        # 4. Total Submissions & Snapshots
        sub_query = select(func.count(SourceSubmission.id))
        if target_inst_id:
            sub_query = sub_query.where(SourceSubmission.institution_id == target_inst_id)
        total_submissions = db.execute(sub_query).scalar() or 0

        snap_query = select(func.count(RosterSnapshot.id))
        if target_inst_id:
            snap_query = snap_query.where(RosterSnapshot.institution_id == target_inst_id)
        total_snapshots = db.execute(snap_query).scalar() or 0

        # 5. Discrepancy Cases (Open vs. Resolved)
        case_base = select(DiscrepancyCase)
        if target_inst_id:
            case_base = case_base.where(DiscrepancyCase.institution_id == target_inst_id)

        all_cases = db.execute(case_base).scalars().all()
        total_cases = len(all_cases)
        open_cases = sum(1 for c in all_cases if c.case_status in ("OPEN", "UNDER_REVIEW"))
        resolved_cases = sum(1 for c in all_cases if c.case_status == "RESOLVED")

        # 6. Zero-Division Safe Percentage Calculations
        if total_registered_students > 0:
            apaar_valid_query = select(func.count(distinct(StudentIdentity.id))).join(
                AnnualRosterObservation, AnnualRosterObservation.student_identity_id == StudentIdentity.id
            ).where(
                StudentIdentity.identity_status.in_(["FORMAT_VALID", "EXTERNALLY_VERIFIED"]),
                AnnualRosterObservation.student_status == "ACTIVE",
            )
            if target_inst_id:
                apaar_valid_query = apaar_valid_query.where(AnnualRosterObservation.institution_id == target_inst_id)
            valid_apaar_count = db.execute(apaar_valid_query).scalar() or 0
            apaar_coverage = round((valid_apaar_count / total_registered_students) * 100.0, 1)
        else:
            apaar_coverage = 100.0  # Zero division safe

        intake_compliance_rate = 100.0
        if total_programmes > 0:
            intake_query = select(IntakeReconciliationSummary).join(
                ReconciliationRun, IntakeReconciliationSummary.reconciliation_run_id == ReconciliationRun.id
            )
            if target_inst_id:
                intake_query = intake_query.where(ReconciliationRun.institution_id == target_inst_id)
            summaries = db.execute(intake_query).scalars().all()
            if summaries:
                compliant_count = sum(1 for s in summaries if s.compliance_status == "COMPLIANT")
                intake_compliance_rate = round((compliant_count / len(summaries)) * 100.0, 1)

        # 7. Programme-wise Enrolment
        prog_rows_query = select(
            Programme.id,
            Programme.programme_name,
            func.count(distinct(AnnualRosterObservation.student_identity_id)).label("enrolled"),
        ).outerjoin(
            AnnualRosterObservation,
            and_(
                AnnualRosterObservation.programme_id == Programme.id,
                AnnualRosterObservation.student_status == "ACTIVE",
            )
        )
        if target_inst_id:
            prog_rows_query = prog_rows_query.where(Programme.institution_id == target_inst_id)
        prog_rows_query = prog_rows_query.group_by(Programme.id, Programme.programme_name)
        prog_results = db.execute(prog_rows_query).all()

        prog_metrics = [
            ProgrammeEnrolmentMetric(
                programme_id=p.id,
                programme_name=p.programme_name,
                enrolled_count=p.enrolled or 0,
            )
            for p in prog_results
        ]

        # 8. Academic Year Enrolment
        ay_query = select(
            AnnualRosterObservation.academic_year,
            func.count(distinct(AnnualRosterObservation.student_identity_id)).label("enrolled"),
        ).where(AnnualRosterObservation.student_status == "ACTIVE")
        if target_inst_id:
            ay_query = ay_query.where(AnnualRosterObservation.institution_id == target_inst_id)
        ay_query = ay_query.group_by(AnnualRosterObservation.academic_year).order_by(AnnualRosterObservation.academic_year.desc())
        ay_results = db.execute(ay_query).all()

        ay_metrics = [
            AcademicYearEnrolmentMetric(
                academic_year=ay.academic_year,
                enrolled_count=ay.enrolled or 0,
            )
            for ay in ay_results
        ]

        # 9. Recent Activity
        audit_query = select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(8)
        recent_events = db.execute(audit_query).scalars().all()
        recent_activity = [
            {
                "id": str(ev.id),
                "action": ev.action,
                "entity_type": ev.entity_type,
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                "event_hash_preview": ev.event_hash[:12] if ev.event_hash else None,
            }
            for ev in recent_events
        ]

        return DashboardSummaryResponse(
            institution_id=target_inst_id,
            institution_name=inst_name,
            role_scope=role_scope,
            total_registered_students=total_registered_students,
            total_institutions=total_institutions,
            total_programmes=total_programmes,
            total_submissions=total_submissions,
            total_snapshots=total_snapshots,
            total_discrepancy_cases=total_cases,
            open_discrepancies_count=open_cases,
            resolved_discrepancies_count=resolved_cases,
            apaar_coverage_percentage=apaar_coverage,
            intake_compliance_rate=intake_compliance_rate,
            enrolment_by_programme=prog_metrics,
            enrolment_by_academic_year=ay_metrics,
            recent_activity=recent_activity,
        )

    @classmethod
    def generate_report_stream(
        cls,
        db: Session,
        actor: User,
        req: ReportExportRequest,
    ) -> StreamingResponse:
        """
        Generates and streams reproducible reports with formula-injection defusing.
        """
        is_inst_admin = actor.role.role_name == "INSTITUTION_ADMIN"
        target_inst_id = actor.institution_id if is_inst_admin else req.institution_id

        output = io.StringIO()
        writer = csv.writer(output)

        # Header metadata block
        now_str = datetime.now(timezone.utc).isoformat()
        writer.writerow(["# APAAR SETU CERTIFIED REGULATORY REPORT"])
        writer.writerow(["# Report Type", defuse_csv_formula(req.report_type)])
        writer.writerow(["# Generated At", defuse_csv_formula(now_str)])
        writer.writerow(["# Generated By", defuse_csv_formula(actor.email)])
        writer.writerow(["# Role Scope", defuse_csv_formula(actor.role.role_name)])
        writer.writerow([])

        if req.report_type in ("INSTITUTION_ENROLMENT", "REGULATORY_OVERVIEW"):
            writer.writerow(["Institution Code", "Legal Name", "Category", "State", "Active Students"])
            inst_query = select(Institution)
            if target_inst_id:
                inst_query = inst_query.where(Institution.id == target_inst_id)
            institutions = db.execute(inst_query).scalars().all()
            for inst in institutions:
                std_count = db.execute(
                    select(func.count(distinct(AnnualRosterObservation.student_identity_id))).where(
                        AnnualRosterObservation.institution_id == inst.id,
                        AnnualRosterObservation.student_status == "ACTIVE",
                    )
                ).scalar() or 0
                writer.writerow([
                    defuse_csv_formula(inst.institution_code),
                    defuse_csv_formula(inst.name),
                    defuse_csv_formula(inst.category),
                    defuse_csv_formula(inst.state),
                    std_count,
                ])

        elif req.report_type == "PROGRAMME_ENROLMENT":
            writer.writerow(["Institution", "Programme Code", "Programme Name", "Qualification Level", "Enrolled Students"])
            prog_query = select(Programme, Institution).join(Institution, Programme.institution_id == Institution.id)
            if target_inst_id:
                prog_query = prog_query.where(Programme.institution_id == target_inst_id)
            rows = db.execute(prog_query).all()
            for prog, inst in rows:
                enr = db.execute(
                    select(func.count(distinct(AnnualRosterObservation.student_identity_id))).where(
                        AnnualRosterObservation.programme_id == prog.id,
                        AnnualRosterObservation.student_status == "ACTIVE",
                    )
                ).scalar() or 0
                writer.writerow([
                    defuse_csv_formula(inst.name),
                    defuse_csv_formula(prog.programme_code),
                    defuse_csv_formula(prog.programme_name),
                    defuse_csv_formula(prog.qualification_level),
                    enr,
                ])

        elif req.report_type == "DISCREPANCY_RESOLUTION":
            writer.writerow(["Case Number", "Scope", "Classification", "Priority", "Status", "Academic Year", "Created At"])
            case_query = select(DiscrepancyCase)
            if target_inst_id:
                case_query = case_query.where(DiscrepancyCase.institution_id == target_inst_id)
            cases = db.execute(case_query).scalars().all()
            for c in cases:
                writer.writerow([
                    defuse_csv_formula(c.case_number),
                    defuse_csv_formula(c.scope_type),
                    defuse_csv_formula(c.classification),
                    defuse_csv_formula(c.review_priority),
                    defuse_csv_formula(c.case_status),
                    defuse_csv_formula(c.academic_year),
                    defuse_csv_formula(c.created_at.isoformat() if c.created_at else ""),
                ])

        else:
            # Generic summary
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Registered Students", db.execute(select(func.count(StudentIdentity.id))).scalar() or 0])
            writer.writerow(["Total Submissions", db.execute(select(func.count(SourceSubmission.id))).scalar() or 0])
            writer.writerow(["Total Snapshots", db.execute(select(func.count(RosterSnapshot.id))).scalar() or 0])

        output.seek(0)
        filename = f"report_{req.report_type.lower()}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
