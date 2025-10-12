"""Gateway Service - API Gateway with rate limiting and auth."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.middleware import AuthMiddleware
from app.proxy import ProxyService
from app.rate_limiter import AdvancedRateLimiter, RateLimitMiddleware

# Import from common package (with fallback)
try:
    from carpeta_common.middleware import setup_cors, setup_logging
    from carpeta_common.observability import setup_observability
    COMMON_AVAILABLE = True
except ImportError:
    from fastapi.middleware.cors import CORSMiddleware
    COMMON_AVAILABLE = False

if COMMON_AVAILABLE:
    setup_logging()
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# Global observability instances
tracer = None
meter = None
service_metrics = None

# Advanced rate limiter
rate_limiter = AdvancedRateLimiter()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    global tracer, meter, service_metrics
    
    logger.info("Starting Gateway Service...")
    
    # Setup observability
    if COMMON_AVAILABLE:
        try:
            tracer, meter, service_metrics = setup_observability(
                app=app,
                service_name="gateway",
                service_version="1.0.0"
            )
            app.state.tracer = tracer
            app.state.meter = meter
            app.state.service_metrics = service_metrics
            logger.info("✅ Observability configured")
        except Exception as e:
            logger.warning(f"⚠️  Failed to setup observability: {e}")
    
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

    # Advanced rate limiter middleware
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
    
    # Auth middleware
    app.add_middleware(AuthMiddleware, settings=settings)

    # Proxy service
    proxy = ProxyService(settings)
    app.state.proxy = proxy

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}
    
    @app.get("/ops/ratelimit/status")
    async def rate_limit_status(request: Request, ip: str = None) -> dict:
        """Get rate limiter status and current counters.
        
        Query params:
            ip: Optional IP address to check specific status
        
        Returns:
            Rate limiter configuration and current status
        """
        # Use requester's IP if not specified
        if not ip:
            ip = rate_limiter._get_client_ip(request)
        
        status = await rate_limiter.get_status(ip)
        return status

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    async def proxy_request(request: Request, path: str) -> JSONResponse:
        """Proxy requests to backend services.
        
        Rate limiting is handled by RateLimitMiddleware before this handler.
        """
        return await proxy.forward_request(request, path)

    return app


app = create_app()

