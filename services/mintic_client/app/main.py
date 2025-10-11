"""MinTIC Client Service - Main application."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.client import MinTICClient
from app.config import Settings
from app.routers import mintic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    logger.info("Starting MinTIC Client Service...")
    yield
    logger.info("Shutting down MinTIC Client Service...")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = Settings()

    app = FastAPI(
        title="MinTIC Client Service",
        description="Client service for MinTIC Hub integration",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize MinTIC client
    mintic_client = MinTICClient(settings)
    app.state.mintic_client = mintic_client

    # Routers
    app.include_router(mintic.router, prefix="/api/mintic", tags=["mintic"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()

