"""Approval Service for Regulatory Configuration Lifecycle, Amendment Lineage, and Quota Calculation."""

import uuid
import math
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, and_, text
from fastapi import HTTPException, status

from app.models import (
    User,
    ApprovalConfiguration,
    ApprovalCategoryAllocation,
)
from app.schemas.approval import (
    ApprovalConfigurationCreate,
    ApprovalConfigurationAmend,
    ApprovalConfigurationRevoke,
    ApprovalCategoryAllocationCreate,
)
from app.services.snapshot_service import SnapshotService

logger = logging.getLogger("apaar_setu.approval")

VALID_ROUNDING_METHODS = {"FLOOR", "CEILING", "ROUND_HALF_UP", "EXPLICIT_FIXED_CAP"}
VALID_ALLOCATION_TYPES = {"WITHIN_SANCTIONED_INTAKE", "ADDITIONAL_SUPERNUMERARY", "INDEPENDENT_CAP", "INFORMATIONAL_ONLY"}
VALID_ALLOCATION_BASES = {"PERCENTAGE", "FIXED_SEATS"}


def compute_seat_cap(
    basis: str,
    allocated_value: float,
    rounding_method: Optional[str],
    denominator: Optional[int],
) -> Tuple[Optional[int], Optional[str]]:
    """
    Deterministically computes integer seat cap according to policy rules and rounding configuration.
    Returns (calculated_cap, error_or_indeterminate_reason).
    """
    if basis == "FIXED_SEATS":
        return int(allocated_value), None

    if basis == "PERCENTAGE":
        if denominator is None:
            return None, "Denominator unestablished for percentage calculation"
        if not rounding_method or rounding_method not in VALID_ROUNDING_METHODS:
            return None, f"Missing or invalid rounding method: {rounding_method}"

        raw_val = float(denominator) * (float(allocated_value) / 100.0)
        if rounding_method == "FLOOR":
            return math.floor(raw_val), None
        elif rounding_method == "CEILING":
            return math.ceil(raw_val), None
        elif rounding_method == "ROUND_HALF_UP":
            d = Decimal(str(raw_val)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            return int(d), None
        elif rounding_method == "EXPLICIT_FIXED_CAP":
            return int(allocated_value), None

    return None, f"Unsupported allocation basis: {basis}"


class ApprovalService:
    """
    Manages statutory approval configurations, immutable amendment versioning,
    and category allocation matrices.
    """

    @classmethod
    def create_configuration(
        cls,
        db: Session,
        req: ApprovalConfigurationCreate,
        actor: User,
    ) -> ApprovalConfiguration:
        """
        Creates Version 1 of a statutory approval configuration with category allocations.
        Enforces tenant authorization and unique ACTIVE index.
        """
        if actor.role.role_name == "INSTITUTION_ADMIN" and req.institution_id != actor.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Cannot create approval configuration for external institution.",
            )

        if req.effective_to < req.effective_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date range: effective_to cannot be prior to effective_from.",
            )

        if req.approved_intake <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approved regular intake must be greater than zero.",
            )

        # 1. Acquire transaction advisory lock serializing concurrent creations for this programme and academic year
        lock_key = f"approval_config_create:{req.institution_id}:{req.programme_id}:{req.academic_year}"
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": lock_key},
        )

        # Check existing active configuration
        existing_active = db.execute(
            select(ApprovalConfiguration).where(
                ApprovalConfiguration.institution_id == req.institution_id,
                ApprovalConfiguration.programme_id == req.programme_id,
                ApprovalConfiguration.academic_year == req.academic_year,
                ApprovalConfiguration.status == "ACTIVE",
            )
        ).scalar_one_or_none()

        if existing_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An ACTIVE approval configuration already exists for this programme in academic year {req.academic_year}. Use the amendment workflow.",
            )

        now_utc = datetime.now(timezone.utc)
        config = ApprovalConfiguration(
            institution_id=req.institution_id,
            programme_id=req.programme_id,
            academic_year=req.academic_year,
            approved_intake=req.approved_intake,
            supernumerary_quota_percentage=req.supernumerary_quota_percentage,
            lateral_entry_quota_percentage=req.lateral_entry_quota_percentage,
            approval_reference=req.approval_reference,
            issuing_authority=req.issuing_authority,
            approval_letter_date=req.approval_letter_date,
            effective_from=req.effective_from,
            effective_to=req.effective_to,
            configuration_version=1,
            status="ACTIVE",
            created_by_user_id=actor.id,
            created_at=now_utc,
        )
        db.add(config)
        db.flush()

        # Add Category Allocations
        if req.category_allocations:
            for alloc_in in req.category_allocations:
                if alloc_in.allocation_type not in VALID_ALLOCATION_TYPES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid allocation type: {alloc_in.allocation_type}",
                    )
                if alloc_in.allocation_basis not in VALID_ALLOCATION_BASES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid allocation basis: {alloc_in.allocation_basis}",
                    )

                denom = req.approved_intake if alloc_in.denominator_basis == "SANCTIONED_INTAKE" else None
                calc_cap, _ = compute_seat_cap(
                    basis=alloc_in.allocation_basis,
                    allocated_value=alloc_in.allocated_value,
                    rounding_method=alloc_in.rounding_method,
                    denominator=denom,
                )

                alloc_record = ApprovalCategoryAllocation(
                    approval_configuration_id=config.id,
                    category_code=alloc_in.category_code.upper().strip(),
                    entry_level=alloc_in.entry_level,
                    allocation_type=alloc_in.allocation_type,
                    allocation_basis=alloc_in.allocation_basis,
                    allocated_value=alloc_in.allocated_value,
                    rounding_method=alloc_in.rounding_method,
                    denominator_basis=alloc_in.denominator_basis,
                    calculated_seat_cap=calc_cap,
                    policy_clause=alloc_in.policy_clause,
                    created_at=now_utc,
                )
                db.add(alloc_record)

        db.flush()

        # Cryptographically chained AuditEvent
        SnapshotService.record_chained_audit_event(
            db=db,
            actor_id=actor.id,
            action="APPROVAL_CONFIG_CREATED",
            entity_type="ApprovalConfiguration",
            entity_id=config.id,
            metadata_payload={
                "institution_id": str(config.institution_id),
                "programme_id": str(config.programme_id),
                "academic_year": config.academic_year,
                "version": 1,
                "approved_intake": config.approved_intake,
                "approval_reference": config.approval_reference,
            },
        )

        db.commit()
        db.refresh(config)
        return config

    @classmethod
    def amend_configuration(
        cls,
        db: Session,
        config_id: uuid.UUID,
        req: ApprovalConfigurationAmend,
        actor: User,
    ) -> ApprovalConfiguration:
        """
        Amends an active configuration by superseding it and spawning Version N+1.
        Acquires transaction-scoped row lock on the current record.
        Preserves complete historical audit trail and immutable lineage.
        """
        if not req.amendment_reason or len(req.amendment_reason.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amendment reason is mandatory and must be at least 10 characters long.",
            )

        # 1. Fetch current with exclusive row lock
        current_config = db.execute(
            select(ApprovalConfiguration)
            .where(ApprovalConfiguration.id == config_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not current_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval configuration {config_id} not found.",
            )

        # Tenancy check
        if actor.role.role_name == "INSTITUTION_ADMIN" and current_config.institution_id != actor.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Cannot amend approval configuration for external institution.",
            )

        if current_config.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot amend configuration with status '{current_config.status}'. Only ACTIVE configurations can be amended.",
            )

        effective_from = req.effective_from or current_config.effective_from
        effective_to = req.effective_to or current_config.effective_to
        if effective_to < effective_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date range: effective_to cannot be prior to effective_from.",
            )

        new_intake = req.approved_intake if req.approved_intake is not None else current_config.approved_intake
        if new_intake <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approved regular intake must be greater than zero.",
            )

        now_utc = datetime.now(timezone.utc)
        next_version = current_config.configuration_version + 1

        # 2. Mark current configuration as SUPERSEDED first to satisfy unique active index
        current_config.status = "SUPERSEDED"
        current_config.superseded_at = now_utc
        current_config.amended_by_user_id = actor.id
        current_config.amendment_reason = req.amendment_reason.strip()
        db.flush()

        # 3. Spawn Version N+1 as the new ACTIVE configuration
        new_config = ApprovalConfiguration(
            institution_id=current_config.institution_id,
            programme_id=current_config.programme_id,
            academic_year=current_config.academic_year,
            approved_intake=new_intake,
            supernumerary_quota_percentage=(
                req.supernumerary_quota_percentage
                if req.supernumerary_quota_percentage is not None
                else current_config.supernumerary_quota_percentage
            ),
            lateral_entry_quota_percentage=(
                req.lateral_entry_quota_percentage
                if req.lateral_entry_quota_percentage is not None
                else current_config.lateral_entry_quota_percentage
            ),
            approval_reference=req.approval_reference or current_config.approval_reference,
            issuing_authority=req.issuing_authority or current_config.issuing_authority,
            approval_letter_date=(
                req.approval_letter_date
                if req.approval_letter_date is not None
                else current_config.approval_letter_date
            ),
            effective_from=effective_from,
            effective_to=effective_to,
            configuration_version=next_version,
            status="ACTIVE",
            amendment_reason=req.amendment_reason.strip(),
            created_by_user_id=current_config.created_by_user_id,
            amended_by_user_id=actor.id,
            created_at=now_utc,
        )
        db.add(new_config)
        db.flush()

        # Link lineage
        current_config.superseded_by_id = new_config.id
        db.flush()

        # 4. Handle Allocations
        if req.category_allocations is not None:
            # New allocations explicitly provided
            for alloc_in in req.category_allocations:
                denom = new_intake if alloc_in.denominator_basis == "SANCTIONED_INTAKE" else None
                calc_cap, _ = compute_seat_cap(
                    basis=alloc_in.allocation_basis,
                    allocated_value=alloc_in.allocated_value,
                    rounding_method=alloc_in.rounding_method,
                    denominator=denom,
                )
                new_alloc = ApprovalCategoryAllocation(
                    approval_configuration_id=new_config.id,
                    category_code=alloc_in.category_code.upper().strip(),
                    entry_level=alloc_in.entry_level,
                    allocation_type=alloc_in.allocation_type,
                    allocation_basis=alloc_in.allocation_basis,
                    allocated_value=alloc_in.allocated_value,
                    rounding_method=alloc_in.rounding_method,
                    denominator_basis=alloc_in.denominator_basis,
                    calculated_seat_cap=calc_cap,
                    policy_clause=alloc_in.policy_clause,
                    created_at=now_utc,
                )
                db.add(new_alloc)
        else:
            # Clone allocations from current configuration
            old_allocs = db.execute(
                select(ApprovalCategoryAllocation).where(
                    ApprovalCategoryAllocation.approval_configuration_id == current_config.id
                )
            ).scalars().all()

            for old in old_allocs:
                denom = new_intake if old.denominator_basis == "SANCTIONED_INTAKE" else None
                calc_cap, _ = compute_seat_cap(
                    basis=old.allocation_basis,
                    allocated_value=float(old.allocated_value),
                    rounding_method=old.rounding_method,
                    denominator=denom,
                )
                cloned = ApprovalCategoryAllocation(
                    approval_configuration_id=new_config.id,
                    category_code=old.category_code,
                    entry_level=old.entry_level,
                    allocation_type=old.allocation_type,
                    allocation_basis=old.allocation_basis,
                    allocated_value=old.allocated_value,
                    rounding_method=old.rounding_method,
                    denominator_basis=old.denominator_basis,
                    calculated_seat_cap=calc_cap,
                    policy_clause=old.policy_clause,
                    created_at=now_utc,
                )
                db.add(cloned)

        db.flush()

        # 5. Record hash-chained AuditEvent
        SnapshotService.record_chained_audit_event(
            db=db,
            actor_id=actor.id,
            action="APPROVAL_CONFIG_AMENDED",
            entity_type="ApprovalConfiguration",
            entity_id=new_config.id,
            metadata_payload={
                "superseded_config_id": str(current_config.id),
                "superseded_version": current_config.configuration_version,
                "new_version": next_version,
                "institution_id": str(new_config.institution_id),
                "programme_id": str(new_config.programme_id),
                "academic_year": new_config.academic_year,
                "amendment_reason": req.amendment_reason.strip(),
            },
        )

        db.commit()
        db.refresh(new_config)
        return new_config

    @classmethod
    def revoke_configuration(
        cls,
        db: Session,
        config_id: uuid.UUID,
        req: ApprovalConfigurationRevoke,
        actor: User,
    ) -> ApprovalConfiguration:
        """
        Revokes an active configuration (e.g. regulatory withdrawal or suspension).
        """
        if not req.revocation_reason or len(req.revocation_reason.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Revocation reason is mandatory and must be at least 10 characters long.",
            )

        config = db.execute(
            select(ApprovalConfiguration)
            .where(ApprovalConfiguration.id == config_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval configuration {config_id} not found.",
            )

        if actor.role.role_name == "INSTITUTION_ADMIN" and config.institution_id != actor.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Cannot revoke approval configuration for external institution.",
            )

        if config.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot revoke configuration with status '{config.status}'. Only ACTIVE configurations can be revoked.",
            )

        config.status = "REVOKED"
        config.amendment_reason = req.revocation_reason.strip()
        config.amended_by_user_id = actor.id
        db.flush()

        SnapshotService.record_chained_audit_event(
            db=db,
            actor_id=actor.id,
            action="APPROVAL_CONFIG_REVOKED",
            entity_type="ApprovalConfiguration",
            entity_id=config.id,
            metadata_payload={
                "institution_id": str(config.institution_id),
                "programme_id": str(config.programme_id),
                "academic_year": config.academic_year,
                "version": config.configuration_version,
                "revocation_reason": req.revocation_reason.strip(),
            },
        )

        db.commit()
        db.refresh(config)
        return config

    @classmethod
    def get_active_configuration(
        cls,
        db: Session,
        institution_id: uuid.UUID,
        programme_id: uuid.UUID,
        academic_year: str,
    ) -> Optional[ApprovalConfiguration]:
        """
        Queries the current ACTIVE approval configuration with its category allocations eagerly loaded.
        """
        stmt = (
            select(ApprovalConfiguration)
            .options(selectinload(ApprovalConfiguration.category_allocations))
            .where(
                ApprovalConfiguration.institution_id == institution_id,
                ApprovalConfiguration.programme_id == programme_id,
                ApprovalConfiguration.academic_year == academic_year,
                ApprovalConfiguration.status == "ACTIVE",
            )
        )
        return db.execute(stmt).scalar_one_or_none()

    @classmethod
    def get_configuration_history(
        cls,
        db: Session,
        institution_id: uuid.UUID,
        programme_id: uuid.UUID,
        academic_year: str,
        actor: User,
    ) -> List[ApprovalConfiguration]:
        """
        Returns full version lineage of configurations for a programme and academic year,
        ordered by configuration_version descending.
        """
        if actor.role.role_name == "INSTITUTION_ADMIN" and institution_id != actor.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Access to configuration history for external institution forbidden.",
            )

        stmt = (
            select(ApprovalConfiguration)
            .options(selectinload(ApprovalConfiguration.category_allocations))
            .where(
                ApprovalConfiguration.institution_id == institution_id,
                ApprovalConfiguration.programme_id == programme_id,
                ApprovalConfiguration.academic_year == academic_year,
            )
            .order_by(ApprovalConfiguration.configuration_version.desc())
        )
        return list(db.execute(stmt).scalars().all())

    @classmethod
    def list_configurations(
        cls,
        db: Session,
        actor: User,
        institution_id: Optional[uuid.UUID] = None,
        programme_id: Optional[uuid.UUID] = None,
        academic_year: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[ApprovalConfiguration]:
        """
        Lists configurations with multi-tenant filtering.
        """
        stmt = (
            select(ApprovalConfiguration)
            .options(selectinload(ApprovalConfiguration.category_allocations))
            .order_by(ApprovalConfiguration.created_at.desc())
        )

        if actor.role.role_name == "INSTITUTION_ADMIN":
            stmt = stmt.where(ApprovalConfiguration.institution_id == actor.institution_id)
        elif institution_id:
            stmt = stmt.where(ApprovalConfiguration.institution_id == institution_id)

        if programme_id:
            stmt = stmt.where(ApprovalConfiguration.programme_id == programme_id)
        if academic_year:
            stmt = stmt.where(ApprovalConfiguration.academic_year == academic_year)
        if status_filter:
            stmt = stmt.where(ApprovalConfiguration.status == status_filter)

        return list(db.execute(stmt).scalars().all())
