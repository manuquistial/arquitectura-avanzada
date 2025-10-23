"""Ingestion Service - Main application."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, init_db, test_connection, get_database_info
from app.routers import documents
from app.config import get_config

# Get configuration
config = get_config()

# Setup logging based on configuration
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Import from common package (with fallback)
try:
    from carpeta_common.middleware import setup_cors, setup_logging
    COMMON_AVAILABLE = True
    if COMMON_AVAILABLE:
        setup_logging()
except ImportError:
    COMMON_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    logger.info(f"Starting Ingestion Service in {config.environment} mode...")
    logger.info(f"Database: {config.database_host}:{config.database_port}/{config.database_name}")
    logger.info(f"Azure Storage: {config.azure_storage_account_name}")
    
    # Initialize database
    await init_db()
    
    yield
    
    # Cleanup
    await engine.dispose()
    logger.info("Shutting down Ingestion Service...")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Ingestion Service",
        description="Document ingestion service with Azure Blob Storage",
        version="0.1.0",
        lifespan=lifespan,
        debug=config.debug,
    )

    # CORS configuration
    if COMMON_AVAILABLE:
        setup_cors(app)
    else:
        # CORS configuration from config
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
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

    @app.get("/ready")
    async def ready() -> dict[str, str | bool]:
        """Readiness check endpoint."""
        # Health check for dependencies
        db_connected = await test_connection()
        return {
            "status": "ready" if db_connected else "not_ready",
            "service": "ingestion",
            "database": "connected" if db_connected else "disconnected"
        }

    @app.get("/db/health")
    async def db_health() -> dict:
        """Database health check endpoint."""
        return await get_database_info()

    @app.get("/db/test")
    async def db_test() -> dict:
        """Database connection test endpoint."""
        is_connected = await test_connection()
        return {
            "status": "connected" if is_connected else "disconnected",
            "test": "successful" if is_connected else "failed"
        }

    @app.get("/config")
    async def get_config_info() -> dict:
        """Get configuration information (for debugging)."""
        return {
            "environment": config.environment,
            "debug": config.debug,
            "database": {
                "host": config.database_host,
                "port": config.database_port,
                "name": config.database_name,
                "user": config.database_user,
                "sslmode": config.database_sslmode,
                "is_azure": config.is_azure_environment()
            },
            "azure_storage": {
                "account_name": config.azure_storage_account_name,
                "container_name": config.azure_storage_container_name
            },
            "kubernetes": {
                "pod_name": config.pod_name,
                "namespace": config.pod_namespace,
                "node_name": config.node_name
            }
        }

    @app.get("/config/database")
    async def get_database_config() -> dict:
        """Get database configuration (sensitive data masked)."""
        return {
            "host": config.database_host,
            "port": config.database_port,
            "name": config.database_name,
            "user": config.database_user,
            "sslmode": config.database_sslmode,
            "is_azure": config.is_azure_environment(),
            "url_masked": config.get_database_url().split("@")[0] + "@***:***"
        }

    return app


app = create_app()

