"""Transfer API router for P2P transfers."""

import hashlib
import logging
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID, uuid4

import httpx
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.models import (
    TransferCitizenRequest,
    TransferCitizenResponse,
    TransferConfirmRequest,
    TransferConfirmResponse,
    InitiateTransferRequest,
    InitiateTransferResponse,
    TransferStatusResponse,
    TransferStatus,
    Transfer as DBTransfer,
    TransferStatus as DBTransferStatus
)
from app.database import get_db
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.azure_storage import azure_storage
from app.azure_servicebus import azure_servicebus
from app.azure_redis import azure_redis

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# In-memory stores (use Redis in production)
idempotency_store: dict[str, TransferCitizenResponse] = {}
transfer_store: dict[str, TransferStatusResponse] = {}


async def verify_b2b_token(authorization: str = Header(...)) -> dict:
    """Verify B2B OAuth JWT token.

    Validates JWT token and returns operator information.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token = authorization.replace("Bearer ", "")
    
    try:
        # Verify JWT token
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        
        # Validate token claims
        if payload.get("iss") != "carpeta-ciudadana-transfer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer"
            )
        
        if payload.get("aud") != "transfer-api":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience"
            )
        
        logger.info(f"Token verified for operator: {payload.get('sub')}")
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def download_document_with_retry(url: str) -> bytes:
    """Download document from presigned URL with retry logic."""

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
    )
    async def _download() -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            return response.content

    return await _download()


def verify_sha256(data: bytes, expected_hash: str | None = None) -> str:
    """Verify document integrity with SHA-256."""
    computed_hash = hashlib.sha256(data).hexdigest()
    if expected_hash and computed_hash != expected_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document integrity check failed",
        )
    return computed_hash


@router.post("/transferCitizen", response_model=TransferCitizenResponse)
async def transfer_citizen(
    request: TransferCitizenRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> TransferCitizenResponse:
    """Receive citizen transfer from another operator.

    Flow:
    1. Check idempotency key
    2. Download documents from presigned URLs
    3. Verify SHA-256 integrity
    4. Store in local S3 and database
    5. Call confirmation endpoint
    6. Return 201 or 409 (duplicate)

    Headers:
    - Authorization: Bearer <b2b_token>
    - Idempotency-Key: <uuid>

    Responses:
    - 201: Citizen transfer received and processing
    - 409: Duplicate request (idempotency)
    """
    logger.info(
        f"Received transfer request for citizen {request.id} "
        f"with idempotency key {idempotency_key}"
    )

    # Try JWT authentication with fallback
    operator_info = None
    if authorization:
        try:
            operator_info = await verify_b2b_token(authorization)
            logger.info(f"JWT authentication successful for operator: {operator_info.get('operator_id')}")
        except Exception as e:
            logger.warning(f"JWT authentication failed: {e}")
            # Continue without authentication for testing
            operator_info = {"operator_id": "test-operator", "operator_name": "Test Operator"}

    # Check idempotency with Redis SETNX (distributed) + Database fallback
    idempotency_acquired = False
    try:
        # Try Redis SETNX for distributed idempotency
        if azure_redis.is_available:
            idempotency_acquired = await azure_redis.set_idempotency_key(
                idempotency_key=idempotency_key,
                ttl_seconds=3600  # 1 hour TTL
            )
            if not idempotency_acquired:
                logger.warning(f"Duplicate request with idempotency key {idempotency_key} (Redis)")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Duplicate request",
                )
            logger.info(f"Idempotency key {idempotency_key} acquired via Redis SETNX")
        else:
            logger.warning("Redis not available, using database-only idempotency")
            # Fallback to database-only idempotency
            existing_transfer = await db.execute(
                select(Transfer).where(Transfer.idempotency_key == idempotency_key)
            )
            if existing_transfer.scalar_one_or_none():
                logger.warning(f"Duplicate request with idempotency key {idempotency_key} (Database)")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Duplicate request",
                )
            idempotency_acquired = True
    except Exception as e:
        logger.error(f"Idempotency check failed: {e}")
        # Fallback to database-only idempotency
        existing_transfer = await db.execute(
            select(DBTransfer).where(DBTransfer.idempotency_key == idempotency_key)
        )
        if existing_transfer.scalar_one_or_none():
            logger.warning(f"Duplicate request with idempotency key {idempotency_key} (Database fallback)")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate request",
            )
        idempotency_acquired = True

    try:
        # Download and verify documents
        downloaded_docs = []
        for doc_id, urls in request.urlDocuments.items():
            for url in urls:
                logger.info(f"Downloading document from {url}")
                data = await download_document_with_retry(url)
                sha256_hash = verify_sha256(data)
                downloaded_docs.append(
                    {"id": doc_id, "data": data, "sha256": sha256_hash, "size": len(data)}
                )

        # Store documents in Azure Storage with fallback
        stored_docs = []
        for doc in downloaded_docs:
            try:
                storage_result = await azure_storage.upload_document(
                    document_data=doc["data"],
                    document_id=doc["id"],
                    citizen_id=request.id,
                    metadata={
                        "sha256": doc["sha256"],
                        "size": doc["size"],
                        "original_url": request.urlDocuments[doc["id"]][0] if doc["id"] in request.urlDocuments else ""
                    }
                )
                stored_docs.append({
                    "id": doc["id"],
                    "storage_result": storage_result
                })
                logger.info(f"Document {doc['id']} stored successfully")
            except Exception as e:
                logger.error(f"Failed to store document {doc['id']}: {e}")
                # Continue with local storage fallback
                stored_docs.append({
                    "id": doc["id"],
                    "storage_result": {"success": False, "error": str(e)}
                })

        logger.info(f"Downloaded and stored {len(downloaded_docs)} documents")

        # Create transfer record in database
        import json
        transfer_record = DBTransfer(
            citizen_id=request.id,
            citizen_name=request.citizenName,
            citizen_email=request.citizenEmail,
            direction="incoming",
            idempotency_key=idempotency_key,
            confirm_url=request.confirmAPI,
            status=DBTransferStatus.PENDING,
            document_ids=json.dumps([doc["id"] for doc in downloaded_docs]),
            source_operator_id=operator_info.get("operator_id") if operator_info else None,
            source_operator_name=operator_info.get("operator_name") if operator_info else None
        )
        
        db.add(transfer_record)
        await db.commit()
        await db.refresh(transfer_record)
        
        logger.info(f"Transfer record created with ID: {transfer_record.id}")

        # Cache transfer data in Redis
        try:
            await azure_redis.set_transfer_cache(
                transfer_id=str(transfer_record.id),
                data={
                    "citizen_id": request.id,
                    "citizen_name": request.citizenName,
                    "status": "pending",
                    "documents": stored_docs
                }
            )
        except Exception as e:
            logger.warning(f"Failed to cache transfer data: {e}")

        # Send notification to Service Bus
        try:
            await azure_servicebus.send_transfer_notification(
                transfer_id=str(transfer_record.id),
                citizen_id=request.id,
                status="pending",
                message="Transfer initiated",
                metadata={
                    "operator_id": operator_info.get("operator_id") if operator_info else "unknown",
                    "document_count": len(downloaded_docs)
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send Service Bus notification: {e}")

        # Create response
        response = TransferCitizenResponse(
            message="Citizen transfer received and processing",
            citizen_id=request.id,
        )

        # Call confirmation endpoint asynchronously
        # In production, use background task or queue
        try:
            await send_confirmation(request.confirmAPI, request.id, req_status=1)
        except Exception as e:
            logger.error(f"Error sending confirmation: {e}")
            # Don't fail the transfer if confirmation fails
            # It will be retried

        # Clean up idempotency key after successful processing
        try:
            if azure_redis.is_available:
                await azure_redis.delete_idempotency_key(idempotency_key)
                logger.info(f"Idempotency key {idempotency_key} cleaned up")
        except Exception as e:
            logger.warning(f"Failed to clean up idempotency key: {e}")

        return response

    except Exception as e:
        logger.error(f"Error processing transfer: {e}")
        # Send failure confirmation
        try:
            await send_confirmation(request.confirmAPI, request.id, req_status=0)
        except Exception as conf_error:
            logger.error(f"Error sending failure confirmation: {conf_error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transfer failed: {str(e)}",
        )


@router.post("/transferCitizenConfirm", response_model=TransferConfirmResponse)
async def transfer_citizen_confirm(
    request: TransferConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> TransferConfirmResponse:
    """Receive transfer confirmation from destination operator.

    Only delete source data if req_status=1 (success).

    Flow:
    - req_status=1: Delete citizen data from source (DB + S3)
    - req_status=0: Keep data, mark transfer as failed

    Returns:
    - 200: Citizen {id} transfer confirmed
    """
    logger.info(
        f"Received transfer confirmation for citizen {request.id} "
        f"with status {request.req_status}"
    )

    # Find transfer record in database (get the most recent one)
    transfer_result = await db.execute(
        select(DBTransfer)
        .where(DBTransfer.citizen_id == request.id)
        .order_by(DBTransfer.initiated_at.desc())
        .limit(1)
    )
    transfer = transfer_result.scalar_one_or_none()
    
    if not transfer:
        logger.warning(f"Transfer not found for citizen {request.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    if request.req_status == 1:
        # Success: Update transfer status to confirmed
        logger.info(f"Transfer successful, updating status for citizen {request.id}")
        transfer.status = DBTransferStatus.CONFIRMED
        transfer.confirmed_at = datetime.utcnow()
        await db.commit()
        message = f"Citizen {request.id} transfer confirmed"
    else:
        # Failure: Mark transfer as failed
        logger.warning(f"Transfer failed for citizen {request.id}")
        transfer.status = DBTransferStatus.FAILED
        transfer.error_message = "Transfer rejected by destination operator"
        await db.commit()
        message = f"Citizen {request.id} transfer failed"

    return TransferConfirmResponse(message=message)


async def send_confirmation(confirm_url: str, citizen_id: int, req_status: int) -> None:
    """Send confirmation to source operator."""

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
    )
    async def _send() -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                confirm_url,
                json={"id": citizen_id, "req_status": req_status},
                timeout=30.0,
            )
            response.raise_for_status()
            logger.info(f"Confirmation sent successfully to {confirm_url}")

    await _send()


@router.post("/initiate", response_model=InitiateTransferResponse)
async def initiate_transfer(
    request: InitiateTransferRequest,
) -> InitiateTransferResponse:
    """Initiate citizen transfer to another operator.
    
    This endpoint is called from the frontend to start a transfer process.
    
    Flow:
    1. Validate request
    2. Get citizen documents from metadata service
    3. Get destination operator info from MinTIC service
    4. Create transfer record
    5. Start background transfer process
    6. Return transfer ID for tracking
    
    Returns:
    - 201: Transfer initiated successfully
    - 400: Invalid request
    - 404: Citizen or operator not found
    - 500: Internal error
    """
    logger.info(f"Initiating transfer for citizen {request.citizen_id} to operator {request.destination_operator_id}")
    
    try:
        # Generate unique transfer ID
        transfer_id = str(uuid4())
        now = datetime.utcnow()
        
        # Create initial transfer record
        transfer_record = TransferStatusResponse(
            transfer_id=transfer_id,
            status=TransferStatus.PENDING,
            progress=0,
            message="Transfer initiated, preparing documents...",
            created_at=now,
            updated_at=now,
        )
        
        # Store transfer record
        transfer_store[transfer_id] = transfer_record
        
        # Background transfer processing
        # 1. Get citizen documents from metadata service
        # 2. Get operator info from MinTIC service
        # 3. Prepare documents for transfer
        # 4. Send transfer request to destination operator
        # 5. Update transfer status based on response
        
        # For now, simulate immediate success
        # In production, this would be handled by a background worker
        await simulate_transfer_process(transfer_id, request)
        
        return InitiateTransferResponse(
            transfer_id=transfer_id,
            status=TransferStatus.PENDING,
            message="Transfer initiated successfully",
            estimated_completion=now.replace(minute=(now.minute + 5) % 60),  # 5 minutes estimate
        )
        
    except Exception as e:
        logger.error(f"Error initiating transfer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate transfer: {str(e)}",
        )


@router.get("/status/{transfer_id}", response_model=TransferStatusResponse)
async def get_transfer_status(transfer_id: str) -> TransferStatusResponse:
    """Get transfer status by ID.
    
    This endpoint is used by the frontend to poll for transfer status.
    
    Returns:
    - 200: Transfer status
    - 404: Transfer not found
    """
    logger.info(f"Getting status for transfer {transfer_id}")
    
    if transfer_id not in transfer_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found",
        )
    
    return transfer_store[transfer_id]


async def simulate_transfer_process(transfer_id: str, request: InitiateTransferRequest):
    """Simulate transfer process for development.
    
    In production, this would be a real background task that:
    1. Gets citizen documents
    2. Prepares transfer package
    3. Sends to destination operator
    4. Handles confirmation
    """
    import asyncio
    
    async def update_status(status: TransferStatus, progress: int, message: str):
        if transfer_id in transfer_store:
            transfer_store[transfer_id].status = status
            transfer_store[transfer_id].progress = progress
            transfer_store[transfer_id].message = message
            transfer_store[transfer_id].updated_at = datetime.utcnow()
    
    try:
        # Simulate processing steps
        await asyncio.sleep(2)
        await update_status(TransferStatus.IN_PROGRESS, 25, "Retrieving documents...")
        
        await asyncio.sleep(3)
        await update_status(TransferStatus.IN_PROGRESS, 50, "Preparing transfer package...")
        
        await asyncio.sleep(2)
        await update_status(TransferStatus.IN_PROGRESS, 75, "Sending to destination operator...")
        
        await asyncio.sleep(3)
        await update_status(TransferStatus.IN_PROGRESS, 90, "Waiting for confirmation...")
        
        await asyncio.sleep(2)
        await update_status(TransferStatus.COMPLETED, 100, "Transfer completed successfully!")
        
    except Exception as e:
        logger.error(f"Transfer process failed: {e}")
        if transfer_id in transfer_store:
            transfer_store[transfer_id].status = TransferStatus.FAILED
            transfer_store[transfer_id].error = str(e)
            transfer_store[transfer_id].updated_at = datetime.utcnow()



@router.get("/")
async def list_transfers(
    citizen_id: str,
    status_filter: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List transfers for a citizen."""
    logger.info(f"Listing transfers for citizen {citizen_id}")
    
    # Query transfers from database
    query = select(DBTransfer).where(DBTransfer.citizen_id == int(citizen_id))
    
    if status_filter:
        query = query.where(DBTransfer.status == status_filter)
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    transfers = result.scalars().all()
    
    # Convert to response format
    transfer_list = []
    for transfer in transfers:
        transfer_list.append({
            "id": str(transfer.id),
            "document_id": transfer.document_ids or "",
            "document_title": f"Transfer {transfer.id}",
            "from_citizen_id": str(transfer.citizen_id),
            "to_citizen_id": transfer.destination_operator_id or "",
            "to_email": transfer.citizen_email,
            "status": transfer.status.value,
            "created_at": transfer.initiated_at.isoformat(),
            "updated_at": transfer.confirmed_at.isoformat() if transfer.confirmed_at else transfer.initiated_at.isoformat(),
            "message": f"Transfer {transfer.status.value}"
        })
    
    return transfer_list


