"""Service Bus event consumers for transfer operations."""

import logging
from typing import Dict, Any

from carpeta_common.service_bus_consumer import ServiceBusConsumer
from app.config import get_config
from app.processors import TransferEventProcessor

logger = logging.getLogger(__name__)

config = get_config()
processor = TransferEventProcessor()


async def handle_transfer_event(event_data: Dict[str, Any]) -> None:
    """Handle transfer event from Service Bus.
    
    Routes events to appropriate processor based on event_type.
    
    Args:
        event_data: Event data from Service Bus
    """
    event_type = event_data.get("event_type", "")
    
    logger.info(f"📨 Received event: {event_type}")
    
    try:
        # Route to appropriate processor
        if event_type == "transfer.requested":
            await processor.process_transfer_requested(event_data)
        elif event_type == "transfer.confirmed":
            await processor.process_transfer_confirmed(event_data)
        elif event_type == "transfer.saga.completed":
            # Saga completion is logged, can trigger additional actions
            logger.info(f"✅ Transfer saga completed: {event_data.get('data', {}).get('transfer_id')}")
        else:
            logger.warning(f"⚠️  Unknown transfer event type: {event_type}, ignoring")
    
    except Exception as e:
        logger.error(f"❌ Error handling transfer event {event_type}: {e}", exc_info=True)
        raise  # Re-raise to trigger retry/DLQ


async def handle_transfer_notification(event_data: Dict[str, Any]) -> None:
    """Handle transfer notification event from Service Bus.
    
    Args:
        event_data: Event data from Service Bus
    """
    logger.info(f"📨 Received transfer notification event")
    
    try:
        await processor.process_transfer_notification(event_data)
    
    except Exception as e:
        logger.error(f"❌ Error handling transfer notification: {e}", exc_info=True)
        raise  # Re-raise to trigger retry/DLQ


async def start_transfer_consumer() -> None:
    """Start Service Bus consumer for transfer events."""
    if not config.servicebus_enabled:
        logger.warning("⚠️  Service Bus disabled, consumer will not start")
        return
    
    if not config.servicebus_connection_string:
        logger.warning("⚠️  Service Bus connection string not configured, consumer will not start")
        return
    
    queue_name = config.transfer_events_queue
    logger.info(f"🚀 Starting Transfer Service consumer for queue: {queue_name}")
    
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
        logger.info("✅ Transfer Service consumer started successfully")
        
        # Start consuming
        await consumer.consume(
            handler=handle_transfer_event,
            max_messages=config.max_messages_per_batch,
            max_wait_time=config.max_wait_time
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start consumer: {e}", exc_info=True)
        raise


async def start_transfer_notification_consumer() -> None:
    """Start Service Bus consumer for transfer notifications (optional)."""
    if not config.servicebus_enabled:
        logger.warning("⚠️  Service Bus disabled, notification consumer will not start")
        return
    
    if not config.servicebus_connection_string:
        logger.warning("⚠️  Service Bus connection string not configured, notification consumer will not start")
        return
    
    queue_name = config.transfer_notifications_queue
    logger.info(f"🚀 Starting Transfer Service notification consumer for queue: {queue_name}")
    
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
        logger.info("✅ Transfer Service notification consumer started successfully")
        
        # Start consuming
        await consumer.consume(
            handler=handle_transfer_notification,
            max_messages=config.max_messages_per_batch,
            max_wait_time=config.max_wait_time
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start notification consumer: {e}", exc_info=True)
        # Don't fail service if notification consumer fails (optional)
        logger.warning("⚠️  Continuing without notification consumer")

