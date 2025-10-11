"""Metadata API router."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import DocumentMetadata
from app.schemas import DocumentListResponse, DocumentResponse, SearchResponse, SearchResult

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    citizen_id: int = Query(..., description="Citizen ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List documents for a citizen."""
    logger.info(f"Listing documents for citizen {citizen_id}")
    
    try:
        # Count total documents
        count_query = select(func.count(DocumentMetadata.id)).where(
            DocumentMetadata.citizen_id == citizen_id,
            DocumentMetadata.is_deleted == False
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Get documents
        query = select(DocumentMetadata).where(
            DocumentMetadata.citizen_id == citizen_id,
            DocumentMetadata.is_deleted == False
        ).offset(skip).limit(limit).order_by(DocumentMetadata.created_at.desc())
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(doc) for doc in documents],
            total=total
        )
    
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents"
        )


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., min_length=1, description="Search query"),
    citizen_id: int | None = Query(None, description="Filter by citizen ID"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search documents using PostgreSQL full-text search.
    
    In production, this would use OpenSearch/Elasticsearch for better performance.
    For now, using PostgreSQL ILIKE as fallback.
    """
    logger.info(f"Searching documents: query='{q}', citizen_id={citizen_id}")
    
    try:
        # Build query
        query_builder = select(DocumentMetadata).where(
            DocumentMetadata.is_deleted == False
        )
        
        # Add text search (simple ILIKE, in production use full-text search)
        search_pattern = f"%{q}%"
        query_builder = query_builder.where(
            (DocumentMetadata.filename.ilike(search_pattern)) |
            (DocumentMetadata.description.ilike(search_pattern)) |
            (DocumentMetadata.tags.ilike(search_pattern))
        )
        
        # Filter by citizen if provided
        if citizen_id:
            query_builder = query_builder.where(
                DocumentMetadata.citizen_id == citizen_id
            )
        
        # Execute
        query_builder = query_builder.limit(limit).order_by(
            DocumentMetadata.created_at.desc()
        )
        result = await db.execute(query_builder)
        documents = result.scalars().all()
        
        # Convert to search results
        search_results = [
            SearchResult(
                id=doc.id,
                title=doc.description or doc.filename,
                description=doc.description,
                filename=doc.filename,
                created_at=doc.created_at,
                score=1.0  # PostgreSQL ILIKE doesn't provide scores
            )
            for doc in documents
        ]
        
        return SearchResponse(
            results=search_results,
            total=len(search_results),
            took_ms=0  # Placeholder
        )
    
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.delete("/documents/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Soft delete a document (mark as deleted)."""
    logger.info(f"Deleting document: {document_id}")
    
    try:
        # Get document
        result = await db.execute(
            select(DocumentMetadata).where(DocumentMetadata.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        # Soft delete
        document.is_deleted = True
        await db.commit()
        
        logger.info(f"Document {document_id} marked as deleted")
        
        # TODO: Delete from OpenSearch index
        # TODO: Optionally delete from blob storage (or keep for audit)
        
        return {"message": f"Document {document_id} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentMetadata:
    """Get document metadata by ID."""
    logger.info(f"Getting document: {document_id}")
    
    try:
        result = await db.execute(
            select(DocumentMetadata).where(
                DocumentMetadata.id == document_id,
                DocumentMetadata.is_deleted == False
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        return document
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document"
        )