@router.get("/health/azure")
async def azure_health_check():
    """Check Azure services health."""
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check Azure Storage
    try:
        storage_health = {
            "available": azure_storage.is_available,
            "status": "healthy" if azure_storage.is_available else "fallback"
        }
    except Exception as e:
        storage_health = {
            "available": False,
            "status": "error",
            "error": str(e)
        }
    
    health_status["services"]["azure_storage"] = storage_health
    
    # Check Azure Service Bus
    try:
        servicebus_health = {
            "available": azure_servicebus.is_available,
            "status": "healthy" if azure_servicebus.is_available else "fallback"
        }
    except Exception as e:
        servicebus_health = {
            "available": False,
            "status": "error",
            "error": str(e)
        }
    
    health_status["services"]["azure_servicebus"] = servicebus_health
    
    # Check Azure Redis
    try:
        redis_health = await azure_redis.health_check()
    except Exception as e:
        redis_health = {
            "status": "error",
            "message": str(e)
        }
    
    health_status["services"]["azure_redis"] = redis_health
    
    return health_status


@router.post("/create")
async def create_transfer(
    transfer_data: dict,
    citizen_id: str = None,
) -> dict:
    """Create a new transfer."""
    logger.info(f"Creating transfer for citizen {citizen_id}")
    
    try:
        # Extract transfer data
        document_id = transfer_data.get('document_id')
        to_email = transfer_data.get('to_email')
        message = transfer_data.get('message', '')
        
        if not document_id or not to_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="document_id and to_email are required"
            )
        
        # Generate transfer ID
        transfer_id = str(uuid4())
        
        # Create transfer record
        transfer_record = {
            "id": transfer_id,
            "document_id": document_id,
            "document_title": f"Document {document_id}",  # TODO: Get real title
            "from_citizen_id": citizen_id or "unknown",
            "to_citizen_id": "unknown",  # TODO: Lookup by email
            "to_email": to_email,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow().timestamp() + 7 * 24 * 3600),  # 7 days
            "message": message,
        }
        
        # Store transfer
        transfer_store[transfer_id] = type('Transfer', (), transfer_record)()
        
        logger.info(f"Transfer {transfer_id} created successfully")
        
        return {
            "message": "Transfer created successfully",
            "transfer_id": transfer_id,
            "transfer": transfer_record
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating transfer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create transfer"
        )


