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
        
        # For now, return empty list or mock data
        # TODO: Implement actual notification storage and retrieval
        # This could query a notifications table or event log
        
        # Check if citizen exists (optional validation)
        try:
            result = await db.execute(
                text("SELECT id, name, email FROM citizens WHERE id = :citizen_id"),
                {"citizen_id": citizen_id}
            )
            citizen = result.fetchone()
            
            if not citizen:
                logger.warning(f"Citizen {citizen_id} not found, returning empty notifications")
                return []
        except Exception as e:
            logger.warning(f"Could not validate citizen existence: {e}")
            # Continue anyway, return empty list
        
        # Return empty list for now
        # Future: Query notifications table or event log filtered by citizen_id
        notifications = []
        
        logger.info(f"Returning {len(notifications)} notifications for citizen_id={citizen_id}")
        return notifications
        
    except Exception as e:
        logger.error(f"Error fetching notifications for citizen_id={citizen_id}: {e}", exc_info=True)
        # Return empty list on error instead of raising exception
        return []

