"""Safe P2P transfer router with distributed locks and proper hub unregister flow.

CRITICAL: Origin must NOT unregister from hub until destination confirms with status=1.
"""

import logging
import hashlib
import httpx
from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.db_models import Transfer, TransferStatus
from app.models import (
    TransferCitizenRequest,
    TransferCitizenResponse,
    TransferConfirmRequest,
    TransferConfirmResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/transferCitizen", response_model=TransferCitizenResponse, status_code=status.HTTP_201_CREATED)
async def transfer_citizen(
    request: TransferCitizenRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransferCitizenResponse:
    """Receive citizen transfer from another operator (destination endpoint).

    Flow:
    1. Check idempotency (Redis SETNX xfer:idemp:{key})
    2. Download documents from presigned URLs
    3. Store in local storage
    4. Save to database with status=PENDING
    5. Return 201 (destination will confirm later)
    
    IMPORTANT: Origin waits for confirmation before unregistering from hub.

    Headers:
    - Idempotency-Key: UUID (required)
    
    Responses:
    - 201: Transfer accepted and processing
    - 409: Duplicate request (idempotency key reused)
    """
    logger.info(
        f"📨 Received transfer for citizen {request.id} "
        f"with idempotency_key={idempotency_key}"
    )
    
    # Check idempotency with Redis
    redis_idemp_key = f"xfer:idemp:{idempotency_key}"
    
    try:
        from carpeta_common.redis_client import setnx
        
        # Try to set idempotency key (SET NX EX 900)
        was_set = await setnx(redis_idemp_key, "processing", ttl=900)
        
        if not was_set:
            logger.warning(f"⚠️  Duplicate transfer request: {idempotency_key}")
            
            # Check database for existing transfer
            result = await db.execute(
                select(Transfer).where(Transfer.idempotency_key == idempotency_key)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Transfer already processed (status: {existing.status})",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Duplicate idempotency key",
                )
    except ImportError:
        logger.warning("⚠️  carpeta_common not available, idempotency disabled")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Idempotency check failed: {e}")
    
    # Create transfer record (incoming)
    transfer = Transfer(
        citizen_id=request.id,
        citizen_name=request.name,
        citizen_email=request.email,
        direction="incoming",
        source_operator_id=request.source_operator_id,
        source_operator_name=request.source_operator_name,
        destination_operator_id="self",  # TODO: Get from config
        destination_operator_name="Carpeta Ciudadana Demo",
        idempotency_key=idempotency_key,
        status=TransferStatus.PENDING,
        document_ids=str(request.documents) if request.documents else "[]"
    )
    
    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)
    
    # TODO: Download documents asynchronously (background task)
    # For now, just accept the transfer
    
    logger.info(f"✅ Transfer {transfer.id} created with status PENDING")
    
    return TransferCitizenResponse(
        transfer_id=transfer.id,
        message=f"Transfer accepted for citizen {request.id}",
        status="pending"
    )


@router.post("/transferCitizenConfirm", response_model=TransferConfirmResponse)
async def transfer_citizen_confirm(
    request: TransferConfirmRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransferConfirmResponse:
    """Confirm citizen transfer (called by destination operator).

    CRITICAL FLOW:
    1. Acquire distributed lock (lock:delete:{citizen_id})
    2. Verify request with token
    3. If req_status=1 (success):
       a. Update local transfer status to PENDING_UNREGISTER
       b. Delete citizen data from local DB
       c. Delete citizen documents from local storage
       d. Call hub DELETE /apis/unregisterCitizen (with retries)
       e. Only if hub confirms → status=SUCCESS
    4. If req_status=0 (failure):
       - Keep data, mark transfer as FAILED
    5. Release lock
    
    IMPORTANT: Lock prevents race conditions in deletion.

    Responses:
    - 200: Confirmation processed
    - 404: Transfer not found
    - 500: Server error
    """
    logger.info(
        f"📨 Received confirmation for citizen {request.citizenId} "
        f"with status={request.req_status}, token={request.token}"
    )
    
    # Acquire distributed lock for atomic deletion
    lock_key = f"lock:delete:{request.citizenId}"
    lock_token = str(uuid4())
    
    try:
        from carpeta_common.redis_client import acquire_lock, release_lock
        
        acquired = await acquire_lock(lock_key, ttl=120, token=lock_token)
        
        if not acquired:
            logger.error(f"🔒 Could not acquire lock for citizen {request.citizenId}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Another operation in progress, try again later"
            )
        
        logger.info(f"🔓 Lock acquired: {lock_key}")
        
    except ImportError:
        logger.warning("⚠️  carpeta_common not available, lock disabled (UNSAFE)")
        lock_token = None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Lock acquisition failed: {e}")
        lock_token = None
    
    try:
        # Find outgoing transfer by citizen_id and token
        result = await db.execute(
            select(Transfer).where(
                Transfer.citizen_id == request.citizenId,
                Transfer.direction == "outgoing",
                Transfer.idempotency_key == request.token
            )
        )
        transfer = result.scalar_one_or_none()
        
        if not transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transfer not found for citizen {request.citizenId}"
            )
        
        if request.req_status == 1:
            # SUCCESS - destination confirmed receipt
            logger.info(f"✅ Destination confirmed transfer for citizen {request.citizenId}")
            
            # Update status to PENDING_UNREGISTER
            transfer.status = TransferStatus.PENDING_UNREGISTER
            transfer.confirmed_at = datetime.utcnow()
            await db.commit()
            
            # TODO: Delete citizen data from local DB (in transaction)
            # TODO: Delete citizen documents from local storage
            
            # Unregister from hub (CRITICAL - only after destination confirms)
            try:
                # Call mintic_client to unregister
                async with httpx.AsyncClient(timeout=10.0) as client:
                    mintic_url = "http://localhost:8005"  # TODO: Get from config
                    
                    unregister_response = await client.delete(
                        f"{mintic_url}/unregister-citizen",
                        json={
                            "id": request.citizenId,
                            "operatorId": transfer.source_operator_id,
                            "operatorName": transfer.source_operator_name
                        }
                    )
                    
                    if unregister_response.status_code in [200, 201, 204]:
                        logger.info(f"✅ Citizen {request.citizenId} unregistered from hub")
                        
                        # Mark as SUCCESS
                        transfer.status = TransferStatus.SUCCESS
                        transfer.unregistered_at = datetime.utcnow()
                        transfer.completed_at = datetime.utcnow()
                        await db.commit()
                        
                    else:
                        # Hub unregister failed - keep in PENDING_UNREGISTER for retry
                        logger.error(
                            f"❌ Hub unregister failed: {unregister_response.status_code} "
                            f"- Transfer remains in PENDING_UNREGISTER for retry"
                        )
                        transfer.error_message = f"Hub unregister failed: {unregister_response.text}"
                        transfer.retry_count += 1
                        await db.commit()
                        
                        # Don't fail the confirmation - will retry later
                        
            except Exception as e:
                logger.error(f"❌ Error unregistering from hub: {e}")
                transfer.error_message = f"Hub unregister error: {str(e)}"
                transfer.retry_count += 1
                await db.commit()
                
                # Don't fail - background job will retry
        
        else:
            # FAILED - destination reported failure
            logger.warning(f"⚠️  Destination reported transfer FAILED for citizen {request.citizenId}")
            transfer.status = TransferStatus.FAILED
            transfer.error_message = "Destination reported failure"
            transfer.completed_at = datetime.utcnow()
            await db.commit()
        
        return TransferConfirmResponse(
            message=f"Confirmation processed for citizen {request.citizenId}",
            success=True
        )
    
    finally:
        # Release lock
        if lock_token:
            try:
                from carpeta_common.redis_client import release_lock
                await release_lock(lock_key, lock_token)
                logger.info(f"🔓 Lock released: {lock_key}")
            except Exception as e:
                logger.error(f"❌ Lock release failed: {e}")

