"""Gateway Service - API Gateway with rate limiting and auth."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import Settings
from app.middleware import AuthMiddleware
from app.proxy import ProxyService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    logger.info("Starting Gateway Service...")
    yield
    logger.info("Shutting down Gateway Service...")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = Settings()

    app = FastAPI(
        title="API Gateway",
        description="API Gateway with rate limiting and authentication",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth middleware
    app.add_middleware(AuthMiddleware, settings=settings)

    # Proxy service
    proxy = ProxyService(settings)
    app.state.proxy = proxy

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    @limiter.limit(f"{settings.rate_limit_per_minute}/minute")
    async def proxy_request(request: Request, path: str) -> JSONResponse:
        """Proxy requests to backend services."""
        return await proxy.forward_request(request, path)

    return app


app = create_app()

