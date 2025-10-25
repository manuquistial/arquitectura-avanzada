"""Database configuration for auth service."""

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

# Database URL is already configured with psycopg in config.py

# Create async engine with optimized configuration
def create_database_engine():
    """Create database engine with configuration-based settings."""
    # Base configuration optimized for Azure PostgreSQL
    engine_config = {
        "echo": config.debug,  # Enable echo in debug mode
    }
    
    # Azure PostgreSQL configuration (compatible with asyncpg)
    # Based on test_pod_db_connection.py results, asyncpg works with minimal configuration
    if config.is_azure_environment():
        engine_config["connect_args"] = {
            "ssl": "require"  # Only ssl parameter is needed for asyncpg
        }
        logger.info("Using Azure PostgreSQL configuration with asyncpg")
    else:
        engine_config["connect_args"] = {
            "ssl": "require" if config.database_sslmode == "require" else "disable"
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
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            logger.info(f"Database test query result: {value}")
            return value == 1
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
        logger.info(f"Database URL: {config.get_database_url()[:50]}...")
        logger.info(f"Azure environment: {config.is_azure_environment()}")
        
        # Test connection first
        logger.info("Testing database connection...")
        if not await test_connection():
            logger.error("Database connection test failed")
            # Don't raise exception immediately, try to continue
            logger.warning("Continuing without database connection test")
        else:
            logger.info("Database connection successful")
        
        # Import models to create tables
        from app.models import Base
        
        logger.info("Creating/verifying database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified successfully")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't raise exception, just log the error
        logger.warning("Database initialization failed, but continuing...")


async def check_db_connection():
    """Check database connection (legacy compatibility)."""
    return await test_connection()


def serialize_json_field(value) -> str:
    """Serialize JSON field for database storage."""
    import json
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)


def deserialize_json_field(value: str):
    """Deserialize JSON field from database."""
    import json
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []
