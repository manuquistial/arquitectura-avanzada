"""Notification Service - Email + Webhooks."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import Settings
from app.routers import notifications

# Setup logging
try:
    from carpeta_common.middleware import setup_logging, setup_cors
    setup_logging()
    COMMON_AVAILABLE = True
except ImportError:
    from fastapi.middleware.cors import CORSMiddleware
    COMMON_AVAILABLE = False
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

logger = logging.getLogger(__name__)
settings = Settings()
consumer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    global consumer_task
    
    logger.info("📧 Starting Notification Service...")
    
    # Start Service Bus consumer in background (if configured)
    if settings.servicebus_connection_string:
        try:
            from app.consumers.notification_consumer import NotificationConsumer
            
            consumer = NotificationConsumer(settings)
            consumer_task = asyncio.create_task(consumer.start())
            logger.info("✅ Service Bus consumers started")
        except ImportError:
            logger.warning("⚠️  Notification consumer module not found, running without event consumption")
        except Exception as e:
            logger.error(f"❌ Failed to start consumer: {e}")
    else:
        logger.warning("⚠️  Service Bus not configured (SERVICEBUS_CONNECTION_STRING missing)")
        logger.info("💡 Running in API-only mode (manual notifications)")
    
    yield
    
    # Shutdown consumer
    if consumer_task:
        logger.info("Shutting down Service Bus consumers...")
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    
    logger.info("👋 Shutting down Notification Service...")


# Create FastAPI app
app = FastAPI(
    title="Notification Service",
    description="Email and webhook notifications for Carpeta Ciudadana",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
if COMMON_AVAILABLE:
    setup_cors(app)
else:
    # CORS configuration from environment or default to localhost
    import os
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Trace-ID"],
    )

# Include routers
app.include_router(notifications.router, prefix="/notify", tags=["notifications"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "notification",
            "version": "1.0.0",
            "consumer_running": consumer_task is not None and not consumer_task.done() if consumer_task else False,
            "servicebus_configured": bool(settings.servicebus_connection_string)
        }
    )


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # Check if consumer is running (if Service Bus is configured)
    if settings.servicebus_connection_string:
        if not consumer_task or consumer_task.done():
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "reason": "Service Bus consumer not running"
                }
            )
    
    return JSONResponse(content={"status": "ready"})


@app.get("/metrics")
async def metrics():
    """OpenTelemetry metrics endpoint."""
    # TODO: Expose Prometheus metrics
    return {
        "service": "notification",
        "metrics": {
            "emails_sent": 0,  # TODO: Implement counter
            "webhooks_sent": 0,  # TODO: Implement counter
            "failures": 0
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)

