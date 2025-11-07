"""Service Bus event consumers for notification operations."""

import logging
from typing import Dict, Any

from carpeta_common.service_bus_consumer import ServiceBusConsumer
from app.config import get_config
from app.processors import NotificationEventProcessor

logger = logging.getLogger(__name__)

config = get_config()
processor = NotificationEventProcessor()


async def handle_citizen_event(event_data: Dict[str, Any]) -> None:
    """Handle citizen event from Service Bus.
    
    Routes events to appropriate processor based on event_type.
    
    Args:
        event_data: Event data from Service Bus
    """
    event_type = event_data.get("event_type", "")
    
    logger.info(f"📨 Received event: {event_type}")
    
    try:
        # Route to appropriate processor
        if event_type == "citizen.registered":
            await processor.process_citizen_registered(event_data)
        else:
            logger.warning(f"⚠️  Unknown citizen event type: {event_type}, ignoring")
    
    except Exception as e:
        logger.error(f"❌ Error handling citizen event {event_type}: {e}", exc_info=True)
        raise  # Re-raise to trigger retry/DLQ


async def start_notification_consumer() -> None:
    """Start Service Bus consumer for citizen events."""
    if not config.servicebus_enabled:
        logger.warning("⚠️  Service Bus disabled, consumer will not start")
        return
    
    if not config.servicebus_connection_string:
        logger.warning("⚠️  Service Bus connection string not configured, consumer will not start")
        return
    
    queue_name = config.citizen_events_queue
    logger.info(f"🚀 Starting Notification Service consumer for queue: {queue_name}")
    
    try:
        consumer = ServiceBusConsumer(
            connection_string=config.servicebus_connection_string,
            queue_name=queue_name,
            max_delivery_count=5,
            initial_backoff=1.0,
            max_backoff=60.0,
            backoff_multiplier=2.0
        )
        
        await consumer.start()
        # Guard: if client was not initialized (library unavailable), skip consume
        if not getattr(consumer, "client", None):
            logger.warning("⚠️  Service Bus client not initialized; consumer will not run")
            return
        logger.info("✅ Notification Service consumer started successfully")
        
        # Start consuming
        await consumer.consume(
            handler=handle_citizen_event,
            max_messages=config.max_messages_per_batch,
            max_wait_time=config.max_wait_time
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start consumer: {e}", exc_info=True)
        raise

