"""
Audit Events API Endpoints
Provides access to audit logs for compliance and security
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from carpeta_common.audit_logger import AuditEvent, get_audit_events

logger = logging.getLogger(__name__)
router = APIRouter()


# Schemas
class AuditEventResponse(BaseModel):
    """Audit event response schema."""
    id: str
    timestamp: datetime
    event_type: str
    user_id: Optional[str]
    user_email: Optional[str]
    ip_address: Optional[str]
    service_name: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    status: str
    details: Optional[dict]
    changes: Optional[dict]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class AuditStatsResponse(BaseModel):
    """Audit statistics response."""
    total_events: int
    success_count: int
    failure_count: int
    events_by_action: dict[str, int]
    events_by_resource: dict[str, int]
    top_users: List[dict]


# Endpoints
@router.get("/audit/events", response_model=List[AuditEventResponse])
async def list_audit_events(
    user_id: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),  # Last N days
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List audit events with filters.
    
    Query Parameters:
    - user_id: Filter by user
    - resource_type: Filter by resource type (document, transfer, etc.)
    - resource_id: Filter by specific resource
    - action: Filter by action (create, update, delete, etc.)
    - status: Filter by status (success, failure)
    - days: Number of days to look back (default: 7)
    - limit: Max results (default: 100)
    - offset: Offset for pagination
    
    Returns:
        List of audit events
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    events = await get_audit_events(
        db=db,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        status=status,
        start_date=start_date,
        limit=limit,
        offset=offset
    )
    
    return events


@router.get("/audit/events/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    event_id: str,
    db: Session = Depends(get_db)
):
    """
    Get specific audit event by ID.
    
    Args:
        event_id: Audit event ID
    
    Returns:
        Audit event details
    """
    event = db.query(AuditEvent).filter(AuditEvent.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Audit event not found")
    
    return event


@router.get("/audit/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Get audit statistics.
    
    Args:
        days: Number of days to analyze
    
    Returns:
        Audit statistics
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all events in period
    events = await get_audit_events(
        db=db,
        start_date=start_date,
        limit=10000  # High limit for stats
    )
    
    # Calculate stats
    total_events = len(events)
    success_count = sum(1 for e in events if e.status == "success")
    failure_count = sum(1 for e in events if e.status == "failure")
    
    # Events by action
    events_by_action: dict[str, int] = {}
    for event in events:
        events_by_action[event.action] = events_by_action.get(event.action, 0) + 1
    
    # Events by resource type
    events_by_resource: dict[str, int] = {}
    for event in events:
        if event.resource_type:
            events_by_resource[event.resource_type] = events_by_resource.get(event.resource_type, 0) + 1
    
    # Top users
    user_counts: dict[str, int] = {}
    for event in events:
        if event.user_id:
            user_counts[event.user_id] = user_counts.get(event.user_id, 0) + 1
    
    top_users = [
        {"user_id": user_id, "event_count": count}
        for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]
    
    return AuditStatsResponse(
        total_events=total_events,
        success_count=success_count,
        failure_count=failure_count,
        events_by_action=events_by_action,
        events_by_resource=events_by_resource,
        top_users=top_users
    )


@router.get("/audit/user/{user_id}/history", response_model=List[AuditEventResponse])
async def get_user_audit_history(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get audit history for specific user.
    
    Args:
        user_id: User ID
        days: Number of days to look back
        limit: Max results
    
    Returns:
        User's audit history
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    events = await get_audit_events(
        db=db,
        user_id=user_id,
        start_date=start_date,
        limit=limit
    )
    
    return events


@router.get("/audit/resource/{resource_type}/{resource_id}", response_model=List[AuditEventResponse])
async def get_resource_audit_history(
    resource_type: str,
    resource_id: str,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get audit history for specific resource.
    
    Useful for document audit trail, transfer history, etc.
    
    Args:
        resource_type: Resource type (document, transfer, etc.)
        resource_id: Resource ID
        limit: Max results
    
    Returns:
        Resource audit history
    """
    events = await get_audit_events(
        db=db,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit
    )
    
    return events


@router.get("/audit/failures", response_model=List[AuditEventResponse])
async def get_audit_failures(
    hours: int = Query(24, ge=1, le=168),  # Last N hours
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get recent audit failures for security monitoring.
    
    Args:
        hours: Number of hours to look back
        limit: Max results
    
    Returns:
        Recent failures
    """
    start_date = datetime.utcnow() - timedelta(hours=hours)
    
    events = await get_audit_events(
        db=db,
        status="failure",
        start_date=start_date,
        limit=limit
    )
    
    return events

