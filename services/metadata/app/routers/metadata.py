"""Metadata API router with OpenSearch integration."""

import hashlib
import json
import logging
from typing import Annotated, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import get_db
from app.opensearch_client import OpenSearchClient
from app.models import DocumentMetadata
from app.schemas import (
    DocumentMetadataCreate,
    DocumentMetadataResponse,
    DocumentSearchResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Singletons
_settings = Settings()
_opensearch = OpenSearchClient(_settings)

# Import Redis client from common package
try:
    from carpeta_common.redis_client import get_json, set_json
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("carpeta_common not installed, caching disabled")


@router.on_event("startup")
async def startup():
    """Initialize OpenSearch index on startup."""
    try:
        await _opensearch.ensure_index()
    except Exception as e:
        logger.error(f"Failed to initialize OpenSearch: {e}")


@router.post("/documents", response_model=DocumentMetadataResponse, status_code=status.HTTP_201_CREATED)
async def create_document_metadata(
    metadata: DocumentMetadataCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentMetadata:
    """Create document metadata and index in OpenSearch."""
    logger.info(f"Creating metadata for document: {metadata.title}")
    
    try:
        # Create in database
        doc = DocumentMetadata(
            id=metadata.id if hasattr(metadata, 'id') else None,
            citizen_id=metadata.citizen_id,
            filename=metadata.filename,
            title=metadata.title,
            content_type=metadata.content_type,
            blob_name=metadata.blob_name,
            sha256_hash=metadata.sha256_hash,
            storage_provider=metadata.storage_provider,
            status=metadata.status or "uploaded",
        )
        
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        # Index in OpenSearch
        await _opensearch.index_document(
            document_id=str(doc.id),
            citizen_id=doc.citizen_id,
            title=doc.title,
            filename=doc.filename,
            hash_value=doc.sha256_hash or "",
            content_type=doc.content_type,
            status=doc.status,
            created_at=doc.created_at.isoformat() if doc.created_at else None,
            updated_at=doc.updated_at.isoformat() if doc.updated_at else None
        )
        
        logger.info(f"✅ Document metadata created and indexed: {doc.id}")
        return doc
        
    except Exception as e:
        logger.error(f"❌ Failed to create metadata: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create metadata: {str(e)}"
        )


@router.get("/search", response_model=DocumentSearchResponse)
async def search_documents(
    q: str = Query("", description="Search query"),
    citizen_id: Optional[int] = Query(None, description="Filter by citizen ID"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> DocumentSearchResponse:
    """Search documents using OpenSearch with Redis caching and invalidation.
    
    Results are cached in Redis for 120 seconds.
    Cache is invalidated via Redis Pub/Sub on document changes.
    """
    # Build cache key (include citizen_id in key for easy invalidation)
    cache_params = {
        "q": q,
        "citizen_id": citizen_id,
        "tags": tags,
        "status": status,
        "page": page,
        "page_size": page_size
    }
    cache_key_data = json.dumps(cache_params, sort_keys=True)
    cache_key_hash = hashlib.md5(cache_key_data.encode()).hexdigest()
    
    # Include citizen_id in key for targeted invalidation
    if citizen_id:
        cache_key = f"search:citizen:{citizen_id}:{cache_key_hash}"
    else:
        cache_key = f"search:global:{cache_key_hash}"
    
    # Try cache first
    if REDIS_AVAILABLE:
        cached = await get_json(cache_key)
        if cached:
            logger.info(f"📦 Cache HIT: {cache_key[:32]}...")
            return DocumentSearchResponse(**cached)
    
    # Cache MISS - query OpenSearch
    logger.info(f"❌ Cache MISS: {cache_key[:32]}...")
    
    # Parse tags
    tag_list = tags.split(",") if tags else None
    
    # Calculate pagination
    from_ = (page - 1) * page_size
    
    # Search in OpenSearch
    results = await _opensearch.search_documents(
        query=q,
        citizen_id=citizen_id,
        tags=tag_list,
        status=status,
        from_=from_,
        size=page_size
    )
    
    # Build response
    response = DocumentSearchResponse(
        total=results["total"],
        page=page,
        page_size=page_size,
        results=results["hits"]
    )
    
    # Cache results (120s TTL)
    if REDIS_AVAILABLE:
        try:
            from carpeta_common.redis_client import set_json
            await set_json(cache_key, response.dict(), ttl=120)
            logger.info(f"💾 Cached search results: {cache_key[:32]}... (TTL=120s)")
        except Exception as e:
            logger.warning(f"Failed to cache results: {e}")
    
    return response


@router.get("/documents", response_model=List[DocumentMetadataResponse])
async def list_documents(
    citizen_id: Optional[int] = Query(None, description="Filter by citizen ID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[DocumentMetadata]:
    """List documents from database (not OpenSearch)."""
    query = select(DocumentMetadata)
    
    if citizen_id:
        query = query.where(DocumentMetadata.citizen_id == citizen_id)
    
    query = query.where(DocumentMetadata.is_deleted == False)
    query = query.limit(limit).offset(offset)
    query = query.order_by(DocumentMetadata.created_at.desc())
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return documents


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Soft delete document and remove from OpenSearch."""
    logger.info(f"Deleting document: {document_id}")
    
    # Mark as deleted in database
    result = await db.execute(
        select(DocumentMetadata).where(DocumentMetadata.id == document_id)
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )
    
    doc.is_deleted = True
    await db.commit()
    
    # Remove from OpenSearch
    await _opensearch.delete_document(document_id)
    
    logger.info(f"✅ Document deleted: {document_id}")
    return {"message": "Document deleted", "document_id": document_id}
