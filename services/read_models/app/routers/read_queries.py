"""Read queries router - Optimized read models for CQRS."""

import logging
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ReadDocument, ReadTransfer
from app.services.redis_client import get_redis_client
from app.monitoring.azure_insights import get_app_insights
from app.config import Settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify basic functionality."""
    return {"message": "Read models service is working", "status": "ok"}


@router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """
    Get dashboard statistics for the frontend.
    
    Returns aggregated data for dashboard widgets.
    """
    try:
        logger.info("Fetching dashboard stats")
        
        # Get document counts by state
        total_docs_query = select(func.count(ReadDocument.id)).where(ReadDocument.is_deleted == False)
        signed_docs_query = select(func.count(ReadDocument.id)).where(
            ReadDocument.is_deleted == False,
            ReadDocument.state == "SIGNED"
        )
        
        # Get transfer counts
        pending_transfers_query = select(func.count(ReadTransfer.id)).where(
            ReadTransfer.status == "PENDING"
        )
        
        # Execute queries
        total_docs = await db.scalar(total_docs_query) or 0
        signed_docs = await db.scalar(signed_docs_query) or 0
        pending_transfers = await db.scalar(pending_transfers_query) or 0
        
        # Calculate shared documents (documents that have been transferred)
        shared_docs_query = select(func.count(ReadDocument.id)).where(
            ReadDocument.is_deleted == False,
            ReadDocument.state == "SIGNED",
            ReadDocument.hub_signature_ref.isnot(None)
        )
        shared_docs = await db.scalar(shared_docs_query) or 0
        
        return {
            "totalDocuments": total_docs,
            "signedDocuments": signed_docs,
            "pendingTransfers": pending_transfers,
            "sharedDocuments": shared_docs
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        # Return mock data as fallback
        return {
            "totalDocuments": 0,
            "signedDocuments": 0,
            "pendingTransfers": 0,
            "sharedDocuments": 0
        }


@router.get("/activities/recent")
async def get_recent_activities(
    limit: int = Query(10, le=50, description="Max results"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent activities for the frontend.
    
    Returns recent document uploads, signatures, and transfers.
    """
    try:
        logger.info(f"Fetching recent activities, limit={limit}")
        
        # Get recent documents
        recent_docs_query = select(ReadDocument).where(
            ReadDocument.is_deleted == False
        ).order_by(ReadDocument.created_at.desc()).limit(limit)
        
        recent_docs = await db.execute(recent_docs_query)
        documents = recent_docs.scalars().all()
        
        # Get recent transfers
        recent_transfers_query = select(ReadTransfer).order_by(
            ReadTransfer.created_at.desc()
        ).limit(limit)
        
        recent_transfers = await db.execute(recent_transfers_query)
        transfers = recent_transfers.scalars().all()
        
        # Format activities
        activities = []
        
        # Add document activities
        for doc in documents:
            activities.append({
                "id": f"doc_{doc.id}",
                "type": "document_uploaded",
                "description": f"Documento '{doc.title}' subido",
                "timestamp": doc.created_at.isoformat(),
                "citizen_id": str(doc.citizen_id),
                "document_id": doc.id
            })
            
            if doc.state == "SIGNED":
                activities.append({
                    "id": f"sign_{doc.id}",
                    "type": "document_signed",
                    "description": f"Documento '{doc.title}' firmado",
                    "timestamp": doc.signed_at.isoformat() if doc.signed_at else doc.updated_at.isoformat(),
                    "citizen_id": str(doc.citizen_id),
                    "document_id": doc.id
                })
        
        # Add transfer activities
        for transfer in transfers:
            activities.append({
                "id": f"transfer_{transfer.id}",
                "type": "transfer_sent" if transfer.status == "PENDING" else "transfer_received",
                "description": f"Transferencia {transfer.status.lower()}",
                "timestamp": transfer.created_at.isoformat(),
                "citizen_id": str(transfer.from_citizen_id),
                "transfer_id": transfer.id
            })
        
        # Sort by timestamp and limit
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]
        
    except Exception as e:
        logger.error(f"Error fetching recent activities: {e}")
        return []


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
    try:
        logger.info(f"Query read_documents: citizen_id={citizen_id}, state={state}, limit={limit}")
        
        # Simple query first to test
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
        
        # Prepare response
        response = {
            "documents": [
                {
                    "id": doc.id,
                    "citizen_id": doc.citizen_id,
                    "citizen_name": doc.citizen_name,
                    "filename": doc.filename,
                    "content_type": doc.content_type,
                    "title": doc.title,
                    "blob_name": doc.blob_name,
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
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error in get_documents: {e}")
        return {"error": str(e), "documents": [], "total": 0}


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
    
    # Try to get from Redis cache first
    settings = Settings()
    redis_client = await get_redis_client(settings)
    
    if redis_client:
        try:
            cached_result = await redis_client.get_cached_transfers_query(
                citizen_id, status, limit, offset
            )
            if cached_result:
                logger.info("✅ Returning cached transfers query result")
                return cached_result
        except Exception as e:
            logger.warning(f"⚠️ Redis cache error: {e}")
    
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
    
    # Prepare response
    response = {
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
    
    # Cache the result
    if redis_client:
        try:
            await redis_client.cache_transfers_query(citizen_id, status, limit, offset, response)
            logger.info("✅ Cached transfers query result")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache transfers query: {e}")
    
    return response


@router.get("/stats")
async def get_stats(
    citizen_id: int = Query(..., description="Citizen ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get quick stats for a citizen (CQRS optimized)."""
    
    # Try to get from Redis cache first
    settings = Settings()
    redis_client = await get_redis_client(settings)
    
    if redis_client:
        try:
            cached_result = await redis_client.get_cached_stats_query(citizen_id)
            if cached_result:
                logger.info("✅ Returning cached stats query result")
                return cached_result
        except Exception as e:
            logger.warning(f"⚠️ Redis cache error: {e}")
    
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
    
    # Prepare response
    response = {
        "citizen_id": citizen_id,
        "total_documents": doc_count,
        "authenticated_documents": auth_count,
        "total_transfers": transfer_count,
        "authentication_rate": (auth_count / doc_count * 100) if doc_count > 0 else 0
    }
    
    # Cache the result
    if redis_client:
        try:
            await redis_client.cache_stats_query(citizen_id, response)
            logger.info("✅ Cached stats query result")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache stats query: {e}")
    
    return response

