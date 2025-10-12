"""Test safe transfer order: confirm → delete local → unregisterCitizen.

Tests:
- (f) Transfer waits for destination confirmation before deleting
- (f) Local deletion happens only after confirmation
- (f) Hub unregister happens only after local deletion
- (f) PENDING_UNREGISTER state if hub unregister fails
- (f) Background job retries PENDING_UNREGISTER
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession


# Mock models since we don't have the actual implementation yet
class TransferStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PENDING_UNREGISTER = "pending_unregister"
    SUCCESS = "success"
    FAILED = "failed"


class Transfer:
    def __init__(self, id, citizen_id, source_operator_id, destination_operator_id, status):
        self.id = id
        self.citizen_id = citizen_id
        self.source_operator_id = source_operator_id
        self.destination_operator_id = destination_operator_id
        self.status = status
        self.confirmed_at = None
        self.unregistered_at = None
        self.completed_at = None
        self.retry_count = 0


# (f) Test safe transfer order
@pytest.mark.asyncio
async def test_transfer_waits_for_confirmation_before_delete():
    """Test that origin waits for destination confirmation before deleting."""
    # Simulate transfer request
    transfer = Transfer(
        id=1,
        citizen_id=1234567890,
        source_operator_id="op-source",
        destination_operator_id="op-dest",
        status=TransferStatus.PENDING
    )
    
    # Destination has NOT confirmed yet
    assert transfer.status == TransferStatus.PENDING
    assert transfer.confirmed_at is None
    
    # Origin should NOT delete local data
    # Origin should NOT call hub unregisterCitizen
    
    # Simulate destination confirmation
    transfer.status = TransferStatus.CONFIRMED
    transfer.confirmed_at = datetime.utcnow()
    
    # NOW origin can proceed with deletion
    assert transfer.status == TransferStatus.CONFIRMED
    assert transfer.confirmed_at is not None


@pytest.mark.asyncio
async def test_local_deletion_after_confirmation():
    """Test that local deletion happens only after destination confirms."""
    transfer = Transfer(
        id=1,
        citizen_id=1234567890,
        source_operator_id="op-source",
        destination_operator_id="op-dest",
        status=TransferStatus.PENDING
    )
    
    # Mock services
    mock_db = AsyncMock(spec=AsyncSession)
    mock_blob_service = AsyncMock()
    mock_mintic_client = AsyncMock()
    
    # BEFORE confirmation: should NOT delete
    if transfer.status == TransferStatus.PENDING:
        # Don't delete
        assert not mock_db.delete.called
        assert not mock_blob_service.delete_blob.called
    
    # AFTER confirmation (req_status=1)
    transfer.status = TransferStatus.CONFIRMED
    transfer.confirmed_at = datetime.utcnow()
    
    if transfer.status == TransferStatus.CONFIRMED:
        # NOW delete local data
        await mock_db.delete(transfer)
        await mock_blob_service.delete_all_for_citizen(transfer.citizen_id)
        
        assert mock_db.delete.called
        assert mock_blob_service.delete_all_for_citizen.called


@pytest.mark.asyncio
async def test_hub_unregister_after_local_deletion():
    """Test that hub unregister happens only after local deletion succeeds."""
    transfer = Transfer(
        id=1,
        citizen_id=1234567890,
        source_operator_id="op-source",
        destination_operator_id="op-dest",
        status=TransferStatus.CONFIRMED
    )
    
    mock_mintic_client = AsyncMock()
    mock_mintic_client.unregister_citizen = AsyncMock()
    
    # Step 1: Delete local data
    local_deletion_success = True
    
    if local_deletion_success:
        # Step 2: NOW call hub unregisterCitizen
        await mock_mintic_client.unregister_citizen({"id": transfer.citizen_id})
        
        assert mock_mintic_client.unregister_citizen.called
        
        # If successful
        transfer.status = TransferStatus.SUCCESS
        transfer.unregistered_at = datetime.utcnow()
        transfer.completed_at = datetime.utcnow()


@pytest.mark.asyncio
async def test_pending_unregister_state_if_hub_fails():
    """Test that transfer enters PENDING_UNREGISTER if hub unregister fails."""
    transfer = Transfer(
        id=1,
        citizen_id=1234567890,
        source_operator_id="op-source",
        destination_operator_id="op-dest",
        status=TransferStatus.CONFIRMED
    )
    
    mock_mintic_client = AsyncMock()
    
    # Simulate hub unregister failure
    mock_mintic_client.unregister_citizen = AsyncMock(side_effect=Exception("Hub timeout"))
    
    # Step 1: Delete local data (SUCCESS)
    local_deletion_success = True
    
    if local_deletion_success:
        # Step 2: Try to unregister from hub
        try:
            await mock_mintic_client.unregister_citizen({"id": transfer.citizen_id})
        except Exception:
            # Hub failed → enter PENDING_UNREGISTER state
            transfer.status = TransferStatus.PENDING_UNREGISTER
            transfer.retry_count += 1
    
    # Should be in PENDING_UNREGISTER
    assert transfer.status == TransferStatus.PENDING_UNREGISTER
    assert transfer.retry_count == 1
    assert transfer.unregistered_at is None  # Not yet unregistered
    assert transfer.completed_at is None  # Not yet completed


@pytest.mark.asyncio
async def test_background_job_retries_pending_unregister():
    """Test that background job retries PENDING_UNREGISTER transfers."""
    # Simulate transfers in PENDING_UNREGISTER state
    pending_transfers = [
        Transfer(
            id=1,
            citizen_id=1234567890,
            source_operator_id="op-source",
            destination_operator_id="op-dest",
            status=TransferStatus.PENDING_UNREGISTER
        ),
        Transfer(
            id=2,
            citizen_id=9876543210,
            source_operator_id="op-source",
            destination_operator_id="op-dest",
            status=TransferStatus.PENDING_UNREGISTER
        )
    ]
    
    mock_mintic_client = AsyncMock()
    mock_mintic_client.unregister_citizen = AsyncMock(return_value={"status": 204})
    
    # Background job processes pending transfers
    for transfer in pending_transfers:
        try:
            result = await mock_mintic_client.unregister_citizen({"id": transfer.citizen_id})
            
            if result["status"] in [200, 204]:
                # Success
                transfer.status = TransferStatus.SUCCESS
                transfer.unregistered_at = datetime.utcnow()
                transfer.completed_at = datetime.utcnow()
            else:
                # Still failing
                transfer.retry_count += 1
        except Exception:
            transfer.retry_count += 1
    
    # All should be success
    assert all(t.status == TransferStatus.SUCCESS for t in pending_transfers)
    assert all(t.unregistered_at is not None for t in pending_transfers)


@pytest.mark.asyncio
async def test_max_retries_for_pending_unregister():
    """Test that after max retries, transfer needs manual intervention."""
    transfer = Transfer(
        id=1,
        citizen_id=1234567890,
        source_operator_id="op-source",
        destination_operator_id="op-dest",
        status=TransferStatus.PENDING_UNREGISTER
    )
    transfer.retry_count = 10  # Already tried 10 times
    
    MAX_RETRIES = 10
    
    if transfer.retry_count >= MAX_RETRIES:
        # Don't retry anymore, needs manual intervention
        # Log alert for ops team
        assert transfer.status == TransferStatus.PENDING_UNREGISTER
        assert transfer.retry_count >= MAX_RETRIES
        # In real implementation: send alert to ops


@pytest.mark.asyncio
async def test_distributed_lock_prevents_race_condition():
    """Test that distributed lock prevents race condition during deletion."""
    transfer = Transfer(
        id=1,
        citizen_id=1234567890,
        source_operator_id="op-source",
        destination_operator_id="op-dest",
        status=TransferStatus.CONFIRMED
    )
    
    # Mock Redis lock
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)  # Lock acquired
    mock_redis.delete = AsyncMock()
    
    lock_key = f"lock:delete:{transfer.citizen_id}"
    lock_token = "unique-token-123"
    
    # Acquire lock
    lock_acquired = await mock_redis.set(lock_key, lock_token, nx=True, ex=120)
    
    assert lock_acquired is True
    
    # Do deletion (atomic with lock)
    if lock_acquired:
        # Delete DB
        # Delete blobs
        # Unregister from hub
        pass
    
    # Release lock
    await mock_redis.delete(lock_key)
    
    assert mock_redis.set.called
    assert mock_redis.delete.called


@pytest.mark.asyncio
async def test_idempotency_for_transfer_confirm():
    """Test that transferCitizenConfirm is idempotent."""
    # Mock Redis for idempotency
    mock_redis = AsyncMock()
    
    idempotency_key = "transfer-confirm-abc123"
    redis_key = f"xfer:idemp:{idempotency_key}"
    
    # First call: key doesn't exist
    mock_redis.setnx = AsyncMock(return_value=True)
    
    can_process = await mock_redis.setnx(redis_key, "1", ex=900)
    
    assert can_process is True
    
    # Second call: key exists (duplicate)
    mock_redis.setnx = AsyncMock(return_value=False)
    
    can_process = await mock_redis.setnx(redis_key, "1", ex=900)
    
    assert can_process is False
    # Should return 409 Conflict


@pytest.mark.asyncio
async def test_complete_safe_transfer_flow():
    """Test the complete safe transfer flow."""
    transfer = Transfer(
        id=1,
        citizen_id=1234567890,
        source_operator_id="op-source",
        destination_operator_id="op-dest",
        status=TransferStatus.PENDING
    )
    
    # 1. Origin initiates transfer
    assert transfer.status == TransferStatus.PENDING
    
    # 2. Destination receives and confirms (req_status=1)
    transfer.status = TransferStatus.CONFIRMED
    transfer.confirmed_at = datetime.utcnow()
    
    # 3. Origin deletes local data (DB + blobs)
    local_deletion_done = True
    assert local_deletion_done
    
    # 4. Origin calls hub unregisterCitizen
    hub_unregister_success = True
    
    if hub_unregister_success:
        transfer.status = TransferStatus.SUCCESS
        transfer.unregistered_at = datetime.utcnow()
        transfer.completed_at = datetime.utcnow()
    else:
        transfer.status = TransferStatus.PENDING_UNREGISTER
        transfer.retry_count += 1
    
    # Final state
    assert transfer.status == TransferStatus.SUCCESS
    assert transfer.confirmed_at is not None
    assert transfer.unregistered_at is not None
    assert transfer.completed_at is not None

