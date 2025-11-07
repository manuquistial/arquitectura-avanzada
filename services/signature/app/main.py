"""Signature Service - Main application."""

import logging
from contextlib import asynccontextmanager
import signal
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
    # Use INFO level to see startup logs
    log_level = getattr(get_config(), 'log_level', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    logger.info("Starting Signature Service...")
    # mark not ready until startup completes
    app.state.ready = False

    # graceful shutdown: on SIGTERM mark not ready so /ready returns 503
    def _handle_sigterm(*_):
        try:
            app.state.ready = False
        except Exception:
            pass

    try:
        signal.signal(signal.SIGTERM, _handle_sigterm)
        signal.signal(signal.SIGINT, _handle_sigterm)
    except Exception:
        # not all environments allow installing signal handlers
        pass
    try:
        import asyncio
        await asyncio.wait_for(init_db(), timeout=30.0)
        logger.info("Database initialized (or continued) successfully")
    except asyncio.TimeoutError:
        logger.warning("⚠️  Database initialization timed out, continuing startup")
    except Exception as e:
        logger.warning(f"⚠️  Database initialization failed: {e}")
    finally:
        # startup finished; mark ready regardless to allow probes to pass
        app.state.ready = True
    yield
    try:
        app.state.ready = False
        await engine.dispose()
        logger.info("Database connection disposed")
    except Exception as e:
        logger.warning(f"Error disposing database connection: {e}")
    logger.info("Shutting down Signature Service...")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Signature Service",
        description="Document signature and hub authentication service",
        version="0.1.0",
        lifespan=lifespan,
        # Optimizations for production
        docs_url=None,  # Disable docs in production
        redoc_url=None,  # Disable redoc in production
        openapi_url=None,  # Disable OpenAPI schema
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
        is_ready = bool(getattr(app.state, "ready", False))
        return {
            "status": "ready" if is_ready else "not_ready",
            "service": "signature",
            "environment": config.environment
        }

    return app


app = create_app()
