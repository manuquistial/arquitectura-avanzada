"""Notification Service - Main application."""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, init_db, close_db, test_connection, get_database_info
from app.routers import notifications
from app.config import get_config
from app.consumers import start_notification_consumer

# Get configuration
config = get_config()

# Setup logging based on configuration
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import from common package (with fallback)
try:
    from carpeta_common.middleware import setup_cors, setup_logging
    COMMON_AVAILABLE = True
    if COMMON_AVAILABLE:
        setup_logging()
except ImportError:
    COMMON_AVAILABLE = False

# Global consumer task
consumer_task = None


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("🛑 Received shutdown signal, stopping consumer...")
    if consumer_task:
        consumer_task.cancel()
    sys.exit(0)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    global consumer_task
    
    logger.info(f"Starting Notification Service in {config.environment} mode...")
    logger.info(f"Service Bus enabled: {config.servicebus_enabled}")
    logger.info(f"Queue: {config.citizen_events_queue}")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # mark not ready during startup
    app.state.ready = False
    # Initialize database (non-blocking/with timeout to avoid probe kills)
    try:
        await asyncio.wait_for(init_db(), timeout=30.0)
    except asyncio.TimeoutError:
        logger.warning("⚠️  Database initialization timed out, continuing startup")
    except Exception as e:
        logger.warning(f"⚠️  Database initialization failed: {e}")
    # startup finished
    app.state.ready = True
    
    # Start Service Bus consumer for citizen events (if enabled and library available)
    if config.servicebus_enabled and config.servicebus_connection_string:
        try:
            # Guard: verify azure-servicebus import availability before starting
            try:
                from azure.servicebus.aio import ServiceBusClient  # noqa: F401
                azure_ok = True
            except Exception as _imp_err:
                azure_ok = False
                logger.warning(f"⚠️  azure-servicebus unavailable at runtime: {_imp_err}")
            if not azure_ok:
                raise RuntimeError("azure-servicebus not available; consumer disabled")
            consumer_task = asyncio.create_task(start_notification_consumer())
            logger.info("✅ Notification Service consumer task started")
        except Exception as e:
            logger.warning(f"⚠️  Failed to start consumer task: {e}")
            logger.info("Continuing without consumer (events will still be published by Citizen Service)")
    else:
        logger.warning("⚠️  Service Bus not configured, consumer will not start")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down Notification Service...")
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            logger.info("✅ Consumer task cancelled")
    
    await close_db()
    logger.info("✅ Notification Service stopped")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Notification Service",
        description="Service for processing citizen events and sending notifications",
        version="1.0.0",
        lifespan=lifespan,
        debug=config.debug
    )
    
    # CORS configuration
    if COMMON_AVAILABLE:
        setup_cors(app)
    else:
        # CORS configuration from config
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Trace-ID"],
        )
    
    # Routers
    app.include_router(notifications.router)
    
    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}
    
    @app.get("/ready")
    async def ready() -> dict[str, str | bool]:
        """Readiness check endpoint."""
        is_ready = bool(getattr(app.state, "ready", False))
        return {
            "status": "ready" if is_ready else "not_ready",
            "service": "notification",
            "servicebus_enabled": config.servicebus_enabled
        }
    
    @app.get("/db/health")
    async def db_health() -> dict:
        """Database health check endpoint."""
        return await get_database_info()
    
    @app.get("/metrics")
    async def metrics() -> dict:
        """Metrics endpoint."""
        # TODO: Add actual metrics from consumer
        return {
            "status": "ok",
            "service": "notification",
            "metrics": {
                "servicebus_enabled": config.servicebus_enabled,
                "queue": config.citizen_events_queue,
                "smtp_enabled": config.smtp_enabled
            }
        }
    
    @app.exception_handler(Exception)
    async def exception_handler(request, exc):
        """Global exception handler."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return {
            "detail": "Internal server error"
        }
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting Notification Service server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=config.log_level.lower()
    )

