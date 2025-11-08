"""
Session Management Endpoints
Handles user sessions stored in Redis
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.session_store import (
    SessionNotFound,
    SessionStoreError,
    session_store,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ========================================
# Schemas
# ========================================

class SessionCreate(BaseModel):
    """Create session request"""
    user_id: str
    email: str
    name: Optional[str] = None
    roles: list[str] = []
    permissions: list[str] = []


class SessionResponse(BaseModel):
    """Session response"""
    session_id: str
    user_id: str
    email: str
    name: Optional[str]
    roles: list[str]
    permissions: list[str]
    created_at: datetime
    expires_at: datetime
    is_active: bool


# ========================================
# Endpoints
# ========================================


def _to_response(record) -> SessionResponse:
    """Convert SessionRecord to response model."""
    return SessionResponse(
        session_id=record.session_id,
        user_id=record.user_id,
        email=record.email,
        name=record.name,
        roles=record.roles,
        permissions=record.permissions,
        created_at=record.created_at if isinstance(record.created_at, datetime) else datetime.fromisoformat(str(record.created_at)),
        expires_at=record.expires_at if isinstance(record.expires_at, datetime) else datetime.fromisoformat(str(record.expires_at)),
        is_active=record.is_active,
    )


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(data: SessionCreate):
    """
    Create new session
    
    Sessions are stored in Redis with TTL
    """
    try:
        record = await session_store.create_session(data.model_dump())
    except SessionStoreError as exc:
        logger.error("Failed to create session: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to create session",
        ) from exc

    logger.info("Session %s created for user %s", record.session_id, data.user_id)
    return _to_response(record)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Get session by ID
    """
    try:
        record = await session_store.get_session(session_id)
        return _to_response(record)
    except SessionNotFound as exc:
        logger.debug("Session %s not found", session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        ) from exc
    except SessionStoreError as exc:
        logger.error("Error retrieving session %s: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve session",
        ) from exc


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    Delete session (logout)
    """
    try:
        await session_store.delete_session(session_id)
    except SessionNotFound as exc:
        logger.debug("Attempted to delete missing session %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        ) from exc
    except SessionStoreError as exc:
        logger.error("Error deleting session %s: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to delete session",
        ) from exc

    logger.info("Session %s deleted", session_id)
    return {"message": "Session deleted", "session_id": session_id}


@router.post("/{session_id}/refresh")
async def refresh_session(session_id: str):
    """
    Refresh session (extend TTL)
    """
    try:
        record = await session_store.refresh_session(session_id)
    except SessionNotFound as exc:
        logger.debug("Attempted to refresh missing session %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        ) from exc
    except SessionStoreError as exc:
        logger.error("Error refreshing session %s: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to refresh session",
        ) from exc

    logger.info("Session %s refreshed", session_id)
    return {
        "message": "Session refreshed",
        "session_id": session_id,
        "expires_at": record.expires_at.isoformat(),
    }

