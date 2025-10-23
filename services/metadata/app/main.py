"""Metadata Service - Main application - Updated for Azure PostgreSQL."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_config
from app.database import engine, init_db, test_connection, get_database_info
from app.opensearch_client import OpenSearchClient
from app.routers import metadata

# Get configuration
config = get_config()

# Setup logging based on configuration
logging.basicConfig(
    level=getattr(logging, config.app.log_level),
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

# Global consumer task
_consumer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan."""
    global _consumer_task
    
    logger.info(f"Starting Metadata Service in {config.app.environment} mode...")
    logger.info(f"Database: {config.database.host}:{config.database.port}/{config.database.name}")
    logger.info(f"OpenSearch: {config.opensearch.host}:{config.opensearch.port}")
    
    # Initialize database
    await init_db()
    
    # Initialize OpenSearch
    opensearch = OpenSearchClient(config)
    
    try:
        opensearch.ensure_index()
        logger.info("✅ OpenSearch initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ OpenSearch initialization failed: {e}")
        logger.warning("Service will continue without OpenSearch functionality")
    
    # Start event consumers in background
    try:
        from app.consumers.event_consumer import MetadataEventConsumer
        consumer = MetadataEventConsumer(config, opensearch)
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
    
    opensearch.close()
    await engine.dispose()
    logger.info("Shutting down Metadata Service...")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Metadata Service",
        description="Document metadata and search service with Azure PostgreSQL",
        version="0.1.0",
        lifespan=lifespan,
        debug=config.app.debug,
    )

    # CORS configuration
    if COMMON_AVAILABLE:
        setup_cors(app)
    else:
        # CORS configuration from config
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.app.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Trace-ID"],
        )

    # Routers
    app.include_router(metadata.router, prefix="/api/metadata", tags=["metadata"])

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
            "service": "metadata",
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
            "environment": config.app.environment,
            "debug": config.app.debug,
            "database": {
                "host": config.database.host,
                "port": config.database.port,
                "name": config.database.name,
                "user": config.database.user,
                "sslmode": config.database.sslmode,
                "is_azure": config.is_azure_environment()
            },
            "opensearch": {
                "host": config.opensearch.host,
                "port": config.opensearch.port,
                "index": config.opensearch.index,
                "use_ssl": config.opensearch.use_ssl
            },
            "redis": {
                "host": config.redis.host,
                "port": config.redis.port,
                "ssl": config.redis.ssl
            },
            "servicebus": {
                "enabled": config.servicebus.enabled,
                "has_connection_string": bool(config.servicebus.connection_string)
            },
            "kubernetes": {
                "pod_name": config.app.pod_name,
                "namespace": config.app.pod_namespace,
                "node_name": config.app.node_name
            }
        }

    @app.get("/config/database")
    async def get_database_config() -> dict:
        """Get database configuration (sensitive data masked)."""
        return {
            "host": config.database.host,
            "port": config.database.port,
            "name": config.database.name,
            "user": config.database.user,
            "sslmode": config.database.sslmode,
            "is_azure": config.is_azure_environment(),
            "url_masked": config.get_database_url().split("@")[0] + "@***:***"
        }

    return app


app = create_app()

