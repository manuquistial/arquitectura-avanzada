"""Azure Service Bus client with CQRS event publishing/consuming.

Provides async pub/sub with DLQ, retries, and idempotency.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, Optional
import uuid

logger = logging.getLogger(__name__)

# Try to import Azure Service Bus
try:
    from azure.servicebus.aio import ServiceBusClient, ServiceBusMessage
    from azure.servicebus import ServiceBusReceiveMode
    from azure.core.exceptions import ServiceBusError
    AZURE_SB_AVAILABLE = True
except ImportError:
    AZURE_SB_AVAILABLE = False
    logger.warning("⚠️  azure-servicebus not installed, using mock mode")

# Import Redis for idempotency
try:
    from carpeta_common.redis_client import setnx
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("⚠️  Redis not available, idempotency disabled")


class ServiceBusClient:
    """Azure Service Bus async client with idempotency and DLQ."""
    
    # Queue names (CQRS events) - Standardized across all services
    QUEUE_CITIZEN_REGISTERED = "citizen-events"
    QUEUE_DOCUMENT_UPLOADED = "document-events"
    QUEUE_DOCUMENT_AUTHENTICATED = "document-events"
    QUEUE_DOCUMENT_SIGNED = "document-events"
    QUEUE_DOCUMENT_DELETED = "document-events"
    QUEUE_SIGNATURE_COMPLETED = "signature-events"
    QUEUE_SIGNATURE_FAILED = "signature-events"
    QUEUE_TRANSFER_REQUESTED = "transfer-events"
    QUEUE_TRANSFER_CONFIRMED = "transfer-events"
    QUEUE_TRANSFER_NOTIFICATIONS = "transfer-notifications"
    
    def __init__(self, connection_string: Optional[str] = None):
        """Initialize Service Bus client.
        
        Args:
            connection_string: Azure Service Bus connection string
                              (if None, uses SERVICEBUS_CONNECTION env var)
        """
        self.connection_string = connection_string or os.getenv("SERVICEBUS_CONNECTION_STRING", "")
        self.use_mock = not AZURE_SB_AVAILABLE or not self.connection_string
        self.client = None
        
        if not self.use_mock:
            self._init_client()
        else:
            logger.info("📨 Using MOCK Service Bus (events logged only)")
    
    def _init_client(self):
        """Initialize Azure Service Bus client."""
        try:
            from azure.servicebus.aio import ServiceBusClient as AzureClient
            self.client = AzureClient.from_connection_string(
                self.connection_string,
                logging_enable=True
            )
            logger.info("✅ Azure Service Bus client initialized")
        except Exception as e:
            logger.error(f"❌ Service Bus init failed: {e}, using mock")
            self.use_mock = True
    
    async def publish_event(
        self,
        queue_name: str,
        event_type: str,
        data: Dict[str, Any],
        event_id: Optional[str] = None,
        deduplicate: bool = True
    ) -> str:
        """Publish event to queue with idempotency.
        
        Args:
            queue_name: Target queue name
            event_type: Event type (e.g., 'citizen.registered')
            data: Event payload
            event_id: Optional event ID (auto-generated if not provided)
            deduplicate: Enable Redis deduplication
            
        Returns:
            Event ID
        """
        # Generate event ID if not provided
        if not event_id:
            event_id = str(uuid.uuid4())
        
        # Redis idempotency check
        if deduplicate and REDIS_AVAILABLE:
            idempotency_key = f"event:{event_id}"
            is_new = await setnx(idempotency_key, "1", ttl=600)  # 10 min
            
            if not is_new:
                logger.warning(f"⚠️  Duplicate event skipped: {event_id}")
                return event_id
        
        # Build message
        message_body = {
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        if self.use_mock:
            self._log_mock_event(queue_name, message_body)
        else:
            await self._publish_to_servicebus(queue_name, message_body)
        
        return event_id
    
    def _log_mock_event(self, queue_name: str, message: Dict[str, Any]):
        """Log event in mock mode."""
        logger.info(
            f"📨 [MOCK EVENT] Queue={queue_name} | "
            f"Type={message['event_type']} | "
            f"EventID={message['event_id']}"
        )
    
    async def _publish_to_servicebus(self, queue_name: str, message: Dict[str, Any]):
        """Publish to Azure Service Bus."""
        try:
            async with self.client:
                sender = self.client.get_queue_sender(queue_name=queue_name)
                
                async with sender:
                    sb_message = ServiceBusMessage(
                        json.dumps(message),
                        content_type="application/json",
                        message_id=message["event_id"]
                    )
                    
                    await sender.send_messages(sb_message)
                    
            logger.info(f"✅ Event published: {queue_name} | {message['event_type']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish to Service Bus: {e}")
            # Fallback to mock
            self._log_mock_event(queue_name, message)
    
    async def consume_queue(
        self,
        queue_name: str,
        handler: Callable[[Dict[str, Any]], Any],
        max_messages: int = 10,
        max_wait_time: int = 30
    ):
        """Consume messages from queue with DLQ and retries.
        
        Args:
            queue_name: Queue to consume from
            handler: Async function to process each message
            max_messages: Max messages per batch
            max_wait_time: Max wait time for messages (seconds)
        """
        if self.use_mock:
            logger.info(f"📭 [MOCK] Consumer started for {queue_name}")
            return
        
        try:
            async with self.client:
                receiver = self.client.get_queue_receiver(
                    queue_name=queue_name,
                    max_wait_time=max_wait_time,
                    receive_mode=ServiceBusReceiveMode.PEEK_LOCK
                )
                
                async with receiver:
                    logger.info(f"📭 Consumer started: {queue_name}")
                    
                    messages = []
                    async for msg in receiver:
                        messages.append(msg)
                        
                        if len(messages) >= max_messages:
                            break
                    
                    # Process batch
                    for msg in messages:
                        try:
                            # Parse message
                            event = json.loads(str(msg))
                            event_id = event.get("event_id")
                            
                            # Check idempotency with Redis
                            if REDIS_AVAILABLE and event_id:
                                processing_key = f"processing:{event_id}"
                                is_new = await setnx(processing_key, "1", ttl=600)
                                
                                if not is_new:
                                    logger.warning(f"⚠️  Duplicate event in processing: {event_id}")
                                    await receiver.complete_message(msg)
                                    continue
                            
                            # Process message
                            await handler(event)
                            
                            # Complete (acknowledge)
                            await receiver.complete_message(msg)
                            logger.info(f"✅ Message processed: {event_id}")
                            
                        except Exception as e:
                            logger.error(f"❌ Error processing message: {e}")
                            
                            # Check delivery count
                            if msg.delivery_count >= 3:
                                # Send to DLQ
                                await receiver.dead_letter_message(
                                    msg,
                                    reason="MaxDeliveryCountExceeded",
                                    error_description=str(e)
                                )
                                logger.error(f"💀 Message sent to DLQ after 3 retries")
                            else:
                                # Abandon for retry (exponential backoff by Service Bus)
                                await receiver.abandon_message(msg)
                                logger.warning(f"🔄 Message abandoned, retry {msg.delivery_count}/3")
                    
        except Exception as e:
            logger.error(f"❌ Consumer error: {e}")
    
    async def close(self):
        """Close Service Bus client."""
        if self.client and not self.use_mock:
            await self.client.close()
            logger.info("Service Bus client closed")


# =============================================================================
# Helper functions for specific events
# =============================================================================

async def publish_citizen_registered(citizen_id: int, name: str, email: str, operator_id: str) -> str:
    """Publish citizen.registered event."""
    bus = ServiceBusClient()
    return await bus.publish_event(
        queue_name=ServiceBusClient.QUEUE_CITIZEN_REGISTERED,
        event_type="citizen.registered",
        data={
            "citizen_id": citizen_id,
            "name": name,
            "email": email,
            "operator_id": operator_id
        }
    )


async def publish_document_uploaded(document_id: str, citizen_id: int, filename: str, sha256_hash: str) -> str:
    """Publish document.uploaded event."""
    bus = ServiceBusClient()
    return await bus.publish_event(
        queue_name=ServiceBusClient.QUEUE_DOCUMENT_UPLOADED,
        event_type="document.uploaded",
        data={
            "document_id": document_id,
            "citizen_id": citizen_id,
            "filename": filename,
            "sha256_hash": sha256_hash
        }
    )


async def publish_document_signed(document_id: str, citizen_id: int, sha256_hash: str) -> str:
    """Publish document.signed event."""
    bus = ServiceBusClient()
    return await bus.publish_event(
        queue_name=ServiceBusClient.QUEUE_DOCUMENT_SIGNED,
        event_type="document.signed",
        data={
            "document_id": document_id,
            "citizen_id": citizen_id,
            "sha256_hash": sha256_hash
        }
    )


async def publish_document_deleted(document_id: str, citizen_id: int) -> str:
    """Publish document.deleted event."""
    bus = ServiceBusClient()
    return await bus.publish_event(
        queue_name=ServiceBusClient.QUEUE_DOCUMENT_DELETED,
        event_type="document.deleted",
        data={
            "document_id": document_id,
            "citizen_id": citizen_id
        }
    )


async def publish_signature_completed(document_id: str, citizen_id: int, success: bool) -> str:
    """Publish signature.completed event."""
    bus = ServiceBusClient()
    return await bus.publish_event(
        queue_name=ServiceBusClient.QUEUE_SIGNATURE_COMPLETED,
        event_type="signature.completed",
        data={
            "document_id": document_id,
            "citizen_id": citizen_id,
            "success": success
        }
    )


async def publish_signature_failed(document_id: str, citizen_id: int, error: str) -> str:
    """Publish signature.failed event."""
    bus = ServiceBusClient()
    return await bus.publish_event(
        queue_name=ServiceBusClient.QUEUE_SIGNATURE_FAILED,
        event_type="signature.failed",
        data={
            "document_id": document_id,
            "citizen_id": citizen_id,
            "error": error
        }
    )


async def publish_document_authenticated(
    document_id: str,
    citizen_id: int,
    sha256_hash: str,
    hub_success: bool
) -> str:
    """Publish document.authenticated event."""
    bus = ServiceBusClient()
    return await bus.publish_event(
        queue_name=ServiceBusClient.QUEUE_DOCUMENT_AUTHENTICATED,
        event_type="document.authenticated",
        data={
            "document_id": document_id,
            "citizen_id": citizen_id,
            "sha256_hash": sha256_hash,
            "hub_success": hub_success
        }
    )


async def publish_transfer_requested(
    transfer_id: int,
    citizen_id: int,
    source_operator: str,
    destination_operator: str
) -> str:
    """Publish transfer.requested event."""
    bus = ServiceBusClient()
    return await bus.publish_event(
        queue_name=ServiceBusClient.QUEUE_TRANSFER_REQUESTED,
        event_type="transfer.requested",
        data={
            "transfer_id": transfer_id,
            "citizen_id": citizen_id,
            "source_operator": source_operator,
            "destination_operator": destination_operator
        }
    )


async def publish_transfer_confirmed(
    transfer_id: int,
    citizen_id: int,
    success: bool
) -> str:
    """Publish transfer.confirmed event."""
    bus = ServiceBusClient()
    return await bus.publish_event(
        queue_name=ServiceBusClient.QUEUE_TRANSFER_CONFIRMED,
        event_type="transfer.confirmed",
        data={
            "transfer_id": transfer_id,
            "citizen_id": citizen_id,
            "success": success
        }
    )

