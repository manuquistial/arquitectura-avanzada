"""Ingestion Service - Main application."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.database import engine, init_db
from app.routers import documents

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
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    logger.info("Starting Ingestion Service...")
    await init_db()
    yield
    await engine.dispose()
    logger.info("Shutting down Ingestion Service...")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Ingestion Service",
        description="Document ingestion service with S3 presigned URLs",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS (using common utilities)
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

    # Routers
    app.include_router(documents.router, prefix="/api/documents", tags=["documents"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()