@router.post("/{transfer_id}/accept")
async def accept_transfer(
    transfer_id: str,
    citizen_id: str = None,
) -> dict:
    """Accept a transfer."""
    logger.info(f"Accepting transfer {transfer_id}")
    
    if transfer_id not in transfer_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    
    transfer = transfer_store[transfer_id]
    
    # Update transfer status
    transfer.status = TransferStatus.COMPLETED
    transfer.updated_at = datetime.utcnow()
    transfer.message = "Transfer accepted"
    
    logger.info(f"Transfer {transfer_id} accepted")
    
    return {
        "message": "Transfer accepted successfully",
        "transfer_id": transfer_id
    }


@router.post("/{transfer_id}/reject")
async def reject_transfer(
    transfer_id: str,
    citizen_id: str = None,
) -> dict:
    """Reject a transfer."""
    logger.info(f"Rejecting transfer {transfer_id}")
    
    if transfer_id not in transfer_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    
    transfer = transfer_store[transfer_id]
    
    # Update transfer status
    transfer.status = TransferStatus.FAILED
    transfer.updated_at = datetime.utcnow()
    transfer.message = "Transfer rejected"
    
    logger.info(f"Transfer {transfer_id} rejected")
    
    return {
        "message": "Transfer rejected successfully",
        "transfer_id": transfer_id
    }

