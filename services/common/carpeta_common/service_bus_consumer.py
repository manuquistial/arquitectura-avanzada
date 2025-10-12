"""
Advanced Service Bus Consumer with:
- Exponential backoff on transient errors
- Dead Letter Queue (DLQ) handling
- Delivery count tracking
- Metrics for retries and DLQ
"""

import asyncio
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
except ImportError:
    AZURE_SB_AVAILABLE = False
    logger.warning("⚠️  azure-servicebus not installed")

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
    TRANSIENT_ERRORS = (
        ServiceBusConnectionError,
        TimeoutError,
        ConnectionError,
    )
    
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
        if not AZURE_SB_AVAILABLE:
            logger.error("Azure Service Bus not available")
            return
        
        try:
            self.client = ServiceBusClient.from_connection_string(
                self.connection_string,
                logging_enable=True
            )
            self.receiver = self.client.get_queue_receiver(
                queue_name=self.queue_name,
                receive_mode=ServiceBusReceiveMode.PEEK_LOCK
            )
            logger.info(f"✅ Service Bus consumer started for queue: {self.queue_name}")
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
        description: str
    ):
        """
        Send message to Dead Letter Queue.
        
        Args:
            message: The message to dead-letter
            reason: Short reason code
            description: Detailed description
        """
        try:
            await self.receiver.dead_letter_message(
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
        handler: Callable[[Dict[str, Any]], Any]
    ) -> bool:
        """
        Process a single message with retry logic.
        
        Args:
            message: The Service Bus message
            handler: Async function to process message body
            
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
                description=f"Message exceeded max delivery count of {self.max_delivery_count}"
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
                await self.receiver.complete_message(message)
                
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
                    description=f"Failed to parse JSON: {str(e)}"
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
            await self.receiver.abandon_message(message)
            logger.warning(f"Message {message_id} abandoned for redelivery")
        except Exception as e:
            logger.error(f"Failed to abandon message {message_id}: {e}")
        
        # Check if we should send to DLQ based on delivery count
        if delivery_count + 1 >= self.max_delivery_count:
            await self.send_to_dlq(
                message,
                reason="ProcessingFailed",
                description=f"Failed after {delivery_count + 1} attempts: {str(last_error)}"
            )
        
        return False
    
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
        if not self.receiver:
            logger.error("Consumer not started. Call start() first.")
            return
        
        logger.info(f"🎧 Starting to consume messages from {self.queue_name}")
        
        try:
            while True:
                messages = await self.receiver.receive_messages(
                    max_message_count=max_messages,
                    max_wait_time=max_wait_time
                )
                
                if not messages:
                    logger.debug("No messages received, waiting...")
                    await asyncio.sleep(5)
                    continue
                
                for message in messages:
                    await self.process_message(message, handler)
                    
        except asyncio.CancelledError:
            logger.info("Consumer cancelled")
        except Exception as e:
            logger.error(f"Error in consume loop: {e}", exc_info=True)
    
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

