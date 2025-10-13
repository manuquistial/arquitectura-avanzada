"""Read Models Service - CQRS Read Side."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import Settings
from app.database import init_db, engine

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
    
    logger.info("🔄 Starting Read Models Service (CQRS Read Side)...")
    
    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")
    
    # Start event consumers in background (if Service Bus configured)
    if settings.servicebus_connection_string:
        try:
            from app.consumers import event_projector
            
            projector = event_projector.EventProjector(settings)
            consumer_task = asyncio.create_task(projector.start())
            logger.info("✅ Event projectors started (CQRS projection)")
        except ImportError:
            logger.warning("⚠️  Event projector module not found, running without projections")
        except Exception as e:
            logger.error(f"❌ Failed to start projectors: {e}")
    else:
            logger.warning("⚠️  Service Bus not configured (SERVICEBUS_CONNECTION_STRING missing)")
            logger.info("💡 Running in query-only mode (no event projections)")
        
        yield
        
    # Shutdown
        if consumer_task:
            logger.info("Shutting down event projectors...")
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        
        await engine.dispose()
        logger.info("👋 Shutting down Read Models Service...")


# Create FastAPI app
app = FastAPI(
    title="Read Models Service",
    description="CQRS read models with optimized queries",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
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

# Import and include routers
try:
    from app.routers import read_queries
    app.include_router(read_queries.router, prefix="/read", tags=["read-models"])
    logger.info("✅ Read queries router loaded")
except ImportError as e:
    logger.warning(f"⚠️  Read queries router not found: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "read-models",
            "version": "1.0.0",
            "projector_running": consumer_task is not None and not consumer_task.done() if consumer_task else False,
            "servicebus_configured": bool(settings.servicebus_connection_string)
        }
    )


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # Simple check - TODO: verify database connection
    return JSONResponse(content={"status": "ready"})


@app.get("/metrics")
async def metrics():
    """OpenTelemetry metrics endpoint."""
    # TODO: Expose Prometheus metrics
    return {
        "service": "read-models",
        "metrics": {
            "events_projected": 0,  # TODO: Implement counter
            "queries_served": 0,
            "cache_hits": 0
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)

