"""
Auth Service - OIDC Provider + Session Management
Handles authentication, token validation, and session management
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, oidc, sessions

# Import from common package (with fallback)
try:
    from carpeta_common.middleware import setup_logging
    COMMON_AVAILABLE = True
except ImportError:
    COMMON_AVAILABLE = False
    logging.basicConfig(level=logging.INFO)

if COMMON_AVAILABLE:
    setup_logging()
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan"""
    logger.info("🚀 Starting Auth Service...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"OIDC Issuer: {settings.oidc_issuer_url}")
    
    yield
    
    logger.info("🛑 Shutting down Auth Service...")


def create_app() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title="Auth Service",
        description="Authentication and authorization service with OIDC support",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Routers
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(oidc.router, prefix="/.well-known", tags=["oidc"])
    app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
    
    # Health endpoints
    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint"""
        return {"status": "healthy", "service": "auth"}
    
    @app.get("/ready")
    async def ready() -> dict[str, str | bool]:
        """Readiness check endpoint"""
        # TODO: Check database connection, Redis, etc.
        return {
            "status": "ready",
            "service": "auth",
            "oidc_enabled": True
        }
    
    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint"""
        return {
            "service": "auth",
            "version": "1.0.0",
            "oidc_issuer": settings.oidc_issuer_url,
            "endpoints": {
                "oidc_discovery": "/.well-known/openid-configuration",
                "jwks": "/.well-known/jwks.json",
                "token": "/api/auth/token",
                "userinfo": "/api/auth/userinfo"
            }
        }
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8011,
        log_level="info",
        reload=True
    )

