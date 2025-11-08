"""Signature API router."""

import logging
from datetime import datetime, date, timedelta
from typing import Annotated, Optional, Tuple
import httpx

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text

from app.config import get_config
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

# Get configuration
config = get_config()

# Singletons
_crypto = CryptoService(config)
_blob = BlobService(config)
_events = EventService(config)


async def _resolve_citizen_document_id(
    db: AsyncSession,
    identifier: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve the incoming identifier (user id, citizen id, email, etc.)
    to a 10-digit citizen document number.
    Returns (resolved_id, issue_message).
    """
    if not identifier:
        return None, "Citizen identifier not provided."

    identifier = identifier.strip()

    # Already a 10-digit document number
    if identifier.isdigit() and len(identifier) == 10:
        return identifier, None

    # 1. Does the identifier already match a citizen record?
    try:
        citizen_lookup = await db.execute(
            text(
                """
                SELECT id
                FROM citizens
                WHERE CAST(id AS TEXT) = CAST(:cid AS TEXT)
                LIMIT 1
                """
            ),
            {"cid": identifier},
        )
        citizen_row = citizen_lookup.scalar_one_or_none()
        if citizen_row:
            return str(citizen_row), None
    except Exception as e:
        logger.warning(f"⚠️  Failed to query citizens table: {e}")

    # 2. Resolve via users table (user.id -> citizen_id/email)
    user_row = None
    try:
        user_lookup = await db.execute(
            text(
                """
                SELECT citizen_id, email
                FROM users
                WHERE CAST(id AS TEXT) = CAST(:uid AS TEXT)
                LIMIT 1
                """
            ),
            {"uid": identifier},
        )
        user_row = user_lookup.fetchone()
    except Exception as e:
        issue = f"Failed querying users table: {e}"
        logger.warning(f"⚠️  {issue}")
        return None, issue

    if user_row:
        citizen_val = getattr(user_row, "citizen_id", None)
        if citizen_val:
            citizen_val = str(citizen_val).strip()
            if citizen_val.isdigit() and len(citizen_val) == 10:
                logger.info(
                    f"✅ Resolved user identifier '{identifier}' to citizen.id '{citizen_val}'"
                )
                return citizen_val, None
            if citizen_val:
                logger.info(
                    f"⚠️  User {identifier} is linked to citizen_id '{citizen_val}' "
                    "which is not a 10-digit document. Attempting recursive resolution..."
                )
                return await _resolve_citizen_document_id(db, citizen_val)

        email_val = getattr(user_row, "email", None)
        if email_val:
            try:
                email_lookup = await db.execute(
                    text(
                        """
                        SELECT id
                        FROM citizens
                        WHERE LOWER(email) = LOWER(:email)
                        LIMIT 1
                        """
                    ),
                    {"email": email_val},
                )
                email_row = email_lookup.fetchone()
                if email_row and email_row.id:
                    logger.info(
                        f"✅ Resolved user '{identifier}' via email to citizen.id '{email_row.id}'"
                    )
                    return str(email_row.id), None
            except Exception as e:
                logger.warning(f"⚠️  Failed resolving citizen via email lookup: {e}")
        return None, (
            f"User {identifier} exists but does not have a citizen linked (citizen_id/email missing)."
        )

    # 3. Identifier might be an email directly
    if "@" in identifier:
        try:
            email_lookup = await db.execute(
                text(
                    """
                    SELECT id
                    FROM citizens
                    WHERE LOWER(email) = LOWER(:email)
                    LIMIT 1
                    """
                ),
                {"email": identifier},
            )
            email_row = email_lookup.fetchone()
            if email_row and email_row.id:
                logger.info(
                    f"✅ Resolved email '{identifier}' to citizen.id '{email_row.id}'"
                )
                return str(email_row.id), None
        except Exception as e:
            logger.warning(f"⚠️  Failed resolving citizen via direct email: {e}")

    return None, f"Identifier '{identifier}' could not be mapped to a citizen document number."


@router.post("/sign", response_model=SignDocumentResponse)
async def sign_document(
    request: SignDocumentRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SignDocumentResponse:
    """Sign document and authenticate with hub.
    
    Flow:
    1. Fetch document metadata from DB to get blob_name
    2. Download document from Blob Storage
    3. Calculate SHA-256 of actual document
    4. Sign hash
    5. Generate SAS URL for hub
    6. Authenticate with hub
    7. Save signature record to DB
    8. Update document metadata (WORM)
    9. Publish events
    """
    logger.info(f"Signing document {request.document_id} for citizen {request.citizen_id}")
    
    # Resolve citizen identifier to the actual citizen document (10 digits)
    citizen_id_for_mintic, user_resolution_issue = await _resolve_citizen_document_id(
        db, request.citizen_id
    )
    if citizen_id_for_mintic:
        logger.info(
            f"Using citizen_id '{citizen_id_for_mintic}' for MinTIC Hub authentication"
        )
    else:
        logger.warning(
            f"⚠️  Unable to resolve citizen document number from identifier '{request.citizen_id}' yet; "
            "will attempt using document metadata."
        )
    
    # Check Redis idempotency (simplified, should use redis_client from common)
    # idempotency_key = f"authdoc:{citizen_id_for_mintic}:{request.document_id}"
    
    try:
        # 1. Fetch document metadata from database to get blob_name
        document_result = await db.execute(
            select(DocumentMetadata).where(DocumentMetadata.id == request.document_id)
        )
        document_metadata = document_result.scalar_one_or_none()
        
        if not document_metadata:
            logger.warning(f"⚠️  Document {request.document_id} not found in database for citizen {citizen_id_for_mintic}")
            # Try to provide more helpful error message by checking if document exists for this citizen
            try:
                from sqlalchemy import text
                check_result = await db.execute(
                    text("SELECT COUNT(*) as count FROM document_metadata WHERE citizen_id = :citizen_id"),
                    {"citizen_id": str(citizen_id_for_mintic)}
                )
                count_row = check_result.fetchone()
                count = count_row[0] if count_row else 0
                if count == 0:
                    detail = f"Document {request.document_id} not found. No documents exist for citizen {citizen_id_for_mintic}"
                else:
                    detail = f"Document {request.document_id} not found. Citizen {citizen_id_for_mintic} has {count} document(s), but this ID doesn't match"
            except Exception as check_error:
                logger.debug(f"Could not check document count: {check_error}")
                detail = f"Document {request.document_id} not found"
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail
            )
        
        if not citizen_id_for_mintic:
            metadata_citizen = (document_metadata.citizen_id or "").strip()
            citizen_id_for_mintic, metadata_issue = await _resolve_citizen_document_id(
                db, metadata_citizen
            )
            if citizen_id_for_mintic:
                logger.info(
                    f"✅ Resolved citizen document number using document metadata: {citizen_id_for_mintic}"
                )
            else:
                detail_parts = [
                    "Unable to determine citizen document number for signature request.",
                    f"Identifier from request: '{request.citizen_id}'.",
                ]
                if user_resolution_issue:
                    detail_parts.append(user_resolution_issue)
                if metadata_issue:
                    detail_parts.append(metadata_issue)
                else:
                    detail_parts.append(
                        "Document metadata does not contain a valid citizen_id."
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=" ".join(detail_parts),
                )
        
        # Check if document is already signed
        if document_metadata.state == "SIGNED" or document_metadata.worm_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document {request.document_id} is already signed and WORM-locked"
            )
        
        # 2. Fetch document from Blob Storage using blob_name
        try:
            document_data = await _blob.download_blob(document_metadata.blob_name)
            logger.info(f"Downloaded document {request.document_id} from blob {document_metadata.blob_name} ({len(document_data)} bytes)")
        except Exception as e:
            logger.error(f"Failed to download document {request.document_id} from blob {document_metadata.blob_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download document from storage: {str(e)}"
            )
        
        # 3. Calculate SHA-256 of the actual document
        sha256_hash = await _crypto.calculate_sha256(document_data)
        
        # 4. Sign hash
        signature_b64, algorithm = await _crypto.sign_hash(sha256_hash)
        
        # 5. Generate SAS URL for hub (GET-only, short expiration from ConfigMap)
        # Hub solo necesita acceso temporal para validar/autenticar
        # NO almacena ni canaliza binarios, solo valida metadata
        # Uses SAS_TTL_MINUTES from ConfigMap (default: 15 minutes)
        # User Delegation SAS if Managed Identity available
        sas_url = await _blob.generate_sas_url(
            document_metadata.blob_name  # Use actual blob_name from metadata
            # expiry_hours will use sas_ttl_minutes from config
        )
        
        # 6. Authenticate with hub via direct MinTIC Hub API
        hub_result = {"success": False, "message": "Not authenticated"}  # Default to failure
        
        try:
            # Direct call to MinTIC Hub API (public endpoint)
            hub_url = f"{config.mintic_hub_url}/apis/authenticateDocument"
            
            async with httpx.AsyncClient(timeout=30.0) as hub_client:
                hub_response = await hub_client.put(
                    hub_url,
                    json={
                        "idCitizen": int(citizen_id_for_mintic),  # Use resolved citizen.id (10-digit document number)
                        "UrlDocument": sas_url,
                        "documentTitle": request.document_title
                    },
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "CarpetaCiudadana-Signature/1.0"
                    }
                )
                
                if hub_response.status_code == 200:
                    hub_result = {"success": True, "message": hub_response.text}
                    logger.info(f"✅ Document authenticated with MinTIC Hub for citizen {citizen_id_for_mintic}")
                else:
                    hub_result = {"success": False, "message": f"Hub returned {hub_response.status_code}: {hub_response.text}"}
                    logger.warning(f"⚠️  MinTIC Hub authentication failed: {hub_response.status_code}")
                    
        except httpx.ConnectError as e:
            logger.error(f"❌ Connection error to MinTIC Hub: {e}")
            hub_result = {"success": False, "message": f"Connection error: {str(e)}"}
        except httpx.TimeoutException as e:
            logger.error(f"❌ Timeout error to MinTIC Hub: {e}")
            hub_result = {"success": False, "message": f"Timeout error: {str(e)}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error to MinTIC Hub: {e}")
            hub_result = {"success": False, "message": f"HTTP error: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ Unexpected error calling MinTIC Hub: {e}")
            hub_result = {"success": False, "message": str(e)}
        
        # 7. Save signature record to database
        try:
            record = SignatureRecord(
                document_id=request.document_id,
                citizen_id=citizen_id_for_mintic,  # Use resolved citizen.id
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
        except Exception as e:
            logger.error(f"❌ Error creating signature record: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create signature record: {str(e)}"
            )
        
        # 8. UPDATE DOCUMENT METADATA WITH WORM (REQUERIMIENTO CRÍTICO)
        # Solo si hub authentication fue exitosa
        if hub_result["success"]:
            logger.info(f"🔒 Activating WORM for document {request.document_id}")
            
            # Documentos firmados se retienen ETERNAMENTE (retention_until = None)
            # Los documentos no firmados tienen retención de 30 días
            # retention_until = None significa retención permanente
            
            # Extraer hub signature ref del response
            hub_sig_ref = hub_result.get("signature_ref", f"hub-sig-{request.document_id[:8]}")
            
            try:
                # Actualizar document_metadata a SIGNED con WORM
                # retention_until = None para retención eterna
                update_stmt = (
                    update(DocumentMetadata)
                    .where(DocumentMetadata.id == request.document_id)
                    .values(
                        state="SIGNED",
                        worm_locked=True,
                        signed_at=datetime.utcnow(),
                        retention_until=None,  # ETERNAMENTE - documentos firmados no expiran
                        hub_signature_ref=hub_sig_ref,
                        status="authenticated"  # Also update old status field
                    )
                )
                await db.execute(update_stmt)
                
                logger.info(
                    f"✅ WORM activated: doc={request.document_id}, "
                    f"retention_until=ETERNAL (None)"
                )
                
                # Azure Storage blob tags update
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
        try:
            await db.commit()
            await db.refresh(record)
            logger.info("✅ Database transaction committed successfully")
        except Exception as e:
            logger.error(f"❌ Error committing database transaction: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to commit transaction: {str(e)}"
            )
        
        # 9. Publish events (use common message broker)
        try:
            from carpeta_common.message_broker import publish_document_authenticated
            
            await publish_document_authenticated(
                document_id=request.document_id,
                citizen_id=citizen_id_for_mintic,  # Use resolved citizen.id
                sha256_hash=sha256_hash,
                hub_success=hub_result["success"]
            )
            logger.info("✅ Event published via common message broker")
        except ImportError:
            logger.warning("⚠️  carpeta_common not installed, using fallback event publishing")
            try:
                await _events.publish_document_authenticated(
                    request.document_id,
                    citizen_id_for_mintic,  # Use resolved citizen.id
                    hub_result["success"]
                )
            except Exception as event_error:
                logger.warning(f"⚠️  Fallback event publishing failed: {event_error}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to publish event via common broker: {e}")
            try:
                await _events.publish_document_authenticated(
                    request.document_id,
                    citizen_id_for_mintic,  # Use resolved citizen.id
                    hub_result["success"]
                )
            except Exception as event_error:
                logger.warning(f"⚠️  Fallback event publishing failed: {event_error}")
        
        logger.info(f"✅ Document signed and authenticated: {request.document_id}")
        
        return SignDocumentResponse(
            document_id=request.document_id,
            signed_document_id=f"{request.document_id}_signed",
            sha256_hash=sha256_hash,
            signature_type=algorithm,
            signed_at=record.signed_at,
            signed_blob_url=sas_url
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404, 400) as-is
        raise
    except Exception as e:
        logger.error(f"❌ Signing failed: {e}", exc_info=True)
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
    try:
        # Try to find by signed_document_id first, then by document_id
        result = await db.execute(
            select(SignatureRecord).where(
                (SignatureRecord.document_id == request.signed_document_id) |
                (SignatureRecord.document_id == request.signed_document_id.replace('_signed', ''))
            )
        )
        record = result.scalar_one_or_none()
        
        if not record:
            logger.warning(f"⚠️  Signature record not found: {request.signed_document_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Signature record not found: {request.signed_document_id}"
            )
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) as-is
        raise
    except Exception as e:
        logger.error(f"❌ Error querying signature record: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query signature record: {str(e)}"
        )
    
    # Verify signature
    try:
        is_valid, details = await _crypto.verify_signature(
            record.sha256_hash,
            record.signature_value
        )
        logger.info(f"✅ Signature verification completed: {is_valid}")
    except Exception as e:
        logger.error(f"❌ Error verifying signature: {e}")
        is_valid = False
        details = f"Verification error: {str(e)}"
    
    # Publish event
    try:
        await _events.publish_document_verified(request.signed_document_id, is_valid)
        logger.info("✅ Verification event published")
    except Exception as e:
        logger.warning(f"⚠️  Failed to publish verification event: {e}")
    
    return VerifySignatureResponse(
        is_valid=is_valid,
        sha256_hash=record.sha256_hash,
        signature_type=record.signature_algorithm,
        signed_at=record.signed_at,
        verified_at=datetime.utcnow(),
        details=details
    )
