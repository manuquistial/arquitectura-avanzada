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
    from carpeta_common.security_headers import SecurityHeadersMiddleware
    COMMON_AVAILABLE = True
except ImportError:
    from fastapi.middleware.cors import CORSMiddleware
    COMMON_AVAILABLE = False
    SecurityHeadersMiddleware = None

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

    # Security Headers (must be first)
    if COMMON_AVAILABLE and SecurityHeadersMiddleware:
        app.add_middleware(
            SecurityHeadersMiddleware,
            environment=settings.environment,
            enable_hsts=settings.environment == "production",
            enable_csp=True
        )
        logger.info("✅ Security headers middleware configured")
    
    # CORS (restrictive configuration)
    import os
    cors_origins = os.getenv("CORS_ORIGINS", "")
    cors_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    
    # Restrictive CORS configuration
    if cors_origins and cors_origins != "*":
        # Parse allowed origins (comma-separated)
        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
    else:
        # Default allowed origins for development
        if settings.environment == "development":
            origins = ["http://localhost:3000", "http://localhost:3001"]
        else:
            # Production: Must be explicitly configured
            origins = []
            logger.warning("⚠️  CORS_ORIGINS not configured for production")
    
    # Allowed methods (restrictive)
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    
    # Allowed headers (restrictive)
    allowed_headers = [
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "X-Trace-ID",
        "X-Span-ID",
        "Accept",
        "Accept-Language",
        "Content-Language"
    ]
    
    # Expose headers (what frontend can access)
    expose_headers = [
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset"
    ]
    
    if COMMON_AVAILABLE:
        setup_cors(app)
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=cors_credentials,
            allow_methods=allowed_methods,
            allow_headers=allowed_headers,
            expose_headers=expose_headers,
            max_age=3600  # Cache preflight for 1 hour
        )
    
    logger.info(f"🔒 CORS configured (restrictive): origins={origins}, credentials={cors_credentials}")

    # Advanced rate limiter middleware
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
    
    # Auth middleware
    app.add_middleware(AuthMiddleware, settings=settings)

    # Proxy service
    proxy = ProxyService(settings)
    app.state.proxy = proxy

    # Health checks (liveness and readiness)
    try:
        from carpeta_common.health import create_health_router
        
        health_router = create_health_router(
            check_database=False,  # Gateway no usa DB directamente
            check_redis=True,
            redis_host=settings.redis_host,
            redis_port=settings.redis_port,
            redis_password=settings.redis_password,
        )
        app.include_router(health_router, tags=["health"])
        logger.info("✅ Health checks configured")
    except ImportError:
        # Fallback simple health check
        @app.get("/health")
        async def health() -> dict[str, str]:
            """Simple health check."""
            return {"status": "alive"}
        
        @app.get("/ready")
        async def ready() -> dict[str, str]:
            """Simple readiness check."""
            return {"status": "ready"}
    
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

