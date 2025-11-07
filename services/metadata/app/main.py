"""Metadata Service - Main application."""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, init_db, close_db, test_connection, get_database_info
from app.routers import metadata
from app.config import get_config
# Import consumers after database initialization to avoid early engine creation
# from app.consumers import start_metadata_consumer, start_signature_consumer

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

# Global consumer tasks
document_consumer_task = None
signature_consumer_task = None


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("🛑 Received shutdown signal, stopping consumers...")
    global document_consumer_task, signature_consumer_task
    if document_consumer_task:
        document_consumer_task.cancel()
    if signature_consumer_task:
        signature_consumer_task.cancel()
    try:
        app.state.ready = False  # type: ignore[name-defined]
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    global document_consumer_task, signature_consumer_task
    
    logger.info(f"Starting Metadata Service in {config.environment} mode...")
    logger.info(f"Database: {config.database_host}:{config.database_port}/{config.database_name}")
    logger.info(f"Service Bus enabled: {config.servicebus_enabled}")
    logger.info(f"Queue: {config.document_events_queue}")
    if config.consume_signature_events:
        logger.info(f"Signature events queue: {config.signature_events_queue}")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # mark not ready during startup
    app.state.ready = False
    # Initialize database (non-blocking/with timeout to avoid startup kill by probes)
    try:
        import asyncio
        await asyncio.wait_for(init_db(), timeout=30.0)
    except asyncio.TimeoutError:
        logger.warning("⚠️  Database initialization timed out, continuing startup")
    except Exception as e:
        logger.warning(f"⚠️  Database initialization failed: {e}")
    # startup finished
    app.state.ready = True
    
    # Import consumers after database initialization
    from app.consumers import start_metadata_consumer, start_signature_consumer
    
    # Start Service Bus consumer for document events (if enabled)
    if config.servicebus_enabled and config.servicebus_connection_string:
        try:
            document_consumer_task = asyncio.create_task(start_metadata_consumer())
            logger.info("✅ Metadata Service document consumer task started")
            
            # Start signature consumer (optional, non-blocking)
            if config.consume_signature_events:
                try:
                    signature_consumer_task = asyncio.create_task(start_signature_consumer())
                    logger.info("✅ Metadata Service signature consumer task started")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to start signature consumer task: {e}")
                    logger.info("Continuing without signature consumer (signature events will still be published)")
        except Exception as e:
            logger.warning(f"⚠️  Failed to start consumer task: {e}")
            logger.info("Continuing without consumer (events will still be published by Ingestion Service)")
    else:
        logger.warning("⚠️  Service Bus not configured, consumer will not start")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down Metadata Service...")
    app.state.ready = False
    if document_consumer_task:
        document_consumer_task.cancel()
        try:
            await document_consumer_task
        except asyncio.CancelledError:
            logger.info("✅ Document consumer task cancelled")
    
    if signature_consumer_task:
        signature_consumer_task.cancel()
        try:
            await signature_consumer_task
        except asyncio.CancelledError:
            logger.info("✅ Signature consumer task cancelled")
    
    await close_db()
    logger.info("✅ Metadata Service stopped")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Metadata Service",
        description="Service for managing document metadata, consuming events, and providing search/indexing",
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
    app.include_router(metadata.router)
    
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
            "service": "metadata",
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
            "service": "metadata",
            "metrics": {
                "servicebus_enabled": config.servicebus_enabled,
                "queue": config.document_events_queue
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
    
    logger.info("🚀 Starting Metadata Service server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=config.log_level.lower()
    )

