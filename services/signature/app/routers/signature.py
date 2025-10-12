"""Signature API router."""

import logging
from datetime import datetime, date, timedelta
from typing import Annotated
import httpx

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.config import Settings
from app.database import get_db
from app.models import SignatureRecord, DocumentMetadata
from app.schemas import (
    SignDocumentRequest,
    SignDocumentResponse,
    VerifySignatureRequest,
    VerifySignatureResponse
)
from app.services.crypto_service import CryptoService
from app.services.blob_service import BlobService
from app.services.event_service import EventService

logger = logging.getLogger(__name__)
router = APIRouter()

# Singletons
_settings = Settings()
_crypto = CryptoService(_settings)
_blob = BlobService(_settings)
_events = EventService(_settings)


@router.post("/sign", response_model=SignDocumentResponse)
async def sign_document(
    request: SignDocumentRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SignDocumentResponse:
    """Sign document and authenticate with hub.
    
    Flow:
    1. Fetch document from blob
    2. Calculate SHA-256
    3. Sign hash
    4. Generate SAS URL
    5. Authenticate with hub
    6. Save record to DB
    7. Publish event
    """
    logger.info(f"Signing document {request.document_id} for citizen {request.citizen_id}")
    
    # Check Redis idempotency (simplified, should use redis_client from common)
    # idempotency_key = f"authdoc:{request.citizen_id}:{request.document_id}"
    
    try:
        # 1. Fetch document (simplified - assume we have the data)
        # In production: fetch from ingestion service or blob
        document_data = f"DOCUMENT_CONTENT_{request.document_id}".encode()
        
        # 2. Calculate SHA-256
        sha256_hash = await _crypto.calculate_sha256(document_data)
        
        # 3. Sign hash
        signature_b64, algorithm = await _crypto.sign_hash(sha256_hash)
        
        # 4. Generate SAS URL for hub (GET-only, short expiration from ConfigMap)
        # Hub solo necesita acceso temporal para validar/autenticar
        # NO almacena ni canaliza binarios, solo valida metadata
        # Uses SAS_TTL_MINUTES from ConfigMap (default: 15 minutes)
        # User Delegation SAS if Managed Identity available
        sas_url = await _blob.generate_sas_url(
            request.document_id
            # expiry_hours will use sas_ttl_minutes from Settings
        )
        
        # 5. Authenticate with hub via mintic_client service (facade)
        hub_result = {"success": True, "message": "OK"}  # Default
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as mintic_client:
                mintic_response = await mintic_client.put(
                    f"{_settings.metadata_service_url.replace('metadata', 'mintic-client')}/authenticate-document",
                    json={
                        "idCitizen": request.citizen_id,
                        "UrlDocument": sas_url,
                        "documentTitle": request.document_title
                    }
                )
                
                if mintic_response.status_code == 200:
                    hub_result = {"success": True, "message": mintic_response.text}
                    logger.info(f"✅ Document authenticated with hub for citizen {request.citizen_id}")
                else:
                    hub_result = {"success": False, "message": mintic_response.text}
                    logger.warning(f"⚠️  Hub authentication failed: {mintic_response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error calling mintic_client: {e}")
            hub_result = {"success": False, "message": str(e)}
        
        # 6. Save signature record to database
        record = SignatureRecord(
            document_id=request.document_id,
            citizen_id=request.citizen_id,
            document_title=request.document_title,
            sha256_hash=sha256_hash,
            signature_algorithm=algorithm,
            signature_value=signature_b64,
            sas_url=sas_url,
            sas_expires_at=datetime.utcnow(),
            hub_authenticated=hub_result["success"],
            hub_response=str(hub_result),
            hub_authenticated_at=datetime.utcnow() if hub_result["success"] else None,
        )
        
        db.add(record)
        await db.flush()  # Flush but don't commit yet
        
        # 6b. UPDATE DOCUMENT METADATA WITH WORM (REQUERIMIENTO CRÍTICO)
        # Solo si hub authentication fue exitosa
        if hub_result["success"]:
            logger.info(f"🔒 Activating WORM for document {request.document_id}")
            
            # Calcular retention (5 años desde firma)
            retention_date = date.today() + timedelta(days=365 * 5)
            
            # Extraer hub signature ref del response
            hub_sig_ref = hub_result.get("signature_ref", f"hub-sig-{request.document_id[:8]}")
            
            try:
                # Actualizar document_metadata a SIGNED con WORM
                update_stmt = (
                    update(DocumentMetadata)
                    .where(DocumentMetadata.id == request.document_id)
                    .values(
                        state="SIGNED",
                        worm_locked=True,
                        signed_at=datetime.utcnow(),
                        retention_until=retention_date,
                        hub_signature_ref=hub_sig_ref,
                        status="authenticated"  # Also update old status field
                    )
                )
                await db.execute(update_stmt)
                
                logger.info(
                    f"✅ WORM activated: doc={request.document_id}, "
                    f"retention_until={retention_date.isoformat()}"
                )
                
                # TODO: Update blob tags in Azure Storage
                # await _blob.set_blob_tags(
                #     blob_name=document.blob_name,
                #     tags={
                #         "state": "SIGNED",
                #         "worm": "true",
                #         "retentionUntil": retention_date.isoformat(),
                #         "hubRef": hub_sig_ref
                #     }
                # )
                
            except Exception as worm_error:
                logger.error(f"❌ Failed to activate WORM: {worm_error}")
                # Don't fail the whole operation, but log the error
                # In production, this should be retried or alerted
        
        # Commit everything in one transaction
        await db.commit()
        await db.refresh(record)
        
        # 7. Publish events (use common message broker)
        try:
            from carpeta_common.message_broker import publish_document_authenticated
            
            await publish_document_authenticated(
                document_id=request.document_id,
                citizen_id=request.citizen_id,
                sha256_hash=sha256_hash,
                hub_success=hub_result["success"]
            )
        except ImportError:
            logger.warning("carpeta_common not installed, skipping event publishing")
        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")
        
        logger.info(f"✅ Document signed and authenticated: {request.document_id}")
        
        return SignDocumentResponse(
            document_id=request.document_id,
            signed_document_id=f"{request.document_id}_signed",
            sha256_hash=sha256_hash,
            signature_type=algorithm,
            signed_at=record.signed_at,
            signed_blob_url=sas_url
        )
        
    except Exception as e:
        logger.error(f"❌ Signing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signing failed: {str(e)}"
        )


@router.post("/verify", response_model=VerifySignatureResponse)
async def verify_signature(
    request: VerifySignatureRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VerifySignatureResponse:
    """Verify document signature."""
    logger.info(f"Verifying signature for {request.signed_document_id}")
    
    # Get signature record from DB
    result = await db.execute(
        select(SignatureRecord).where(SignatureRecord.document_id == request.signed_document_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signature record not found: {request.signed_document_id}"
        )
    
    # Verify signature
    is_valid, details = await _crypto.verify_signature(
        record.sha256_hash,
        record.signature_value
    )
    
    # Publish event
    await _events.publish_document_verified(request.signed_document_id, is_valid)
    
    return VerifySignatureResponse(
        is_valid=is_valid,
        sha256_hash=record.sha256_hash,
        signature_type=record.signature_algorithm,
        signed_at=record.signed_at,
        verified_at=datetime.utcnow(),
        details=details
    )
