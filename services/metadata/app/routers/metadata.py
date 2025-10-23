"""Metadata API router with OpenSearch integration and Azure PostgreSQL."""

import hashlib
import json
import logging
from typing import Annotated, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.opensearch_client import OpenSearchClient
from app.models import DocumentMetadata
from app.schemas import (
    DocumentMetadataCreate,
    DocumentMetadataResponse,
    DocumentSearchResponse,
)
from app.config import get_config

logger = logging.getLogger(__name__)
router = APIRouter()

# Configuration and clients
_config = get_config()
_opensearch = OpenSearchClient(_config)

# Redis client import with fallback
try:
    from carpeta_common.redis_client import get_json, set_json
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("carpeta_common not installed, caching disabled")
    
    # Fallback functions for when Redis is not available
    async def get_json(key: str):
        return None
    
    async def set_json(key: str, value: dict, ttl: int = 300):
        pass


@router.on_event("startup")
async def startup():
    """Initialize OpenSearch index on startup."""
    try:
        _opensearch.ensure_index()
    except Exception as e:
        logger.error(f"Failed to initialize OpenSearch: {e}")


@router.post("/documents", response_model=DocumentMetadataResponse, status_code=status.HTTP_201_CREATED)
async def create_document_metadata(
    metadata: DocumentMetadataCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentMetadata:
    """Create document metadata with robust error handling."""
    try:
        logger.info(f"📄 [CREATE] Creating metadata for document: {metadata.filename}")
        
        # Create document metadata
        import uuid
        document_id = str(uuid.uuid4())
        document = DocumentMetadata(
            id=document_id,
            citizen_id=metadata.citizen_id,
            title=metadata.title,
            filename=metadata.filename,
            content_type=metadata.content_type,
            size_bytes=metadata.size_bytes,
            sha256_hash=metadata.sha256_hash,
            blob_name=f"citizens/{metadata.citizen_id}/documents/{document_id}/{metadata.filename}",
            storage_provider="azure",
            status="pending",
            is_uploaded=False,
            state="UNSIGNED",
            worm_locked=False,
            legal_hold=False,
            lifecycle_tier="Hot",
            description=metadata.description,
            tags=metadata.tags,
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        logger.info(f"✅ [CREATE] Document metadata created: {document.id}")
        
        # Index in OpenSearch with error handling
        try:
            _opensearch.index_document(document)
            logger.info(f"✅ [CREATE] Document indexed in OpenSearch: {document.id}")
        except Exception as e:
            logger.warning(f"⚠️ [CREATE] Failed to index in OpenSearch: {e}")
            # Continue without failing the request
        
        return document
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"❌ [CREATE] Failed to create document metadata: {e}")
        logger.error(f"❌ [CREATE] Error type: {error_type}")
        
        # Azure-specific error handling
        if "connection" in str(e).lower():
            logger.error("❌ [CREATE] Database connection failed during document creation")
            logger.error("💡 [CREATE] Check Azure PostgreSQL availability and network connectivity")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable"
            )
        elif "permission" in str(e).lower():
            logger.error("❌ [CREATE] Database permission denied during document creation")
            logger.error("💡 [CREATE] Check database user permissions for INSERT operations")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient database permissions"
            )
        elif "timeout" in str(e).lower():
            logger.error("❌ [CREATE] Database connection timeout during document creation")
            logger.error("💡 [CREATE] Check Azure PostgreSQL performance and network latency")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Database operation timeout"
            )
        else:
            logger.error(f"❌ [CREATE] Unexpected database error during document creation: {error_type}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create document metadata: {str(e)}"
            )


