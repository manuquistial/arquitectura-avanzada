"""
Transfer Worker - Dedicated Consumer for Transfer Processing
Scalable worker that processes transfers from Azure Service Bus queue
"""

import asyncio
import logging
import os
import signal
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

# Import from common package
try:
    from carpeta_common.service_bus_consumer import ServiceBusConsumer
    from carpeta_common.middleware import setup_logging
    COMMON_AVAILABLE = True
except ImportError:
    COMMON_AVAILABLE = False
    logging.basicConfig(level=logging.INFO)

if COMMON_AVAILABLE:
    setup_logging()

logger = logging.getLogger(__name__)

# Global consumer instance
consumer: ServiceBusConsumer | None = None
consumer_task: asyncio.Task | None = None
shutdown_event = asyncio.Event()


async def process_transfer_message(message_body: dict) -> None:
    """
    Process a single transfer message
    
    Args:
        message_body: Message payload from Service Bus
    """
    transfer_id = message_body.get("transfer_id")
    logger.info(f"🔄 Processing transfer: {transfer_id}")
    
    try:
        # TODO: Implement actual transfer processing logic
        # 1. Validate transfer data
        # 2. Check source and destination ownership
        # 3. Update transfer status
        # 4. Copy document references
        # 5. Send notifications
        # 6. Emit events
        
        # Simulated processing
        await asyncio.sleep(2)  # Simulate work
        
        logger.info(f"✅ Transfer processed successfully: {transfer_id}")
        
    except Exception as e:
        logger.error(f"❌ Error processing transfer {transfer_id}: {e}")
        raise  # Re-raise to trigger DLQ


async def start_consumer():
    """Start Service Bus consumer"""
    global consumer, consumer_task
    
    if not COMMON_AVAILABLE:
        logger.warning("⚠️  carpeta_common not available, consumer disabled")
        return
    
    connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")
    queue_name = os.getenv("SERVICEBUS_TRANSFER_QUEUE", "transfers")
    
    if not connection_string:
        logger.warning("⚠️  SERVICEBUS_CONNECTION_STRING not set, consumer disabled")
        return
    
    try:
        # Create consumer
        consumer = ServiceBusConsumer(
            connection_string=connection_string,
            queue_name=queue_name,
            handler=process_transfer_message,
            max_concurrent=int(os.getenv("MAX_CONCURRENT_MESSAGES", "10")),
            prefetch_count=int(os.getenv("PREFETCH_COUNT", "20")),
            max_wait_time=int(os.getenv("MAX_WAIT_TIME", "60"))
        )
        
        logger.info(f"🚀 Starting consumer for queue: {queue_name}")
        
        # Start consuming in background task
        consumer_task = asyncio.create_task(consumer.start())
        
        logger.info("✅ Consumer started successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to start consumer: {e}")
        raise


async def stop_consumer():
    """Stop Service Bus consumer"""
    global consumer, consumer_task
    
    if consumer:
        logger.info("🛑 Stopping consumer...")
        await consumer.stop()
        
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    
    logger.info("✅ Consumer stopped")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan"""
    logger.info("🚀 Starting Transfer Worker...")
    
    # Start consumer
    await start_consumer()
    
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: shutdown_event.set())
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Transfer Worker...")
    await stop_consumer()
    logger.info("✅ Shutdown complete")


def create_app() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title="Transfer Worker",
        description="Dedicated worker for processing transfer requests",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint"""
        return {"status": "healthy"}
    
    @app.get("/ready")
    async def ready() -> dict[str, str | bool]:
        """Readiness check endpoint"""
        is_ready = consumer is not None and consumer_task is not None
        return {
            "status": "ready" if is_ready else "not ready",
            "consumer_active": is_ready
        }
    
    @app.get("/metrics")
    async def metrics() -> dict[str, int]:
        """Basic metrics endpoint"""
        processed = getattr(consumer, "messages_processed", 0) if consumer else 0
        failed = getattr(consumer, "messages_failed", 0) if consumer else 0
        
        return {
            "messages_processed": processed,
            "messages_failed": failed,
            "messages_in_progress": processed - failed if processed > failed else 0
        }
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8012,
        log_level="info",
        access_log=True
    )

