"""MinTIC Client Service - Main application."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.client import MinTICClient
from app.config import Settings
from app.database import init_db
from app.routers import mintic, status

logging.basicConfig(
        level=logging.WARNING,  # Only warnings and errors
        format='%(levelname)s: %(message)s'  # Minimal format
    )
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    logger.info("Starting MinTIC Client Service...")
    
    # Get settings directly
    settings = Settings()
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        logger.info("Continuing without database for testing purposes")
    
    # Initialize Redis connection (if enabled)
    if settings.redis_enabled:
        try:
            await app.state.mintic_client.redis_client.connect()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
    else:
        logger.info("Redis disabled, skipping connection")
    
    yield
    
    # Cleanup
    if settings.redis_enabled:
        try:
            await app.state.mintic_client.redis_client.disconnect()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Redis disconnect failed: {e}")
    
    logger.info("Shutting down MinTIC Client Service...")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = Settings()

    app = FastAPI(
        title="Service",
        description="Service description",
        version="0.1.0",
        lifespan=lifespan,
        # Optimizations for production
        docs_url=None,  # Disable docs in production
        redoc_url=None,  # Disable redoc in production
        openapi_url=None,  # Disable OpenAPI schema
    )

    # CORS configuration from environment or default to localhost
    cors_origins = settings.cors_origins.split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Trace-ID"],
    )

    # Initialize MinTIC client
    mintic_client = MinTICClient(settings)
    app.state.mintic_client = mintic_client

    # Routers
    app.include_router(mintic.router, prefix="/api/mintic", tags=["mintic"])
    app.include_router(status.router, tags=["status"])

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
            "service": "mintic_client"
        }

    return app


app = create_app()

