"""Signature Service - Main application."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.database import engine, init_db
from app.routers import signature
from app.config import get_config

# Get configuration
config = get_config()

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
    logging.basicConfig(level=getattr(logging, config.log_level))

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    logger.info("Starting Signature Service...")
    await init_db()
    yield
    await engine.dispose()
    logger.info("Shutting down Signature Service...")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Signature Service",
        description="Document signature and hub authentication service",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS (using common utilities)
    if COMMON_AVAILABLE:
        setup_cors(app)
    else:
        # CORS configuration from environment or default to localhost
        cors_origins = config.cors_origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Trace-ID"],
        )

    # Routers
    app.include_router(signature.router, prefix="/api/signature", tags=["signature"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready() -> dict[str, str | bool]:
        """Readiness check endpoint."""
        # Health check for dependencies
        from app.database import test_connection, get_database_info
        
        db_status = "connected"
        try:
            if not await test_connection():
                db_status = "disconnected"
        except Exception:
            db_status = "error"
        
        return {
            "status": "ready",
            "service": "signature",
            "database": db_status,
            "environment": config.environment
        }

    return app


app = create_app()
