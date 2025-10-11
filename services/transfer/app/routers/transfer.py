"""Transfer API router for P2P transfers."""

import hashlib
import logging
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.models import (
    TransferCitizenRequest,
    TransferCitizenResponse,
    TransferConfirmRequest,
    TransferConfirmResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# In-memory store for idempotency (use Redis in production)
idempotency_store: dict[str, TransferCitizenResponse] = {}


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

