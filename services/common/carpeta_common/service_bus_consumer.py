"""
Advanced Service Bus Consumer with:
- Exponential backoff on transient errors
- Dead Letter Queue (DLQ) handling
- Delivery count tracking
- Metrics for retries and DLQ
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import Azure Service Bus
try:
    from azure.servicebus.aio import ServiceBusClient, ServiceBusReceiver
    from azure.servicebus import ServiceBusReceiveMode, ServiceBusReceivedMessage
    from azure.core.exceptions import ServiceBusError, ServiceBusConnectionError
    AZURE_SB_AVAILABLE = True
    # Define transient errors when Azure SB is available
    TRANSIENT_ERROR_TYPES = (
        ServiceBusConnectionError,
        TimeoutError,
        ConnectionError,
    )
except ImportError:
    AZURE_SB_AVAILABLE = False
    # Downgrade severity and make message explicit; consumer is optional
    logger.warning("⚠️  azure-servicebus not installed; Service Bus features disabled")
    # Define transient errors without Azure SB (using base exceptions)
    TRANSIENT_ERROR_TYPES = (
        TimeoutError,
        ConnectionError,
    )

def _try_enable_azure_sb() -> bool:
    """Attempt a lazy import at runtime to enable Azure Service Bus if available."""
    global AZURE_SB_AVAILABLE
    if AZURE_SB_AVAILABLE:
        return True
    try:
        # Re-attempt import lazily; environments may differ between build/runtime
        from azure.servicebus.aio import ServiceBusClient as _SBClient  # noqa: F401
        from azure.servicebus import ServiceBusReceiveMode as _SBMode  # noqa: F401
        from azure.core.exceptions import ServiceBusError as _SBE, ServiceBusConnectionError as _SBCE  # noqa: F401
        AZURE_SB_AVAILABLE = True
    except Exception:
        AZURE_SB_AVAILABLE = False
    return AZURE_SB_AVAILABLE

# Metrics
CONSUMER_METRICS = {
    "retries": 0,
    "dlq_count": 0,
    "success": 0,
    "errors": 0,
    "transient_errors": 0,
}


class ServiceBusConsumer:
    """
    Advanced Service Bus consumer with retry logic and DLQ handling.
    """
    
    # Transient error types that should be retried
    TRANSIENT_ERRORS = TRANSIENT_ERROR_TYPES
    
    def __init__(
        self,
        connection_string: str,
        queue_name: str,
        max_delivery_count: int = 5,
        initial_backoff: float = 1.0,
        max_backoff: float = 60.0,
        backoff_multiplier: float = 2.0,
    ):
        """
        Initialize Service Bus consumer.
        
        Args:
            connection_string: Azure Service Bus connection string
            queue_name: Queue name to consume from
            max_delivery_count: Max delivery attempts before sending to DLQ
            initial_backoff: Initial backoff time in seconds
            max_backoff: Maximum backoff time in seconds
            backoff_multiplier: Backoff multiplier for exponential backoff
        """
        self.connection_string = connection_string
        self.queue_name = queue_name
        self.max_delivery_count = max_delivery_count
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier
        
        self.client: Optional[ServiceBusClient] = None
        self.receiver: Optional[ServiceBusReceiver] = None
    
    async def start(self):
        """Start the consumer."""
        try:
            # Import inside to ensure availability at runtime
            from azure.servicebus.aio import ServiceBusClient as _RuntimeSBClient
            # Initialize client; if import fails, it will be caught below
            self.client = _RuntimeSBClient.from_connection_string(
                self.connection_string,
                logging_enable=True
            )
            # Use context manager approach to avoid metadata attribute conflicts
            # The receiver will be created as a context manager in consume()
            logger.info(f"✅ Service Bus consumer client initialized for queue: {self.queue_name}")
        except ImportError:
            logger.warning("⚠️  azure-servicebus not installed; skipping consumer start")
            return
        except Exception as e:
            logger.error(f"❌ Failed to start consumer: {e}")
            raise
    
    async def stop(self):
        """Stop the consumer."""
        if self.receiver:
            await self.receiver.close()
        if self.client:
            await self.client.close()
        logger.info(f"Service Bus consumer stopped for queue: {self.queue_name}")
    
    def calculate_backoff(self, retry_count: int) -> float:
        """
        Calculate exponential backoff time.
        
        Args:
            retry_count: Current retry attempt number
            
        Returns:
            Backoff time in seconds
        """
        backoff = self.initial_backoff * (self.backoff_multiplier ** retry_count)
        return min(backoff, self.max_backoff)
    
    async def send_to_dlq(
        self,
        message: 'ServiceBusReceivedMessage',
        reason: str,
        description: str,
        receiver: Optional['ServiceBusReceiver'] = None
    ):
        """
        Send message to Dead Letter Queue.
        
        Args:
            message: The message to dead-letter
            reason: Short reason code
            description: Detailed description
            receiver: The Service Bus receiver (optional, for compatibility)
        """
        try:
            # Use receiver parameter if provided, otherwise fallback to self.receiver (for compatibility)
            target_receiver = receiver or self.receiver
            if not target_receiver:
                logger.error("❌ No receiver available to send message to DLQ")
                return
                
            await target_receiver.dead_letter_message(
                message,
                reason=reason,
                error_description=description
            )
            CONSUMER_METRICS["dlq_count"] += 1
            logger.warning(
                f"📮 Message sent to DLQ. Reason: {reason}, "
                f"Description: {description}, "
                f"Message ID: {message.message_id}"
            )
        except Exception as e:
            logger.error(f"❌ Failed to send message to DLQ: {e}")
    
    def is_transient_error(self, error: Exception) -> bool:
        """
        Check if error is transient and should be retried.
        
        Args:
            error: The exception to check
            
        Returns:
            True if error is transient
        """
        return isinstance(error, self.TRANSIENT_ERRORS)
    
    async def process_message(
        self,
        message: 'ServiceBusReceivedMessage',
        handler: Callable[[Dict[str, Any]], Any],
        receiver: 'ServiceBusReceiver'
    ) -> bool:
        """
        Process a single message with retry logic.
        
        Args:
            message: The Service Bus message
            handler: Async function to process message body
            receiver: The Service Bus receiver (passed from consume context)
            
        Returns:
            True if processed successfully, False otherwise
        """
        delivery_count = message.delivery_count or 0
        message_id = message.message_id
        
        logger.info(
            f"📨 Processing message {message_id}, "
            f"delivery count: {delivery_count}/{self.max_delivery_count}"
        )
        
        # Check if delivery count exceeded
        if delivery_count >= self.max_delivery_count:
            await self.send_to_dlq(
                message,
                reason="MaxDeliveryCountExceeded",
                description=f"Message exceeded max delivery count of {self.max_delivery_count}",
                receiver=receiver
            )
            return False
        
        retry_count = 0
        last_error = None
        
        while retry_count < 3:  # Internal retry loop for transient errors
            try:
                # Parse message body
                body = message.body
                if isinstance(body, bytes):
                    body = body.decode('utf-8')
                
                data = json.loads(body) if isinstance(body, str) else body
                
                # Call handler
                await handler(data)
                
                # Complete message (remove from queue)
                await receiver.complete_message(message)
                
                CONSUMER_METRICS["success"] += 1
                logger.info(f"✅ Message {message_id} processed successfully")
                return True
                
            except self.TRANSIENT_ERRORS as e:
                # Transient error - retry with backoff
                retry_count += 1
                last_error = e
                CONSUMER_METRICS["transient_errors"] += 1
                CONSUMER_METRICS["retries"] += 1
                
                if retry_count < 3:
                    backoff = self.calculate_backoff(retry_count)
                    logger.warning(
                        f"⚠️  Transient error on message {message_id}: {e}. "
                        f"Retrying in {backoff:.2f}s (attempt {retry_count}/3)"
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        f"❌ Max transient retries exceeded for message {message_id}"
                    )
                    
            except json.JSONDecodeError as e:
                # Malformed message - send to DLQ immediately
                logger.error(f"❌ JSON decode error on message {message_id}: {e}")
                await self.send_to_dlq(
                    message,
                    reason="MalformedMessage",
                    description=f"Failed to parse JSON: {str(e)}",
                    receiver=receiver
                )
                return False
                
            except Exception as e:
                # Non-transient error - log and abandon
                logger.error(
                    f"❌ Error processing message {message_id}: {e}",
                    exc_info=True
                )
                last_error = e
                CONSUMER_METRICS["errors"] += 1
                break
        
        # If we got here, processing failed
        # Abandon message so it can be redelivered
        try:
            await receiver.abandon_message(message)
            logger.warning(f"Message {message_id} abandoned for redelivery")
        except Exception as e:
            logger.error(f"Failed to abandon message {message_id}: {e}")
        
        # Check if we should send to DLQ based on delivery count
        if delivery_count + 1 >= self.max_delivery_count:
            await self.send_to_dlq(
                message,
                reason="ProcessingFailed",
                description=f"Failed after {delivery_count + 1} attempts: {str(last_error)}",
                receiver=receiver
            )
        
        return False
    
    def _has_entity_path_in_connection_string(self) -> bool:
        """
        Check if the connection string contains EntityPath.
        
        Returns:
            True if EntityPath is present in connection string
        """
        return "EntityPath=" in self.connection_string
    
    def _extract_entity_path_from_connection_string(self) -> Optional[str]:
        """
        Extract EntityPath from connection string if present.
        
        Returns:
            EntityPath value if present, None otherwise
        """
        if not self._has_entity_path_in_connection_string():
            return None
        
        # Parse connection string to extract EntityPath
        # Format: ...;EntityPath=queue-name;...
        parts = self.connection_string.split(';')
        for part in parts:
            if part.startswith('EntityPath='):
                return part.split('=', 1)[1]
        return None
    
    async def consume(
        self,
        handler: Callable[[Dict[str, Any]], Any],
        max_messages: int = 1,
        max_wait_time: float = 60.0
    ):
        """
        Consume messages from the queue.
        
        Args:
            handler: Async function to process message body
            max_messages: Max messages to receive per batch
            max_wait_time: Max wait time for messages in seconds
        """
        if not self.client:
            logger.error("Consumer not started. Call start() first.")
            return
        
        logger.info(f"🎧 Starting to consume messages from {self.queue_name}")
        
        try:
            async with self.client:
                # Check if connection string has EntityPath
                # If it does, don't pass queue_name to get_queue_receiver
                # because the EntityPath in the connection string already specifies the queue
                has_entity_path = self._has_entity_path_in_connection_string()
                
                if has_entity_path:
                    # Extract EntityPath from connection string and use it as queue_name
                    # Azure Service Bus requires queue_name to match EntityPath when present
                    entity_path = self._extract_entity_path_from_connection_string()
                    if entity_path:
                        logger.debug(f"Connection string has EntityPath={entity_path}, using it as queue_name")
                        queue_name_to_use = entity_path
                    else:
                        # Fallback to self.queue_name if extraction fails
                        logger.warning(f"Could not extract EntityPath from connection string, using self.queue_name")
                        queue_name_to_use = self.queue_name
                    
                    # Create receiver with EntityPath as queue_name (must match EntityPath in connection string)
                    async with self.client.get_queue_receiver(
                        queue_name=queue_name_to_use,
                        receive_mode=ServiceBusReceiveMode.PEEK_LOCK
                    ) as receiver:
                        while True:
                            try:
                                messages = await receiver.receive_messages(
                                    max_message_count=max_messages,
                                    max_wait_time=max_wait_time
                                )
                                
                                if not messages:
                                    logger.debug("No messages received, waiting...")
                                    await asyncio.sleep(5)
                                    continue
                                
                                for message in messages:
                                    await self.process_message(message, handler, receiver)
                                    
                            except asyncio.CancelledError:
                                logger.info("Consumer cancelled")
                                break
                            except Exception as e:
                                logger.error(f"Error in consume loop: {e}", exc_info=True)
                                await asyncio.sleep(1)  # Brief pause before retry
                else:
                    # Connection string doesn't have EntityPath, use queue_name parameter
                    async with self.client.get_queue_receiver(
                        queue_name=self.queue_name,
                        receive_mode=ServiceBusReceiveMode.PEEK_LOCK
                    ) as receiver:
                        while True:
                            try:
                                messages = await receiver.receive_messages(
                                    max_message_count=max_messages,
                                    max_wait_time=max_wait_time
                                )
                                
                                if not messages:
                                    logger.debug("No messages received, waiting...")
                                    await asyncio.sleep(5)
                                    continue
                                
                                for message in messages:
                                    await self.process_message(message, handler, receiver)
                                    
                            except asyncio.CancelledError:
                                logger.info("Consumer cancelled")
                                break
                            except Exception as e:
                                logger.error(f"Error in consume loop: {e}", exc_info=True)
                                await asyncio.sleep(1)  # Brief pause before retry
                    
        except asyncio.CancelledError:
            logger.info("Consumer cancelled")
        except Exception as e:
            logger.error(f"Error in consume: {e}", exc_info=True)
    
    def get_metrics(self) -> Dict[str, int]:
        """Get consumer metrics."""
        return CONSUMER_METRICS.copy()


# Backward compatibility wrapper
class MessageBrokerConsumer:
    """Wrapper for backward compatibility."""
    
    def __init__(self, connection_string: str, queue_name: str):
        self.consumer = ServiceBusConsumer(connection_string, queue_name)
    
    async def start(self):
        await self.consumer.start()
    
    async def stop(self):
        await self.consumer.stop()
    
    async def consume(self, handler: Callable):
        await self.consumer.consume(handler)
    
    def get_metrics(self):
        return self.consumer.get_metrics()