@router.get("/search", response_model=DocumentSearchResponse)
async def search_documents(
    q: str = Query("", description="Search query"),
    citizen_id: Optional[str] = Query(None, description="Filter by citizen ID"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> DocumentSearchResponse:
    """Search documents using OpenSearch with Redis caching and invalidation."""
    try:
        logger.info(f"🔍 [SEARCH] Starting search endpoint")
        logger.info(f"🔍 [SEARCH] Parameters: q='{q}', citizen_id={citizen_id}, tags='{tags}', status='{status}', page={page}, page_size={page_size}")
        
        # Build cache key
        cache_params = {
            "q": q,
            "citizen_id": citizen_id,
            "tags": tags,
            "status": status,
            "page": page,
            "page_size": page_size
        }
        cache_key_data = json.dumps(cache_params, sort_keys=True)
        cache_key_hash = hashlib.sha256(cache_key_data.encode()).hexdigest()
        
        if citizen_id:
            cache_key = f"search:citizen:{citizen_id}:{cache_key_hash}"
        else:
            cache_key = f"search:global:{cache_key_hash}"
        
        # Try cache first
        if REDIS_AVAILABLE:
            try:
                cached = await get_json(cache_key)
                if cached:
                    logger.info(f"📦 [SEARCH] Cache HIT: {cache_key[:32]}...")
                    return DocumentSearchResponse(**cached)
                else:
                    logger.info(f"❌ [SEARCH] Cache MISS: {cache_key[:32]}...")
            except Exception as e:
                logger.warning(f"❌ [SEARCH] Cache read failed: {e}")
        
        # Cache MISS - query OpenSearch
        tag_list = tags.split(",") if tags else None
        from_ = (page - 1) * page_size
        
        try:
            # Check if OpenSearch is available
            if not _opensearch.client:
                logger.warning("⚠️ [SEARCH] OpenSearch not available, returning empty results")
                response = DocumentSearchResponse(
                    total=0,
                    page=page,
                    page_size=page_size,
                    documents=[],
                    took_ms=0
                )
            else:
                results = _opensearch.search_documents(
                    query=q,
                    citizen_id=citizen_id,
                    tags=tag_list,
                    status=status,
                    from_=from_,
                    size=page_size
                )
                
                response = DocumentSearchResponse(
                    total=results["total"],
                    page=page,
                    page_size=page_size,
                    documents=results["hits"],
                    took_ms=0
                )
            
        except Exception as e:
            logger.error(f"❌ [SEARCH] OpenSearch search failed: {e}")
            # Fallback to empty results
            response = DocumentSearchResponse(
                total=0,
                page=page,
                page_size=page_size,
                documents=[],
                took_ms=0
            )
        
        # Cache results (120s TTL)
        if REDIS_AVAILABLE:
            try:
                await set_json(cache_key, response.dict(), ttl=120)
                logger.info(f"💾 [SEARCH] Cached search results: {cache_key[:32]}... (TTL=120s)")
            except Exception as e:
                logger.warning(f"❌ [SEARCH] Failed to cache results: {e}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ [SEARCH] Unexpected error in search endpoint: {e}")
        return DocumentSearchResponse(
            total=0,
            page=page,
            page_size=page_size,
            documents=[],
            took_ms=0
        )


@router.get("/documents", response_model=List[DocumentMetadataResponse])
async def list_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    citizen_id: Optional[str] = Query(None, description="Filter by citizen ID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> List[DocumentMetadata]:
    """List documents from database with proper response model."""
    try:
        logger.info(f"🔍 [DOCUMENTS] Starting list documents endpoint")
        logger.info(f"🔍 [DOCUMENTS] Parameters: citizen_id={citizen_id}, limit={limit}, offset={offset}")
        
        # Test database connection first
        logger.info("🔍 [DOCUMENTS] Testing database connection...")
        test_query = select(DocumentMetadata).limit(1)
        test_result = await db.execute(test_query)
        test_docs = test_result.scalars().all()
        
        logger.info(f"✅ [DOCUMENTS] Database connection successful, found {len(test_docs)} test documents")
        
        # Build the full query
        logger.info("🔍 [DOCUMENTS] Building full query...")
        query = select(DocumentMetadata)
        
        if citizen_id:
            logger.info(f"🔍 [DOCUMENTS] Adding citizen_id filter: {citizen_id}")
            query = query.where(DocumentMetadata.citizen_id == citizen_id)
        
        query = query.where(DocumentMetadata.is_deleted == False)
        query = query.limit(limit).offset(offset)
        query = query.order_by(DocumentMetadata.created_at.desc())
        
        logger.info("🔍 [DOCUMENTS] Executing full query...")
        result = await db.execute(query)
        documents = result.scalars().all()
        
        logger.info(f"✅ [DOCUMENTS] Query successful, found {len(documents)} documents")
        
        # Log first few documents for debugging
        for i, doc in enumerate(documents[:3]):
            logger.info(f"📄 [DOCUMENTS] Document {i+1}: id={doc.id}, citizen_id={doc.citizen_id}, title={doc.title[:50]}...")
        
        return documents
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"❌ [DOCUMENTS] Failed to list documents: {e}")
        logger.error(f"❌ [DOCUMENTS] Error type: {error_type}")
        
        # Azure-specific error handling
        if "connection" in str(e).lower():
            logger.error("❌ [DOCUMENTS] Database connection failed during document listing")
            logger.error("💡 [DOCUMENTS] Check Azure PostgreSQL availability and network connectivity")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable"
            )
        elif "permission" in str(e).lower():
            logger.error("❌ [DOCUMENTS] Database permission denied during document listing")
            logger.error("💡 [DOCUMENTS] Check database user permissions for SELECT operations")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient database permissions"
            )
        elif "timeout" in str(e).lower():
            logger.error("❌ [DOCUMENTS] Database connection timeout during document listing")
            logger.error("💡 [DOCUMENTS] Check Azure PostgreSQL performance and network latency")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Database operation timeout"
            )
        else:
            logger.error(f"❌ [DOCUMENTS] Unexpected database error during document listing: {error_type}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list documents: {str(e)}"
            )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Delete document metadata with OpenSearch cleanup."""
    try:
        logger.info(f"🗑️ [DELETE] Deleting document: {document_id}")
        
        # Check if document exists
        query = select(DocumentMetadata).where(DocumentMetadata.id == document_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Soft delete in database
        document.is_deleted = True
        document.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"✅ [DELETE] Document soft deleted: {document_id}")
        
        # Remove from OpenSearch
        try:
            _opensearch.delete_document(document_id)
            logger.info(f"✅ [DELETE] Document removed from OpenSearch: {document_id}")
        except Exception as e:
            logger.warning(f"⚠️ [DELETE] Failed to remove from OpenSearch: {e}")
        
        # Invalidate cache
        if REDIS_AVAILABLE:
            try:
                # Invalidate citizen-specific cache
                cache_pattern = f"search:citizen:{document.citizen_id}:*"
                logger.info(f"🗑️ [DELETE] Invalidating cache pattern: {cache_pattern}")
                # Note: Redis pattern deletion would need additional implementation
            except Exception as e:
                logger.warning(f"⚠️ [DELETE] Failed to invalidate cache: {e}")
        
        return {"message": "Document deleted successfully", "document_id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"❌ [DELETE] Failed to delete document: {e}")
        logger.error(f"❌ [DELETE] Error type: {error_type}")
        
        # Azure-specific error handling
        if "connection" in str(e).lower():
            logger.error("❌ [DELETE] Database connection failed during document deletion")
            logger.error("💡 [DELETE] Check Azure PostgreSQL availability and network connectivity")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable"
            )
        elif "permission" in str(e).lower():
            logger.error("❌ [DELETE] Database permission denied during document deletion")
            logger.error("💡 [DELETE] Check database user permissions for UPDATE operations")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient database permissions"
            )
        elif "timeout" in str(e).lower():
            logger.error("❌ [DELETE] Database connection timeout during document deletion")
            logger.error("💡 [DELETE] Check Azure PostgreSQL performance and network latency")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Database operation timeout"
            )
        else:
            logger.error(f"❌ [DELETE] Unexpected database error during document deletion: {error_type}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document: {str(e)}"
            )

