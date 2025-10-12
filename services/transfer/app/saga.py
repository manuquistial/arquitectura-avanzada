"""Saga pattern for distributed transfer operations.

Implements choreography-based saga with compensation.

Steps:
1. Generate SAS URLs (compensate: revoke SAS)
2. Send transfer request (compensate: send cancel)
3. Wait for confirmation (timeout: fail saga)
4. Delete source data on success (no compensation)

Each step publishes events to Service Bus for observability and recovery.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)


class SagaStep(str, Enum):
    """Saga step names."""
    STARTED = "started"
    SAS_GENERATED = "sas_generated"
    TRANSFER_SENT = "transfer_sent"
    CONFIRMED = "confirmed"
    SOURCE_DELETED = "source_deleted"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


class SagaState(str, Enum):
    """Saga state machine."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


class TransferSaga:
    """Saga for citizen transfer between operators.
    
    Manages distributed transaction with compensation on failure.
    """
    
    def __init__(
        self,
        transfer_id: int,
        citizen_id: int,
        source_operator: str,
        destination_operator: str,
        destination_url: str
    ):
        """Initialize transfer saga.
        
        Args:
            transfer_id: Transfer ID
            citizen_id: Citizen ID
            source_operator: Source operator ID
            destination_operator: Destination operator ID
            destination_url: Transfer endpoint URL
        """
        self.transfer_id = transfer_id
        self.citizen_id = citizen_id
        self.source_operator = source_operator
        self.destination_operator = destination_operator
        self.destination_url = destination_url
        
        # State
        self.state = SagaState.RUNNING
        self.current_step = SagaStep.STARTED
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        
        # Data collected during saga
        self.sas_urls: list[str] = []
        self.document_ids: list[str] = []
        self.confirmation_received = False
        self.error: Optional[str] = None
        
        # Compensation data
        self.compensation_actions: list[Dict[str, Any]] = []
    
    async def execute(self) -> bool:
        """Execute saga steps.
        
        Returns:
            True if saga completed successfully, False otherwise
        """
        try:
            # Step 1: Generate SAS URLs for documents
            await self._step_generate_sas()
            
            # Step 2: Send transfer request to destination
            await self._step_send_transfer()
            
            # Step 3: Wait for confirmation (with timeout)
            await self._step_wait_confirmation()
            
            # Step 4: Delete source data
            await self._step_delete_source()
            
            # Mark as completed
            self.state = SagaState.COMPLETED
            self.current_step = SagaStep.COMPLETED
            self.completed_at = datetime.utcnow()
            
            await self._publish_saga_event("transfer.saga.completed", {
                "transfer_id": self.transfer_id,
                "duration_seconds": (self.completed_at - self.started_at).total_seconds()
            })
            
            logger.info(f"✅ Transfer saga completed: {self.transfer_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Transfer saga failed: {e}")
            self.state = SagaState.FAILED
            self.error = str(e)
            
            # Execute compensation
            await self._compensate()
            
            return False
    
    async def _step_generate_sas(self):
        """Step 1: Generate SAS URLs for all citizen documents."""
        logger.info(f"📝 [Saga {self.transfer_id}] Step 1: Generating SAS URLs")
        
        # TODO: Get documents from database
        # TODO: Generate SAS URLs for each document
        # For now, mock
        self.sas_urls = [
            f"https://storage.blob.core.windows.net/docs/doc1.pdf?sas=mock",
            f"https://storage.blob.core.windows.net/docs/doc2.pdf?sas=mock"
        ]
        self.document_ids = ["doc1", "doc2"]
        
        # Record compensation action
        self.compensation_actions.append({
            "action": "revoke_sas",
            "sas_urls": self.sas_urls.copy()
        })
        
        self.current_step = SagaStep.SAS_GENERATED
        await self._publish_saga_event("transfer.step.sas_generated", {
            "transfer_id": self.transfer_id,
            "document_count": len(self.sas_urls)
        })
        
        logger.info(f"✅ [Saga {self.transfer_id}] SAS URLs generated: {len(self.sas_urls)}")
    
    async def _step_send_transfer(self):
        """Step 2: Send transfer request to destination operator."""
        logger.info(f"📤 [Saga {self.transfer_id}] Step 2: Sending transfer request")
        
        # Acquire distributed lock
        try:
            from carpeta_common.redis_client import acquire_lock, release_lock
            lock_key = f"lock:transfer:{self.citizen_id}"
            token = await acquire_lock(lock_key, ttl=300)  # 5 min
            
            if not token:
                raise Exception("Failed to acquire transfer lock")
            
            try:
                # TODO: HTTP POST to destination_url with circuit breaker
                # For now, mock success
                await asyncio.sleep(0.1)  # Simulate network call
                
                self.current_step = SagaStep.TRANSFER_SENT
                await self._publish_saga_event("transfer.step.sent", {
                    "transfer_id": self.transfer_id,
                    "destination": self.destination_operator
                })
                
                logger.info(f"✅ [Saga {self.transfer_id}] Transfer request sent")
                
            finally:
                await release_lock(lock_key, token)
                
        except ImportError:
            # No Redis, proceed without lock
            logger.warning("Redis not available, skipping lock")
            await asyncio.sleep(0.1)
            self.current_step = SagaStep.TRANSFER_SENT
    
    async def _step_wait_confirmation(self):
        """Step 3: Wait for confirmation from destination.
        
        In real implementation, this would be:
        - Webhook callback
        - Polling
        - Service Bus event subscription
        """
        logger.info(f"⏳ [Saga {self.transfer_id}] Step 3: Waiting for confirmation")
        
        # TODO: Implement actual confirmation wait
        # For now, mock immediate confirmation
        await asyncio.sleep(0.5)
        
        self.confirmation_received = True
        self.current_step = SagaStep.CONFIRMED
        
        await self._publish_saga_event("transfer.step.confirmed", {
            "transfer_id": self.transfer_id
        })
        
        logger.info(f"✅ [Saga {self.transfer_id}] Confirmation received")
    
    async def _step_delete_source(self):
        """Step 4: Delete source data (no compensation for this step)."""
        logger.info(f"🗑️  [Saga {self.transfer_id}] Step 4: Deleting source data")
        
        # Acquire lock for deletion
        try:
            from carpeta_common.redis_client import acquire_lock, release_lock
            lock_key = f"lock:delete:{self.citizen_id}"
            token = await acquire_lock(lock_key, ttl=120)
            
            if not token:
                raise Exception("Failed to acquire delete lock")
            
            try:
                # TODO: Delete from database
                # TODO: Delete from blob storage
                # For now, mock
                await asyncio.sleep(0.1)
                
                self.current_step = SagaStep.SOURCE_DELETED
                await self._publish_saga_event("transfer.step.source_deleted", {
                    "transfer_id": self.transfer_id,
                    "citizen_id": self.citizen_id
                })
                
                logger.info(f"✅ [Saga {self.transfer_id}] Source data deleted")
                
            finally:
                await release_lock(lock_key, token)
                
        except ImportError:
            # No Redis
            await asyncio.sleep(0.1)
            self.current_step = SagaStep.SOURCE_DELETED
    
    async def _compensate(self):
        """Execute compensation actions in reverse order."""
        logger.warning(f"🔄 [Saga {self.transfer_id}] Starting compensation")
        
        self.state = SagaState.COMPENSATING
        
        # Execute compensations in reverse order
        for action in reversed(self.compensation_actions):
            try:
                await self._execute_compensation(action)
            except Exception as e:
                logger.error(f"Compensation action failed: {e}")
        
        self.state = SagaState.COMPENSATED
        self.current_step = SagaStep.COMPENSATED
        
        await self._publish_saga_event("transfer.saga.compensated", {
            "transfer_id": self.transfer_id,
            "error": self.error
        })
        
        logger.info(f"✅ [Saga {self.transfer_id}] Compensation completed")
    
    async def _execute_compensation(self, action: Dict[str, Any]):
        """Execute a compensation action."""
        action_type = action.get("action")
        
        if action_type == "revoke_sas":
            # Revoke SAS URLs (in Azure, SAS can't be revoked, just expire)
            # In practice: update database to mark as invalid
            logger.info(f"🔄 Compensating: revoke SAS URLs")
            # TODO: Mark SAS as revoked in DB
        
        # Add more compensation actions as needed
    
    async def _publish_saga_event(self, event_type: str, data: Dict[str, Any]):
        """Publish saga event to Service Bus."""
        try:
            from carpeta_common.bus import ServiceBusClient
            bus = ServiceBusClient()
            
            await bus.publish_event(
                queue_name="transfer-saga-events",  # Dedicated saga queue
                event_type=event_type,
                data=data
            )
        except Exception as e:
            logger.warning(f"Failed to publish saga event: {e}")

