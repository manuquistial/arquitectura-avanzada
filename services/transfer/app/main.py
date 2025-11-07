"""Transfer Service - Main application."""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.database import engine, init_db
from app.routers import transfer, auth
from app.config import get_config
from app.consumers import start_transfer_consumer, start_transfer_notification_consumer

# Import from common package (with fallback)
try:
    from carpeta_common.middleware import setup_cors, setup_logging
    COMMON_AVAILABLE = True
except ImportError:
    from fastapi.middleware.cors import CORSMiddleware
    COMMON_AVAILABLE = False

if COMMON_AVAILABLE:
    setup_logging()
else:
    # Optimized logging for production
    logging.basicConfig(
        level=logging.WARNING,  # Only warnings and errors
        format='%(levelname)s: %(message)s'  # Minimal format
    )

logger = logging.getLogger(__name__)

# Get configuration
config = get_config()

# Global consumer tasks
transfer_consumer_task = None
transfer_notification_consumer_task = None


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("🛑 Received shutdown signal, stopping consumers...")
    global transfer_consumer_task, transfer_notification_consumer_task
    if transfer_consumer_task:
        transfer_consumer_task.cancel()
    if transfer_notification_consumer_task:
        transfer_notification_consumer_task.cancel()
    sys.exit(0)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    global transfer_consumer_task, transfer_notification_consumer_task
    
    logger.info(f"Starting Transfer Service in {config.environment} mode...")
    logger.info(f"Service Bus enabled: {config.servicebus_enabled}")
    logger.info(f"Queue: {config.transfer_events_queue}")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await asyncio.wait_for(init_db(), timeout=30.0)
        logger.info("Database initialized (or continued) successfully")
    except asyncio.TimeoutError:
        logger.warning("⚠️  Database initialization timed out, continuing startup")
    except Exception as e:
        logger.warning(f"⚠️  Database initialization failed: {e}")
    
    # Start Service Bus consumer for transfer events (if enabled)
    if config.servicebus_enabled and config.servicebus_connection_string:
        try:
            transfer_consumer_task = asyncio.create_task(start_transfer_consumer())
            logger.info("✅ Transfer Service consumer task started")
            
            # Start notification consumer (optional, non-blocking)
            try:
                transfer_notification_consumer_task = asyncio.create_task(start_transfer_notification_consumer())
                logger.info("✅ Transfer Service notification consumer task started")
            except Exception as e:
                logger.warning(f"⚠️  Failed to start notification consumer task: {e}")
                logger.info("Continuing without notification consumer (notifications will still be published)")
        except Exception as e:
            logger.warning(f"⚠️  Failed to start consumer task: {e}")
            logger.info("Continuing without consumer (events will still be published by Transfer Service)")
    else:
        logger.warning("⚠️  Service Bus not configured, consumer will not start")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down Transfer Service...")
    if transfer_consumer_task:
        transfer_consumer_task.cancel()
        try:
            await transfer_consumer_task
        except asyncio.CancelledError:
            logger.info("✅ Transfer consumer task cancelled")
    
    if transfer_notification_consumer_task:
        transfer_notification_consumer_task.cancel()
        try:
            await transfer_notification_consumer_task
        except asyncio.CancelledError:
            logger.info("✅ Transfer notification consumer task cancelled")
    
    try:
        await engine.dispose()
        logger.info("Database connection disposed")
    except Exception as e:
        logger.warning(f"Error disposing database connection: {e}")
    logger.info("✅ Transfer Service stopped")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Transfer Service",
        description="P2P transfer service between operators",
        version="0.1.0",
        lifespan=lifespan,
        # Optimizations for production
        docs_url=None,  # Disable docs in production
        redoc_url=None,  # Disable redoc in production
        openapi_url=None,  # Disable OpenAPI schema
    )

    # CORS (using common utilities)
    if COMMON_AVAILABLE:
        setup_cors(app)
    else:
    # CORS configuration from environment or default to localhost
        from app.config import settings
        cors_origins = settings.cors_origins.split(",")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Trace-ID"],
        )

    # Routers
    app.include_router(transfer.router, prefix="/api", tags=["transfer"])
    app.include_router(auth.router, prefix="/api", tags=["auth"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready() -> dict[str, str | bool]:
        """Readiness check endpoint."""
        # Health check for dependencies
        return {
            "status": "ready",
            "service": "transfer",
            "servicebus_enabled": config.servicebus_enabled
        }
    
    @app.get("/metrics")
    async def metrics() -> dict:
        """Metrics endpoint."""
        # TODO: Add actual metrics from consumer
        return {
            "status": "ok",
            "service": "transfer",
            "metrics": {
                "servicebus_enabled": config.servicebus_enabled,
                "transfer_events_queue": config.transfer_events_queue,
                "transfer_notifications_queue": config.transfer_notifications_queue
            }
        }

    return app


app = create_app()

