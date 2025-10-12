"""Read queries router - Optimized read models for CQRS."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ReadDocument, ReadTransfer

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/documents")
async def get_documents(
    citizen_id: Optional[int] = Query(None, description="Filter by citizen ID"),
    state: Optional[str] = Query(None, description="Filter by state (UNSIGNED/SIGNED)"),
    limit: int = Query(50, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get optimized read model for documents.
    
    Returns denormalized data for fast queries (no JOINs).
    Data is projected from events: document.uploaded, document.authenticated, citizen.registered
    """
    logger.info(f"Query read_documents: citizen_id={citizen_id}, state={state}, limit={limit}")
    
    # Build query
    query = select(ReadDocument).where(ReadDocument.is_deleted == False)
    
    if citizen_id:
        query = query.where(ReadDocument.citizen_id == citizen_id)
    
    if state:
        query = query.where(ReadDocument.status == state)
    
    # Order by upload date (newest first)
    query = query.order_by(ReadDocument.uploaded_at.desc())
    
    # Pagination
    query = query.limit(limit).offset(offset)
    
    # Execute
    result = await db.execute(query)
    documents = result.scalars().all()
    
    # Count total (for pagination)
    count_query = select(func.count()).select_from(ReadDocument).where(ReadDocument.is_deleted == False)
    if citizen_id:
        count_query = count_query.where(ReadDocument.citizen_id == citizen_id)
    if state:
        count_query = count_query.where(ReadDocument.status == state)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # TODO: Cache results in Redis with TTL=300s
    # cache_key = f"read:docs:{citizen_id}:{state}:{limit}:{offset}"
    
    return {
        "documents": [
            {
                "id": doc.id,
                "citizen_id": doc.citizen_id,
                "citizen_name": doc.citizen_name,  # Denormalized!
                "filename": doc.filename,
                "content_type": doc.content_type,
                "title": doc.title,
                "sha256_hash": doc.sha256_hash,
                "is_authenticated": doc.is_authenticated,
                "authenticated_at": doc.authenticated_at.isoformat() if doc.authenticated_at else None,
                "status": doc.status,
                "uploaded_at": doc.uploaded_at.isoformat(),
            }
            for doc in documents
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + len(documents)) < total
    }


@router.get("/transfers")
async def get_transfers(
    citizen_id: Optional[int] = Query(None, description="Filter by citizen ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Get optimized read model for transfers.
    
    Returns denormalized data for fast queries.
    Data is projected from events: transfer.requested, transfer.confirmed
    """
    logger.info(f"Query read_transfers: citizen_id={citizen_id}, status={status}")
    
    # Build query
    query = select(ReadTransfer)
    
    if citizen_id:
        query = query.where(ReadTransfer.citizen_id == citizen_id)
    
    if status:
        query = query.where(ReadTransfer.status == status)
    
    # Order by requested date (newest first)
    query = query.order_by(ReadTransfer.requested_at.desc())
    
    # Pagination
    query = query.limit(limit).offset(offset)
    
    # Execute
    result = await db.execute(query)
    transfers = result.scalars().all()
    
    # Count total
    count_query = select(func.count()).select_from(ReadTransfer)
    if citizen_id:
        count_query = count_query.where(ReadTransfer.citizen_id == citizen_id)
    if status:
        count_query = count_query.where(ReadTransfer.status == status)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    return {
        "transfers": [
            {
                "id": t.id,
                "citizen_id": t.citizen_id,
                "citizen_name": t.citizen_name,  # Denormalized!
                "source_operator_id": t.source_operator_id,
                "source_operator_name": t.source_operator_name,
                "destination_operator_id": t.destination_operator_id,
                "destination_operator_name": t.destination_operator_name,
                "status": t.status,
                "success": t.success,
                "document_count": t.document_count,
                "requested_at": t.requested_at.isoformat(),
                "confirmed_at": t.confirmed_at.isoformat() if t.confirmed_at else None,
            }
            for t in transfers
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + len(transfers)) < total
    }


@router.get("/stats")
async def get_stats(
    citizen_id: int = Query(..., description="Citizen ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get quick stats for a citizen (CQRS optimized)."""
    
    # Count documents (single query, no JOINs)
    doc_count_query = select(func.count()).select_from(ReadDocument).where(
        ReadDocument.citizen_id == citizen_id,
        ReadDocument.is_deleted == False
    )
    doc_count = await db.scalar(doc_count_query)
    
    # Count authenticated documents
    auth_count_query = select(func.count()).select_from(ReadDocument).where(
        ReadDocument.citizen_id == citizen_id,
        ReadDocument.is_authenticated == True,
        ReadDocument.is_deleted == False
    )
    auth_count = await db.scalar(auth_count_query)
    
    # Count transfers
    transfer_count_query = select(func.count()).select_from(ReadTransfer).where(
        ReadTransfer.citizen_id == citizen_id
    )
    transfer_count = await db.scalar(transfer_count_query)
    
    return {
        "citizen_id": citizen_id,
        "total_documents": doc_count,
        "authenticated_documents": auth_count,
        "total_transfers": transfer_count,
        "authentication_rate": (auth_count / doc_count * 100) if doc_count > 0 else 0
    }

