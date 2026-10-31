"""Audit Log API Router for Cryptographically Chained Ledger Inspection."""

import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models import User, AuditEvent

router = APIRouter(prefix="/audit", tags=["Tamper-Evident Audit Ledger"])


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    ip_address: Optional[str] = None
    metadata_payload: Dict[str, Any] = {}
    previous_event_hash: str
    event_hash: str
    timestamp: datetime


class PaginatedAuditResponse(BaseModel):
    items: List[AuditEventResponse]
    total: int


@router.get("/events", response_model=PaginatedAuditResponse, status_code=status.HTTP_200_OK)
def list_audit_events(
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves chronological tamper-evident audit ledger events protected by SHA-256 hash chaining.
    """
    stmt = select(AuditEvent, User.name.label("actor_name")).outerjoin(
        User, AuditEvent.actor_id == User.id
    )

    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditEvent.action == action)

    stmt = stmt.order_by(desc(AuditEvent.timestamp)).limit(limit)
    rows = db.execute(stmt).all()

    items = [
        AuditEventResponse(
            id=ev.id,
            actor_id=ev.actor_id,
            actor_name=actor_name or "System Process",
            action=ev.action,
            entity_type=ev.entity_type,
            entity_id=ev.entity_id,
            ip_address=ev.ip_address,
            metadata_payload=ev.metadata_payload or {},
            previous_event_hash=ev.previous_event_hash,
            event_hash=ev.event_hash,
            timestamp=ev.timestamp,
        )
        for ev, actor_name in rows
    ]

    return PaginatedAuditResponse(items=items, total=len(items))

