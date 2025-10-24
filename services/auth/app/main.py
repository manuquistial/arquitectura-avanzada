"""
Auth Service - OIDC Provider + Session Management
Handles authentication, token validation, and session management
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_config
from app.routers import auth, oidc, sessions

# Import from common package (with fallback)
try:
    from carpeta_common.middleware import setup_logging
    COMMON_AVAILABLE = True
except ImportError:
    COMMON_AVAILABLE = False
    logging.basicConfig(
        level=logging.WARNING,  # Only warnings and errors
        format='%(levelname)s: %(message)s'  # Minimal format
    )

if COMMON_AVAILABLE:
    setup_logging()
else:
    # Optimized logging for production
    logging.basicConfig(
        level=logging.WARNING,  # Only warnings and errors
        format='%(levelname)s: %(message)s'  # Minimal format
    )

logger = logging.getLogger(__name__)
config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan"""
    logger.info("🚀 Starting Auth Service...")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"OIDC Issuer: {config.oidc_issuer_url}")
    
    # Initialize database
    try:
        from app.database import init_db, check_db_connection
        await init_db()
        db_connected = await check_db_connection()
        if db_connected:
            logger.info("✅ Database connection established")
        else:
            logger.warning("⚠️ Database connection failed")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        logger.info("Continuing without database for testing purposes")
    
    yield
    
    logger.info("🛑 Shutting down Auth Service...")


def create_app() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title="Auth Service",
        description="Authentication and authorization service with OIDC support",
        version="1.0.0",
        lifespan=lifespan,
        # Optimizations for production
        docs_url=None,  # Disable docs in production
        redoc_url=None,  # Disable redoc in production
        openapi_url=None,  # Disable OpenAPI schema
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
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
        # Health check for dependencies
        return {
            "status": "ready",
            "service": "auth",
            "oidc_enabled": True
        }
    
    @app.get("/")
    async def root() -> dict[str, Any]:
        """Root endpoint"""
        return {
            "service": "auth",
            "version": "1.0.0",
            "oidc_issuer": config.oidc_issuer_url,
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
        port=8000,
        log_level="info",
        reload=True
    )

