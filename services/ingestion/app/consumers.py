"""Service Bus event consumers for document events."""

import logging
from typing import Dict, Any

from carpeta_common.service_bus_consumer import ServiceBusConsumer
from app.config import get_config
from app.processors import DocumentEventProcessor

logger = logging.getLogger(__name__)

config = get_config()
processor = DocumentEventProcessor(config)


async def handle_document_event(event_data: Dict[str, Any]) -> None:
    """Handle document event from Service Bus.
    
    Routes events to appropriate processor based on event_type.
    
    Args:
        event_data: Event data from Service Bus
    """
    event_type = event_data.get("event_type", "")
    
    logger.info(f"📨 Received event: {event_type}")
    
    try:
        # Route to appropriate processor
        if event_type == "document.uploaded":
            await processor.process_document_uploaded(event_data)
        elif event_type == "document.deleted":
            await processor.process_document_deleted(event_data)
        elif event_type == "document.authenticated" or event_type == "document.hubAuthenticated":
            await processor.process_document_authenticated(event_data)
        elif event_type == "document.signed":
            await processor.process_document_signed(event_data)
        elif event_type == "document.verified":
            await processor.process_document_verified(event_data)
        else:
            logger.warning(f"⚠️  Unknown event type: {event_type}, ignoring")
    
    except Exception as e:
        logger.error(f"❌ Error handling document event {event_type}: {e}", exc_info=True)
        raise  # Re-raise to trigger retry/DLQ


async def start_document_consumer() -> None:
    """Start Service Bus consumer for document events."""
    if not config.servicebus_enabled:
        logger.warning("⚠️  Service Bus disabled, consumer will not start")
        return
    
    if not config.servicebus_connection_string:
        logger.warning("⚠️  Service Bus connection string not configured, consumer will not start")
        return
    
    queue_name = "document-events"
    logger.info(f"🚀 Starting document events consumer for queue: {queue_name}")
    
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
        logger.info("✅ Document events consumer started successfully")
        
        # Start consuming
        await consumer.consume(
            handler=handle_document_event,
            max_messages=10,  # Process up to 10 messages per batch
            max_wait_time=60.0  # Wait up to 60 seconds for messages
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start consumer: {e}", exc_info=True)
        raise

