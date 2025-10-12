"""Sharing routes."""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import get_db
from app.models import SharePackage, ShareAccessLog
from app.schemas import (
    CreateSharePackageRequest,
    CreateSharePackageResponse,
    SharePackageAccess,
    SharePackageDocument
)
from app.services.abac_client import ABACClient
from app.services.sas_generator import SASGenerator
from app.services.token_generator import TokenGenerator

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependencies
settings = Settings()
abac_client = ABACClient(settings)
sas_generator = SASGenerator(settings)


@router.post("/packages", response_model=CreateSharePackageResponse, status_code=status.HTTP_201_CREATED)
async def create_share_package(
    request: CreateSharePackageRequest,
    db: AsyncSession = Depends(get_db)
) -> CreateSharePackageResponse:
    """Create a share package with shortlink.
    
    Steps:
    1. Verify ABAC (owner can share)
    2. Generate SAS URLs for documents
    3. Create package record with token
    4. Cache in Redis
    5. Publish event
    """
    logger.info(f"Creating share package for {request.owner_email} with {len(request.document_ids)} documents")
    
    # 1. ABAC authorization check
    # TODO: Get actual user from JWT
    user_sub = request.owner_email  # Simplified
    
    for doc_id in request.document_ids:
        authorized, reason = await abac_client.authorize(
            subject=user_sub,
            resource=f"document:{doc_id}",
            action="share",
            context={"audience": request.audience}
        )
        
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to share document {doc_id}: {reason}"
            )
    
    # 2. Validate expiration
    if request.expires_at <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expiration date must be in the future"
        )
    
    # 3. Generate unique token
    token = TokenGenerator.generate_token(settings.shortlink_token_length)
    
    # Check uniqueness
    result = await db.execute(select(SharePackage).where(SharePackage.token == token))
    if result.scalar_one_or_none():
        # Retry with new token
        token = TokenGenerator.generate_token(settings.shortlink_token_length + 4)
    
    # 4. Create package record
    package = SharePackage(
        token=token,
        owner_email=request.owner_email,
        document_ids=request.document_ids,
        audience=request.audience,
        requires_auth=request.requires_auth,
        watermark_enabled=request.watermark_enabled,
        watermark_text=request.watermark_text or settings.watermark_text,
        expires_at=request.expires_at,
        created_by=user_sub,
        is_active=True
    )
    
    db.add(package)
    await db.commit()
    await db.refresh(package)
    
    # 5. Cache in Redis
    try:
        from carpeta_common.redis_client import set_json
        
        cache_data = {
            "package_id": package.id,
            "owner_email": package.owner_email,
            "document_ids": package.document_ids,
            "expires_at": package.expires_at.isoformat(),
            "watermark_enabled": package.watermark_enabled,
            "watermark_text": package.watermark_text
        }
        
        ttl = int((package.expires_at - datetime.utcnow()).total_seconds())
        await set_json(f"share:{token}", cache_data, ttl=ttl)
        logger.info(f"💾 Cached share package in Redis: share:{token} (TTL={ttl}s)")
        
    except ImportError:
        logger.warning("carpeta_common not installed, skipping Redis cache")
    except Exception as e:
        logger.warning(f"Failed to cache in Redis: {e}")
    
    # 6. Publish event
    try:
        from carpeta_common.message_broker import publish_event
        
        await publish_event(
            event_type="share.package.created",
            queue_name="share-events",
            payload={
                "package_id": package.id,
                "token": token,
                "owner_email": package.owner_email,
                "document_count": len(package.document_ids),
                "audience": package.audience,
                "expires_at": package.expires_at.isoformat()
            }
        )
        logger.info("📤 Published share.package.created event")
    except ImportError:
        logger.warning("carpeta_common not installed, skipping event publishing")
    except Exception as e:
        logger.warning(f"Failed to publish event: {e}")
    
    # 7. Generate shortlink
    shortlink = TokenGenerator.generate_shortlink(settings.shortlink_base_url, token)
    
    logger.info(f"✅ Share package created: {shortlink}")
    
    return CreateSharePackageResponse(
        package_id=package.id,
        token=token,
        shortlink=shortlink,
        expires_at=package.expires_at,
        document_count=len(package.document_ids)
    )


