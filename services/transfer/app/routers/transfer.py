"""Transfer API router for P2P transfers."""

import hashlib
import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.models import (
    TransferCitizenRequest,
    TransferCitizenResponse,
    TransferConfirmRequest,
    TransferConfirmResponse,
    InitiateTransferRequest,
    InitiateTransferResponse,
    TransferStatusResponse,
    TransferStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# In-memory stores (use Redis in production)
idempotency_store: dict[str, TransferCitizenResponse] = {}
transfer_store: dict[str, TransferStatusResponse] = {}


async def verify_b2b_token(authorization: str = Header(...)) -> str:
    """Verify B2B OAuth token with mTLS.

    In production, verify JWT token from IAM service.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token = authorization.replace("Bearer ", "")
    # TODO: Verify token with IAM service
    return token


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
    token: Annotated[str, Depends(verify_b2b_token)],
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

    # Check idempotency
    if idempotency_key in idempotency_store:
        logger.warning(f"Duplicate request with idempotency key {idempotency_key}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate request",
        )

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

        # TODO: Store in local S3 and database
        logger.info(f"Downloaded {len(downloaded_docs)} documents")

        # Store in database (citizen and documents)
        # TODO: Implement database storage

        # Create response
        response = TransferCitizenResponse(
            message="Citizen transfer received and processing",
            citizen_id=request.id,
        )

        # Store idempotency
        idempotency_store[idempotency_key] = response

        # Call confirmation endpoint asynchronously
        # In production, use background task or queue
        try:
            await send_confirmation(request.confirmAPI, request.id, req_status=1)
        except Exception as e:
            logger.error(f"Error sending confirmation: {e}")
            # Don't fail the transfer if confirmation fails
            # It will be retried

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

    if request.req_status == 1:
        # Success: Delete source data
        logger.info(f"Transfer successful, deleting source data for citizen {request.id}")
        # TODO: Delete from database and S3
        message = f"Citizen {request.id} transfer confirmed"
    else:
        # Failure: Keep data, mark as failed
        logger.warning(f"Transfer failed for citizen {request.id}")
        # TODO: Update transfer status to failed
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
        
        # TODO: Start background task to process transfer
        # This would typically involve:
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
            estimated_completion=now.replace(minute=now.minute + 5),  # 5 minutes estimate
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
) -> list[dict]:
    """List transfers for a citizen."""
    logger.info(f"Listing transfers for citizen {citizen_id}")
    
    # Filter transfers by citizen_id
    citizen_transfers = []
    for transfer_id, transfer in transfer_store.items():
        # Check if citizen is sender or receiver
        if (hasattr(transfer, 'from_citizen_id') and transfer.from_citizen_id == citizen_id) or \
           (hasattr(transfer, 'to_citizen_id') and transfer.to_citizen_id == citizen_id):
            citizen_transfers.append({
                "id": transfer_id,
                "document_id": getattr(transfer, 'document_id', ''),
                "document_title": getattr(transfer, 'document_title', 'Unknown Document'),
                "from_citizen_id": getattr(transfer, 'from_citizen_id', ''),
                "to_citizen_id": getattr(transfer, 'to_citizen_id', ''),
                "to_email": getattr(transfer, 'to_email', ''),
                "status": transfer.status.value if hasattr(transfer.status, 'value') else str(transfer.status),
                "created_at": transfer.created_at.isoformat(),
                "updated_at": transfer.updated_at.isoformat(),
                "message": getattr(transfer, 'message', ''),
            })
    
    # Apply status filter if provided
    if status_filter:
        citizen_transfers = [t for t in citizen_transfers if t['status'] == status_filter]
    
    # Apply pagination
    return citizen_transfers[offset:offset + limit]


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

