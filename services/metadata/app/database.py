"""Database configuration for Metadata Service."""

import asyncio
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.config import get_config

logger = logging.getLogger(__name__)

# Get configuration
config = get_config()

# Get database URL from configuration
DATABASE_URL = config.get_database_url()

# Create async engine with optimized configuration
def create_database_engine():
    """Create database engine with configuration-based settings."""
    # Base configuration optimized for Azure PostgreSQL
    engine_config = {
        "echo": config.debug,  # Enable echo in debug mode
        # Reduce connection footprint per process to avoid saturating DB
        "pool_size": 5,
        "max_overflow": 5,
        "pool_pre_ping": True,
    }
    
    # Azure PostgreSQL configuration (compatible with asyncpg)
    if config.is_azure_environment():
        engine_config["connect_args"] = {
            "ssl": "require",  # Only ssl parameter is needed for asyncpg
            "server_settings": {"application_name": "metadata"}
        }
        logger.info("Using Azure PostgreSQL configuration with asyncpg")
    else:
        engine_config["connect_args"] = {
            "ssl": "require" if config.database_sslmode == "require" else "disable",
            "server_settings": {"application_name": "metadata"}
        }
        logger.info("Using local PostgreSQL configuration")
    
    return create_async_engine(DATABASE_URL, **engine_config)

# Create engine
engine = create_database_engine()

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def test_connection() -> bool:
    """Test database connection."""
    try:
        logger.info("Testing database connection...")
        logger.info(f"Database host: {config.database_host}")
        logger.info(f"Database port: {config.database_port}")
        logger.info(f"Database name: {config.database_name}")
        logger.info(f"Database user: {config.database_user}")
        logger.info(f"SSL mode: {config.database_sslmode}")
        
        # No timeout - let SQLAlchemy/asyncpg handle connection timeouts
        # This matches ingestion's behavior which works correctly
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            logger.info(f"Database test query result: {value}")
            return value == 1
    except asyncio.CancelledError:
        logger.warning("Database connection test was cancelled (may continue)")
        return False
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        return False


async def get_database_info() -> dict:
    """Get database information."""
    try:
        async with engine.begin() as conn:
            # Get database version and info
            result = await conn.execute(text("SELECT version(), current_database(), current_user, now()"))
            row = result.fetchone()
            
            return {
                "status": "connected",
                "version": row[0],
                "database": row[1],
                "user": row[2],
                "timestamp": str(row[3])
            }
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


async def init_db() -> None:
    """Initialize database."""
    try:
        logger.info("Starting database initialization...")
        masked = config.get_database_url().split('@')[0] + '@***:***'
        logger.info(f"Database URL: {masked}")
        logger.info(f"Azure environment: {config.is_azure_environment()}")
        
        # Test connection first (details are logged inside test_connection)
        if not await test_connection():
            logger.error("Database connection test failed")
            # Don't raise exception immediately, try to continue
            logger.warning("Continuing without database connection test")
        else:
            logger.info("Database connection successful")
        
        # Import models to create tables (if needed)
        # Note: Metadata Service uses the same table as Ingestion Service
        # Tables should already exist, but we can verify here
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't raise exception, just log the error
        logger.warning("Database initialization failed, but continuing...")


async def close_db() -> None:
    """Close database connections."""
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")