@router.get("/s/{token}", response_model=SharePackageAccess)
async def access_share_package(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> SharePackageAccess:
    """Access a share package via shortlink.
    
    Steps:
    1. Load package from Redis or DB
    2. Validate expiration and status
    3. Verify ABAC consent
    4. Generate fresh SAS URLs
    5. Log access
    6. Return documents with SAS URLs
    """
    logger.info(f"Accessing share package: {token}")
    
    # 1. Try Redis cache first
    package_data = None
    try:
        from carpeta_common.redis_client import get_json
        
        package_data = await get_json(f"share:{token}")
        if package_data:
            logger.info(f"📦 Cache HIT: share:{token}")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Redis cache failed: {e}")
    
    # 2. Load from database if not in cache
    if not package_data:
        logger.info(f"❌ Cache MISS: share:{token}")
        result = await db.execute(
            select(SharePackage).where(SharePackage.token == token)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share package not found"
            )
    else:
        # Reconstruct package from cache
        result = await db.execute(
            select(SharePackage).where(SharePackage.id == package_data["package_id"])
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share package not found in database"
            )
    
    # 3. Validate expiration
    if package.expires_at <= datetime.utcnow():
        # Log denied access
        await _log_access(db, package, request, granted=False, reason="Expired")
        
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share link has expired"
        )
    
    # 4. Validate status
    if not package.is_active:
        await _log_access(db, package, request, granted=False, reason="Revoked")
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Share link has been revoked"
        )
    
    # 5. ABAC consent check (if audience specified)
    if package.audience and package.audience != "public":
        # TODO: Get user from JWT
        user_email = request.headers.get("X-User-Email", "anonymous")
        
        if user_email != package.audience:
            authorized, reason = await abac_client.authorize(
                subject=user_email,
                resource=f"share:{package.id}",
                action="access",
                context={"owner": package.owner_email, "audience": package.audience}
            )
            
            if not authorized:
                await _log_access(db, package, request, granted=False, reason=f"Unauthorized: {reason}")
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not authorized to access this share: {reason}"
                )
    
    # 6. Generate fresh SAS URLs for documents
    expiry_hours = min(
        settings.sas_default_expiry_hours,
        int((package.expires_at - datetime.utcnow()).total_seconds() / 3600) + 1
    )
    
    sas_results = await sas_generator.generate_sas_urls(
        blob_names=package.document_ids,
        expiry_hours=expiry_hours,
        add_watermark=package.watermark_enabled
    )
    
    # 7. Build document list
    documents = []
    for sas_data in sas_results:
        # TODO: Query metadata service for document info
        doc = SharePackageDocument(
            document_id=sas_data["blob_name"],
            filename=sas_data["blob_name"].split("/")[-1],
            content_type="application/octet-stream",  # TODO: Get from metadata
            size=0,  # TODO: Get from metadata
            sas_url=sas_data["sas_url"],
            watermarked=package.watermark_enabled
        )
        documents.append(doc)
    
    # 8. Update access count
    package.access_count += 1
    package.last_accessed_at = datetime.utcnow()
    await db.commit()
    
    # 9. Log successful access
    await _log_access(db, package, request, granted=True)
    
    logger.info(f"✅ Share package accessed: {token} ({len(documents)} documents)")
    
    return SharePackageAccess(
        package_id=package.id,
        owner_email=package.owner_email,
        expires_at=package.expires_at,
        documents=documents,
        watermark_text=package.watermark_text if package.watermark_enabled else None
    )


async def _log_access(
    db: AsyncSession,
    package: SharePackage,
    request: Request,
    granted: bool,
    reason: Optional[str] = None
) -> None:
    """Log access attempt."""
    try:
        log_entry = ShareAccessLog(
            share_package_id=package.id,
            token=package.token,
            accessed_by_email=request.headers.get("X-User-Email"),
            accessed_by_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            access_granted=granted,
            denial_reason=reason
        )
        
        db.add(log_entry)
        await db.commit()
        
    except Exception as e:
        logger.error(f"Failed to log access: {e}")

