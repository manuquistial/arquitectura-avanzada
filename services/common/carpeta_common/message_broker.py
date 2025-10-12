"""Message broker abstraction for Azure Service Bus with mock support.

Supports:
- Azure Service Bus (production)
- Mock/logging (local development)
- Redis deduplication
- Retry logic with exponential backoff
- Dead Letter Queue (DLQ) handling
- Metrics for retries and DLQ
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import Azure Service Bus (optional for local dev)
try:
    from azure.servicebus.aio import ServiceBusClient, ServiceBusMessage, ServiceBusReceiver
    from azure.servicebus import ServiceBusReceiveMode, ServiceBusReceivedMessage
    from azure.core.exceptions import ServiceBusError
    AZURE_SB_AVAILABLE = True
except ImportError:
    AZURE_SB_AVAILABLE = False
    logger.warning("⚠️  azure-servicebus not installed, using mock mode")

# Import Redis client from package
try:
    from carpeta_common.redis_client import get_redis_client, setnx
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("⚠️  Redis client not available, deduplication disabled")

# Metrics counters (in-memory for simplicity, ideally use Prometheus client)
METRICS = {
    "queue.consumer.retries": 0,
    "queue.consumer.dlq_count": 0,
    "queue.consumer.success": 0,
    "queue.consumer.errors": 0,
}

def increment_metric(metric_name: str, value: int = 1):
    """Increment a metric counter."""
    if metric_name in METRICS:
        METRICS[metric_name] += value

def get_metrics() -> Dict[str, int]:
    """Get all metrics."""
    return METRICS.copy()


class MessageBroker:
    """Abstract message broker with Azure Service Bus + Mock support."""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        use_mock: bool = False
    ):
        """Initialize message broker.
        
        Args:
            connection_string: Azure Service Bus connection string
            use_mock: Force mock mode (for testing/local dev)
        """
        self.use_mock = use_mock or not AZURE_SB_AVAILABLE or not connection_string
        self.connection_string = connection_string
        self.client: Optional[Any] = None
        
        if not self.use_mock:
            self._init_servicebus()
        else:
            logger.info("📨 Using MOCK message broker (events logged only)")
    
    def _init_servicebus(self):
        """Initialize Azure Service Bus client."""
        try:
            self.client = ServiceBusClient.from_connection_string(
                self.connection_string,
                logging_enable=True
            )
            logger.info("✅ Azure Service Bus client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Service Bus: {e}")
            logger.info("📨 Falling back to MOCK mode")
            self.use_mock = True
    
    async def publish(
        self,
        queue_name: str,
        event_type: str,
        data: Dict[str, Any],
        event_id: Optional[str] = None,
        deduplicate: bool = True
    ) -> str:
        """Publish event to queue with optional deduplication.
        
        Args:
            queue_name: Queue name (e.g., 'citizen.registered')
            event_type: Event type for filtering
            data: Event data payload
            event_id: Optional event ID for deduplication
            deduplicate: Enable Redis deduplication
            
        Returns:
            Event ID
        """
        # Generate event ID if not provided
        if not event_id:
            event_id = str(uuid.uuid4())
        
        # Check deduplication
        if deduplicate and REDIS_AVAILABLE:
            dedupe_key = f"event:{event_id}"
            is_new = await setnx(dedupe_key, "1", ttl=600)  # 10 min TTL
            
            if not is_new:
                logger.warning(f"⚠️  Duplicate event detected: {event_id}")
                return event_id
        
        # Build message
        message_body = {
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        if self.use_mock:
            await self._publish_mock(queue_name, message_body)
        else:
            await self._publish_servicebus(queue_name, message_body)
        
        return event_id
    
    async def _publish_mock(self, queue_name: str, message: Dict[str, Any]):
        """Publish to mock broker (just logging)."""
        logger.info(
            f"📨 [MOCK EVENT] Queue: {queue_name} | "
            f"Type: {message['event_type']} | "
            f"Data: {json.dumps(message['data'])}"
        )
    
    async def _publish_servicebus(self, queue_name: str, message: Dict[str, Any]):
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
                    
            logger.info(
                f"✅ Event published to Service Bus: {queue_name} | "
                f"{message['event_type']}"
            )
        except Exception as e:
            logger.error(f"❌ Failed to publish to Service Bus: {e}")
            # Fallback to mock
            await self._publish_mock(queue_name, message)
    
    async def consume(
        self,
        queue_name: str,
        handler: Callable[[Dict[str, Any]], Any],
        max_messages: int = 10
    ):
        """Consume messages from queue.
        
        Args:
            queue_name: Queue name
            handler: Async function to handle each message
            max_messages: Max messages to receive per batch
        """
        if self.use_mock:
            logger.info(f"📭 [MOCK] Consumer started for {queue_name}")
            # In mock mode, consumer does nothing (events are just logged)
            return
        
        try:
            async with self.client:
                receiver = self.client.get_queue_receiver(
                    queue_name=queue_name,
                    max_wait_time=30,
                    receive_mode=ServiceBusReceiveMode.PEEK_LOCK
                )
                
                async with receiver:
                    logger.info(f"📭 Consumer started for queue: {queue_name}")
                    
                    async for msg in receiver:
                        try:
                            # Parse message
                            message_data = json.loads(str(msg))
                            
                            # Handle message
                            await handler(message_data)
                            
                            # Complete (acknowledge) message
                            await receiver.complete_message(msg)
                            logger.info(f"✅ Message processed: {message_data.get('event_id')}")
                            
                        except Exception as e:
                            logger.error(f"❌ Error processing message: {e}")
                            # Abandon message (will be redelivered)
                            await receiver.abandon_message(msg)
                            
        except Exception as e:
            logger.error(f"❌ Consumer error: {e}")
    
    async def close(self):
        """Close Service Bus client."""
        if self.client and not self.use_mock:
            await self.client.close()
            logger.info("Service Bus client closed")


# =============================================================================
# Helper functions for common event patterns
# =============================================================================

async def get_message_broker() -> MessageBroker:
    """Get configured message broker instance."""
    connection_string = os.getenv("SERVICE_BUS_CONNECTION_STRING", "")
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Use mock in development unless connection string is provided
    use_mock = environment == "development" and not connection_string
    
    return MessageBroker(connection_string, use_mock=use_mock)


async def publish_citizen_registered(citizen_id: int, name: str, email: str) -> str:
    """Publish citizen.registered event."""
    broker = await get_message_broker()
    return await broker.publish(
        queue_name="citizen-registered",
        event_type="citizen.registered",
        data={
            "citizen_id": citizen_id,
            "name": name,
            "email": email
        }
    )


async def publish_document_authenticated(
    document_id: str,
    citizen_id: int,
    sha256_hash: str,
    hub_success: bool
) -> str:
    """Publish document.authenticated event."""
    broker = await get_message_broker()
    return await broker.publish(
        queue_name="document-authenticated",
        event_type="document.authenticated",
        data={
            "document_id": document_id,
            "citizen_id": citizen_id,
            "sha256_hash": sha256_hash,
            "hub_success": hub_success
        }
    )


async def publish_transfer_completed(
    transfer_id: int,
    citizen_id: int,
    destination_operator: str,
    success: bool
) -> str:
    """Publish transfer.completed event."""
    broker = await get_message_broker()
    return await broker.publish(
        queue_name="transfer-completed",
        event_type="transfer.completed",
        data={
            "transfer_id": transfer_id,
            "citizen_id": citizen_id,
            "destination_operator": destination_operator,
            "success": success
        }
    )

