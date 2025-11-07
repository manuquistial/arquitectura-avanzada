"""API routers for Metadata Service."""

import logging
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import DocumentMetadata
from app.schemas import (
    DocumentMetadataResponse,
    DocumentMetadataListResponse,
    MetadataSearchRequest,
    MetadataSearchResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


async def _get_document_count(citizen_id: str, db: AsyncSession) -> int:
    """Get document count for a citizen."""
    try:
        result = await db.execute(
            select(DocumentMetadata)
            .where(DocumentMetadata.citizen_id == citizen_id)
            .where(DocumentMetadata.is_deleted == False)
        )
        return len(result.scalars().all())
    except Exception:
        return 0


@router.get("/documents/{document_id}", response_model=DocumentMetadataResponse)
async def get_document_metadata(
    document_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentMetadataResponse:
    """Get complete metadata for a document."""
    logger.info(f"Getting metadata for document {document_id}")
    
    try:
        result = await db.execute(
            select(DocumentMetadata).where(DocumentMetadata.id == document_id)
        )
        metadata = result.scalar_one_or_none()
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        return DocumentMetadataResponse.model_validate(metadata)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document metadata"
        )


@router.get("/documents/citizen/{citizen_id}", response_model=DocumentMetadataListResponse)
async def get_citizen_documents(
    citizen_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_deleted: bool = Query(default=False, description="Include deleted documents"),
) -> DocumentMetadataListResponse:
    """Get all documents metadata for a citizen."""
    logger.info(f"Getting documents metadata for citizen {citizen_id}")
    
    try:
        query = select(DocumentMetadata).where(DocumentMetadata.citizen_id == citizen_id)
        
        if not include_deleted:
            query = query.where(DocumentMetadata.is_deleted == False)
        
        query = query.order_by(DocumentMetadata.created_at.desc())
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return DocumentMetadataListResponse(
            documents=[DocumentMetadataResponse.model_validate(doc) for doc in documents],
            total=len(documents),
            citizen_id=citizen_id
        )
        
    except Exception as e:
        logger.error(f"Error getting citizen documents metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get citizen documents metadata"
        )


@router.post("/search", response_model=MetadataSearchResponse)
async def search_documents(
    request: MetadataSearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MetadataSearchResponse:
    """Search documents by metadata."""
    logger.info(f"Searching documents: query={request.query}, citizen_id={request.citizen_id}")
    
    try:
        query = select(DocumentMetadata).where(DocumentMetadata.is_deleted == False)
        
        # Filter by citizen_id if provided
        if request.citizen_id:
            query = query.where(DocumentMetadata.citizen_id == request.citizen_id)
        
        # Filter by state if provided
        if request.state:
            query = query.where(DocumentMetadata.state == request.state)
        
        # Filter by content_type if provided
        if request.content_type:
            query = query.where(DocumentMetadata.content_type == request.content_type)
        
        # Text search in title and description (basic)
        if request.query:
            search_term = f"%{request.query}%"
            query = query.where(
                or_(
                    DocumentMetadata.title.ilike(search_term),
                    DocumentMetadata.description.ilike(search_term),
                    DocumentMetadata.filename.ilike(search_term)
                )
            )
        
        # Get total count
        count_result = await db.execute(select(DocumentMetadata).where(query.whereclause))
        total = len(count_result.scalars().all())
        
        # Apply pagination
        query = query.offset(request.offset).limit(request.limit)
        query = query.order_by(DocumentMetadata.created_at.desc())
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return MetadataSearchResponse(
            documents=[DocumentMetadataResponse.model_validate(doc) for doc in documents],
            total=total,
            limit=request.limit,
            offset=request.offset
        )
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search documents"
        )


@router.get("/sync/status/{citizen_id}")
async def get_sync_status(
    citizen_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get sync status for a citizen (last document upload timestamp).
    
    This endpoint is called by MinTIC Client service.
    """
    logger.info(f"Getting sync status for citizen {citizen_id}")
    
    try:
        result = await db.execute(
            select(DocumentMetadata)
            .where(DocumentMetadata.citizen_id == citizen_id)
            .where(DocumentMetadata.is_deleted == False)
            .order_by(DocumentMetadata.created_at.desc())
            .limit(1)
        )
        latest_doc = result.scalar_one_or_none()
        
        if latest_doc:
            doc_count = await _get_document_count(citizen_id, db)
            return {
                "citizen_id": citizen_id,
                "last_sync": latest_doc.created_at.isoformat(),
                "last_document_id": latest_doc.id,
                "document_count": doc_count
            }
        else:
            return {
                "citizen_id": citizen_id,
                "last_sync": None,
                "last_document_id": None,
                "document_count": 0
            }
            
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sync status"
        )



