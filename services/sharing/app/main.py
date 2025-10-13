"""Main application for sharing service."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import Settings
from app.database import init_db, engine
from app.routers import sharing

# Setup logging
try:
    from carpeta_common.middleware import setup_logging
    setup_logging()
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

logger = logging.getLogger(__name__)
settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    logger.info("🚀 Starting Sharing Service...")
    await init_db()
    yield
    await engine.dispose()
    logger.info("👋 Shutting down Sharing Service...")


# Create FastAPI app
app = FastAPI(
    title="Sharing Service",
    description="Document sharing with shortlinks and SAS URLs",
    version="1.0.0",
    lifespan=lifespan
)

# Setup CORS
try:
    from carpeta_common.middleware import setup_cors
    setup_cors(app)
except ImportError:
    from fastapi.middleware.cors import CORSMiddleware
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

# Include routers
app.include_router(sharing.router, prefix="/share", tags=["sharing"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "sharing",
            "version": "1.0.0"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

