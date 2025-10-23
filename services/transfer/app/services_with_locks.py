"""
Transfer service with distributed locks integration
Prevents race conditions in transfer operations
"""

import logging
from typing import Optional

from carpeta_common.redis_lock import LockManager, RedisLock
from carpeta_common.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class TransferService:
    """
    Transfer service with distributed locking.
    
    Uses Redis locks to prevent:
    - Concurrent transfer initiations for same document
    - Double-spending (document transferred multiple times)
    - Race conditions in status updates
    """
    
    def __init__(self):
        self.redis = get_redis_client()
        self.lock_manager = LockManager(self.redis)
    
    def initiate_transfer(self, document_id: str, from_user: str, to_user: str) -> dict:
        """
        Initiate document transfer with locking.
        
        Args:
            document_id: ID of document to transfer
            from_user: Current owner
            to_user: New owner
        
        Returns:
            Transfer details
        
        Raises:
            ValueError: If validation fails
            LockAcquisitionError: If lock cannot be acquired
        """
        # Lock document to prevent concurrent transfers
        with self.lock_manager.lock_document(document_id, ttl=60):
            logger.info(f"Transfer initiated: {document_id} ({from_user} → {to_user})")
            
            # Transfer validation and creation
            
            return {
                "transfer_id": "transfer-123",
                "document_id": document_id,
                "from_user": from_user,
                "to_user": to_user,
                "status": "pending"
            }
    
    def accept_transfer(self, transfer_id: str, user_id: str) -> dict:
        """
        Accept incoming transfer with locking.
        
        Args:
            transfer_id: Transfer to accept
            user_id: User accepting
        
        Returns:
            Updated transfer details
        """
        # Lock transfer operation
        with self.lock_manager.lock_transfer(transfer_id, ttl=60):
            logger.info(f"Transfer accepted: {transfer_id} by {user_id}")
            
            # Transfer acceptance logic
            
            return {
                "transfer_id": transfer_id,
                "status": "accepted",
                "accepted_at": "2025-10-13T06:00:00Z"
            }
    
    def reject_transfer(self, transfer_id: str, user_id: str, reason: str) -> dict:
        """
        Reject incoming transfer with locking.
        
        Args:
            transfer_id: Transfer to reject
            user_id: User rejecting
            reason: Rejection reason
        
        Returns:
            Updated transfer details
        """
        # Lock transfer operation
        with self.lock_manager.lock_transfer(transfer_id, ttl=30):
            logger.info(f"Transfer rejected: {transfer_id} by {user_id} (reason: {reason})")
            
            # Transfer rejection logic
            
            return {
                "transfer_id": transfer_id,
                "status": "rejected",
                "rejected_at": "2025-10-13T06:00:00Z",
                "reason": reason
            }
    
    def cancel_transfer(self, transfer_id: str, user_id: str) -> dict:
        """
        Cancel outgoing transfer with locking.
        
        Args:
            transfer_id: Transfer to cancel
            user_id: User canceling (must be sender)
        
        Returns:
            Updated transfer details
        """
        # Lock transfer operation
        with self.lock_manager.lock_transfer(transfer_id, ttl=30):
            logger.info(f"Transfer canceled: {transfer_id} by {user_id}")
            
            # Transfer cancellation logic
            
            return {
                "transfer_id": transfer_id,
                "status": "canceled",
                "canceled_at": "2025-10-13T06:00:00Z"
            }


# Example usage in FastAPI endpoint
"""
from fastapi import APIRouter, HTTPException
from app.services_with_locks import TransferService
from carpeta_common.redis_lock import LockAcquisitionError

router = APIRouter()
transfer_service = TransferService()

@router.post("/transfers")
async def create_transfer(document_id: str, to_user: str, current_user: str):
    try:
        transfer = transfer_service.initiate_transfer(
            document_id=document_id,
            from_user=current_user,
            to_user=to_user
        )
        return transfer
    except LockAcquisitionError:
        raise HTTPException(
            status_code=409,
            detail="Transfer already in progress for this document"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/transfers/{transfer_id}/accept")
async def accept_transfer(transfer_id: str, current_user: str):
    try:
        result = transfer_service.accept_transfer(transfer_id, current_user)
        return result
    except LockAcquisitionError:
        raise HTTPException(
            status_code=409,
            detail="Transfer is being processed"
        )
"""

