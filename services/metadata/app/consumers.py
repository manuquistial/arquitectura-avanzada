"""Service Bus event consumers for metadata operations."""

import logging
from typing import Dict, Any

from carpeta_common.service_bus_consumer import ServiceBusConsumer
from app.config import get_config
from app.processors import MetadataEventProcessor

logger = logging.getLogger(__name__)

config = get_config()
processor = MetadataEventProcessor()


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
        elif event_type == "signature.completed":
            # Process signature completion (same as document.verified)
            await processor.process_document_verified(event_data)
        elif event_type == "signature.failed":
            # Log signature failures
            logger.warning(f"⚠️  Signature failed: {event_data.get('data', {})}")
        else:
            logger.warning(f"⚠️  Unknown event type: {event_type}, ignoring")
    
    except Exception as e:
        logger.error(f"❌ Error handling document event {event_type}: {e}", exc_info=True)
        raise  # Re-raise to trigger retry/DLQ


async def handle_signature_event(event_data: Dict[str, Any]) -> None:
    """Handle signature event from Service Bus.
    
    Routes signature events to appropriate processor.
    
    Args:
        event_data: Event data from Service Bus
    """
    event_type = event_data.get("event_type", "")
    
    logger.info(f"📨 Received signature event: {event_type}")
    
    try:
        # Route to appropriate processor
        if event_type == "document.verified" or event_type == "signature.completed":
            await processor.process_document_verified(event_data)
        elif event_type == "signature.failed":
            data = event_data.get("data", {})
            document_id = data.get("document_id")
            error = data.get("error", "Unknown error")
            logger.warning(f"⚠️  Signature failed for document {document_id}: {error}")
        else:
            logger.warning(f"⚠️  Unknown signature event type: {event_type}, ignoring")
    
    except Exception as e:
        logger.error(f"❌ Error handling signature event {event_type}: {e}", exc_info=True)
        raise  # Re-raise to trigger retry/DLQ


async def start_metadata_consumer() -> None:
    """Start Service Bus consumer for document events."""
    if not config.servicebus_enabled:
        logger.warning("⚠️  Service Bus disabled, consumer will not start")
        return
    
    if not config.servicebus_connection_string:
        logger.warning("⚠️  Service Bus connection string not configured, consumer will not start")
        return
    
    queue_name = config.document_events_queue
    logger.info(f"🚀 Starting Metadata Service consumer for queue: {queue_name}")
    
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
        logger.info("✅ Metadata Service consumer started successfully")
        
        # Start consuming
        await consumer.consume(
            handler=handle_document_event,
            max_messages=config.max_messages_per_batch,
            max_wait_time=config.max_wait_time
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start consumer: {e}", exc_info=True)
        raise


async def start_signature_consumer() -> None:
    """Start Service Bus consumer for signature events (optional)."""
    if not config.servicebus_enabled:
        logger.warning("⚠️  Service Bus disabled, signature consumer will not start")
        return
    
    if not config.servicebus_connection_string:
        logger.warning("⚠️  Service Bus connection string not configured, signature consumer will not start")
        return
    
    if not config.consume_signature_events:
        logger.info("ℹ️  Signature events consumption disabled (CONSUME_SIGNATURE_EVENTS=false)")
        return
    
    queue_name = config.signature_events_queue
    logger.info(f"🚀 Starting Metadata Service signature consumer for queue: {queue_name}")
    
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
        logger.info("✅ Metadata Service signature consumer started successfully")
        
        # Start consuming
        await consumer.consume(
            handler=handle_signature_event,
            max_messages=config.max_messages_per_batch,
            max_wait_time=config.max_wait_time
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start signature consumer: {e}", exc_info=True)
        # Don't fail service if signature consumer fails (optional)
        logger.warning("⚠️  Continuing without signature consumer")
