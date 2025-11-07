"""API routers for Notification Service."""

import logging
from typing import Annotated, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "notification"
    }


@router.get("/stats")
async def get_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get notification statistics (future enhancement)."""
    # TODO: Implement notification stats
    return {
        "status": "ok",
        "service": "notification",
        "stats": {
            "total_notifications_sent": 0,
            "emails_sent": 0,
            "events_processed": 0
        }
    }


@router.get("/user/{citizen_id}")
async def get_user_notifications(
    citizen_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[Dict[str, Any]]:
    """Get notifications for a specific citizen.
    
    Args:
        citizen_id: Citizen ID to get notifications for
        db: Database session
        
    Returns:
        List of notifications for the citizen
    """
    try:
        logger.info(f"Fetching notifications for citizen_id={citizen_id}")
        
        resolved_citizen_id = await _resolve_citizen_id(db, citizen_id)
        if not resolved_citizen_id:
            logger.warning(f"Citizen {citizen_id} not found, returning empty notifications")
            return []
        
        result = await db.execute(
            text("""
                SELECT id, event_type, title, message, metadata, is_read, created_at
                FROM notifications
                WHERE citizen_id = :citizen_id
                ORDER BY created_at DESC
                LIMIT 100
            """),
            {"citizen_id": resolved_citizen_id},
        )
        rows = result.mappings().all()
        
        notifications = []
        for row in rows:
            metadata = row.get("metadata")
            notifications.append({
                "id": row["id"],
                "event_type": row["event_type"],
                "title": row["title"],
                "message": row["message"],
                "metadata": metadata if isinstance(metadata, dict) else metadata,
                "is_read": row["is_read"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            })
        
        logger.info(f"Returning {len(notifications)} notifications for citizen_id={citizen_id}")
        return notifications
        
    except Exception as e:
        logger.error(f"Error fetching notifications for citizen_id={citizen_id}: {e}", exc_info=True)
        # Return empty list on error instead of raising exception
        return []


async def _resolve_citizen_id(db: AsyncSession, identifier: str) -> str | None:
    """Resolve incoming identifier (user id or citizen id) to citizen document id."""
    if not identifier:
        return None
    
    # First, check if identifier matches a citizen.id (document)
    citizen_query = await db.execute(
        text("SELECT id FROM citizens WHERE id = :cid LIMIT 1"),
        {"cid": identifier},
    )
    citizen = citizen_query.scalar_one_or_none()
    if citizen:
        return citizen
    
    # Next, attempt to resolve via users table (user.id -> citizen_id)
    user_query = await db.execute(
        text("""
            SELECT citizen_id, email
            FROM users
            WHERE CAST(id AS TEXT) = CAST(:uid AS TEXT)
            LIMIT 1
        """),
        {"uid": identifier},
    )
    user_row = user_query.fetchone()
    if user_row and user_row.citizen_id:
        return str(user_row.citizen_id)
    
    # If user exists without citizen_id, try resolving via email
    if user_row and user_row.email:
        email_lookup = await db.execute(
            text("""
                SELECT id FROM citizens
                WHERE LOWER(email) = LOWER(:email)
                LIMIT 1
            """),
            {"email": user_row.email},
        )
        email_row = email_lookup.fetchone()
        if email_row and email_row.id:
            return str(email_row.id)
    
    return None

