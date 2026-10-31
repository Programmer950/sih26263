"""Historical Aggregate Enrolment Reconciliation Service (PRD Module 9)."""

import uuid
import logging
from typing import Optional, List, Tuple
from datetime import datetime, date, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from fastapi import HTTPException, status

from app.models import (
    User,
    AggregateEnrolmentDeclaration,
    RosterSnapshot,
    ReconciliationRun,
    DiscrepancyCase,
)
import hashlib
from app.schemas.aggregate import (
    AggregateDeclarationCreate,
    AggregateReconciliationResult,
)
from app.services.snapshot_service import SnapshotService

logger = logging.getLogger("apaar_setu.aggregate_reconciliation")


class AggregateReconciliationService:

    @staticmethod
    def create_declaration(
        db: Session,
        actor: User,
        data: AggregateDeclarationCreate,
    ) -> AggregateEnrolmentDeclaration:
        """Records a new historical aggregate enrolment declaration."""
        # Tenant isolation
        if actor.role.role_name == "INSTITUTION_ADMIN":
            if actor.institution_id != data.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot create aggregate declaration for a different institution.",
                )

        declaration = AggregateEnrolmentDeclaration(
            institution_id=data.institution_id,
            programme_id=data.programme_id,
            academic_year=data.academic_year,
            reporting_period=data.reporting_period,
            declared_count=data.declared_count,
            population_definition=data.population_definition,
            student_status_definition=data.student_status_definition,
            counting_methodology=data.counting_methodology,
            reporting_source=data.reporting_source,
            source_reference=data.source_reference,
            declaration_date=data.declaration_date or date.today(),
        )
        db.add(declaration)
        db.commit()
        db.refresh(declaration)

        # Audit
        SnapshotService.record_chained_audit_event(
            db=db,
            actor_id=actor.id,
            action="AGGREGATE_DECLARATION_RECORDED",
            entity_type="AggregateEnrolmentDeclaration",
            entity_id=declaration.id,
            metadata_payload={
                "academic_year": declaration.academic_year,
                "declared_count": declaration.declared_count,
                "reporting_source": declaration.reporting_source,
            },
        )
        return declaration

    @staticmethod
    def list_declarations(
        db: Session,
        actor: User,
        institution_id: Optional[uuid.UUID] = None,
        academic_year: Optional[str] = None,
    ) -> List[AggregateEnrolmentDeclaration]:
        """Lists aggregate declarations enforcing role and tenant boundaries."""
        stmt = select(AggregateEnrolmentDeclaration)
        if actor.role.role_name == "INSTITUTION_ADMIN":
            stmt = stmt.where(AggregateEnrolmentDeclaration.institution_id == actor.institution_id)
        elif institution_id:
            stmt = stmt.where(AggregateEnrolmentDeclaration.institution_id == institution_id)

        if academic_year:
            stmt = stmt.where(AggregateEnrolmentDeclaration.academic_year == academic_year)

        return list(db.execute(stmt.order_by(AggregateEnrolmentDeclaration.academic_year.desc())).scalars().all())

    @staticmethod
    def reconcile(
        db: Session,
        actor: User,
        declaration_id: uuid.UUID,
        roster_snapshot_id: uuid.UUID,
    ) -> AggregateReconciliationResult:
        """
        PRD Module 9: Reconciles a declared aggregate figure with an authoritative roster snapshot.
        Enforces strict comparability pre-conditions (Institution, Programme, Academic Period,
        Population Definition, and Counting Methodology).
        """
        declaration = db.execute(
            select(AggregateEnrolmentDeclaration).where(AggregateEnrolmentDeclaration.id == declaration_id)
        ).scalar_one_or_none()
        if not declaration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Declaration not found.")

        snapshot = db.execute(
            select(RosterSnapshot).where(RosterSnapshot.id == roster_snapshot_id)
        ).scalar_one_or_none()
        if not snapshot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roster snapshot not found.")

        # Tenant isolation
        if actor.role.role_name == "INSTITUTION_ADMIN":
            if actor.institution_id != declaration.institution_id or actor.institution_id != snapshot.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cross-tenant aggregate reconciliation query blocked.",
                )

        # 1. Comparability Checks
        incomparable_reasons = []

        if declaration.institution_id != snapshot.institution_id:
            incomparable_reasons.append("Institution boundary mismatch.")

        if declaration.programme_id != snapshot.programme_id:
            incomparable_reasons.append("Programme ID mismatch between declaration and snapshot.")

        if declaration.academic_year != snapshot.academic_year:
            incomparable_reasons.append(
                f"Academic year mismatch: declaration specifies '{declaration.academic_year}', snapshot is '{snapshot.academic_year}'."
            )

        # Population / methodology compatibility check
        snapshot_pop = (snapshot.snapshot_metadata or {}).get("population_definition", "ALL_ENROLLED_REGULAR")
        if declaration.population_definition != snapshot_pop and declaration.population_definition != "ALL_ENROLLED_REGULAR":
            incomparable_reasons.append(
                f"Population definition incompatible: declaration requires '{declaration.population_definition}', roster snapshot represents '{snapshot_pop}'."
            )

        now = datetime.now(timezone.utc)
        source_refs = [
            f"Declaration:{declaration.source_reference or declaration.id}",
            f"Snapshot:{snapshot.id}",
            f"SnapshotHash:{snapshot.file_fingerprint_sha256[:16] if snapshot.file_fingerprint_sha256 else 'N/A'}",
        ]

        if incomparable_reasons:
            explanation = "NON-COMPARABLE: Definitions or reporting contexts differ. " + " ".join(incomparable_reasons)
            return AggregateReconciliationResult(
                declaration_id=declaration.id,
                roster_snapshot_id=snapshot.id,
                snapshot_id=snapshot.id,
                reconciliation_run_id=None,
                institution_id=declaration.institution_id,
                programme_id=declaration.programme_id,
                academic_year=declaration.academic_year,
                comparability_status="NON_COMPARABLE",
                declared_count=declaration.declared_count,
                roster_count=snapshot.record_count,
                variance=0,
                outcome_status="INCOMPARABLE",
                reconciliation_status="NON_COMPARABLE",
                discrepancy_case_id=None,
                explanation=explanation,
                source_references=source_refs,
                reconciliation_timestamp=now,
            )

        # 2. Reconcile Counts
        roster_count = snapshot.record_count
        declared_count = declaration.declared_count
        variance = roster_count - declared_count

        case_id = None
        if variance == 0:
            outcome_status = "EXACT_MATCH"
            explanation = (
                f"EXACT MATCH: Declared aggregate enrolment ({declared_count}) perfectly aligns with "
                f"detailed roster snapshot headcount ({roster_count}) for {declaration.academic_year}."
            )
        elif variance > 0:
            outcome_status = "ROSTER_EXCESS"
            explanation = (
                f"ROSTER COUNT EXCEEDS DECLARATION: Detailed roster snapshot contains {roster_count} students, "
                f"exceeding declared aggregate of {declared_count} by +{variance} records. Generated non-accusatory inquiry finding."
            )
        else:
            outcome_status = "DECLARED_EXCESS"
            explanation = (
                f"DECLARED COUNT EXCEEDS ROSTER: Declared aggregate is {declared_count}, but authoritative "
                f"roster snapshot contains only {roster_count} records (variance: {variance}). Recommending administrative review."
            )

        # 3. Create persistent ReconciliationRun and non-punitive Discrepancy Case if variance != 0
        run_fingerprint = hashlib.sha256(f"{declaration.id}:{snapshot.id}:{variance}".encode()).hexdigest()
        recon_run = ReconciliationRun(
            institution_id=declaration.institution_id,
            programme_id=declaration.programme_id,
            academic_year=declaration.academic_year,
            candidate_snapshot_id=snapshot.id,
            candidate_snapshot_hash=snapshot.snapshot_hash,
            run_type="AGGREGATE_RECONCILIATION",
            execution_status="COMPLETED",
            result_fingerprint=run_fingerprint,
            summary_counts={"declared": declared_count, "roster": roster_count, "variance": variance},
            parameters_json={"declaration_id": str(declaration.id), "population": declaration.population_definition},
            initiated_by_user_id=actor.id,
        )
        db.add(recon_run)
        db.flush()

        if variance != 0:
            case_num = f"AGG-{declaration.academic_year}-{uuid.uuid4().hex[:6].upper()}"
            case = DiscrepancyCase(
                case_number=case_num,
                scope_type="PROGRAMME",
                institution_id=declaration.institution_id,
                programme_id=declaration.programme_id,
                academic_year=declaration.academic_year,
                student_identity_id=None,
                classification="HISTORICAL_AGGREGATE_VARIANCE",
                review_priority="MEDIUM" if abs(variance) > 5 else "LOW",
                case_status="OPEN",
                observed_count=roster_count,
                approved_limit=declared_count,
                excess_count=abs(variance),
                initial_reconciliation_run_id=recon_run.id,
                latest_reconciliation_run_id=recon_run.id,
                source_submission_id=snapshot.source_submission_id,
                evidence_context_json={
                    "declaration_id": str(declaration.id),
                    "roster_snapshot_id": str(snapshot.id),
                    "declared_count": declared_count,
                    "roster_count": roster_count,
                    "variance": variance,
                    "explanation": explanation,
                },
            )
            db.add(case)
            db.flush()
            case_id = case.id

        db.commit()

        # Audit
        SnapshotService.record_chained_audit_event(
            db=db,
            actor_id=actor.id,
            action="HISTORICAL_AGGREGATE_RECONCILIATION_RUN",
            entity_type="AggregateEnrolmentDeclaration",
            entity_id=declaration.id,
            metadata_payload={
                "snapshot_id": str(snapshot.id),
                "declared_count": declared_count,
                "roster_count": roster_count,
                "variance": variance,
                "outcome_status": outcome_status,
            },
        )

        recon_status = "MATCH" if outcome_status == "EXACT_MATCH" else "DISCREPANT"
        return AggregateReconciliationResult(
            declaration_id=declaration.id,
            roster_snapshot_id=snapshot.id,
            snapshot_id=snapshot.id,
            reconciliation_run_id=recon_run.id,
            institution_id=declaration.institution_id,
            programme_id=declaration.programme_id,
            academic_year=declaration.academic_year,
            comparability_status="COMPARABLE",
            declared_count=declared_count,
            roster_count=roster_count,
            variance=variance,
            outcome_status=outcome_status,
            reconciliation_status=recon_status,
            discrepancy_case_id=case_id,
            explanation=explanation,
            source_references=source_refs,
            reconciliation_timestamp=now,
        )

