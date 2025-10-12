"""Metadata Service - Main application."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.config import Settings
from app.database import engine, init_db
from app.opensearch_client import OpenSearchClient
from app.routers import metadata

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

# Global consumer task
_consumer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    global _consumer_task
    
    logger.info("Starting Metadata Service...")
    await init_db()
    
    # Initialize OpenSearch
    settings = Settings()
    opensearch = OpenSearchClient(settings)
    await opensearch.ensure_index()
    
    # Start event consumers in background
    try:
        from app.consumers.event_consumer import MetadataEventConsumer
        consumer = MetadataEventConsumer(settings, opensearch)
        _consumer_task = asyncio.create_task(consumer.start_consumers())
        logger.info("✅ Event consumers started in background")
    except Exception as e:
        logger.warning(f"Failed to start consumers: {e}")
    
    yield
    
    # Cleanup
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    
    await opensearch.close()
    await engine.dispose()
    logger.info("Shutting down Metadata Service...")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Metadata Service",
        description="Document metadata and search service",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS (using common utilities)
    if COMMON_AVAILABLE:
        setup_cors(app)
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Routers
    app.include_router(metadata.router, prefix="/api/metadata", tags=["metadata"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()

