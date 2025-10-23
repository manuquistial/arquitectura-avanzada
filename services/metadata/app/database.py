"""Database configuration for metadata service - Updated for Azure PostgreSQL."""

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

# Create async engine with optimized configuration for Azure PostgreSQL
def create_database_engine():
    """Create database engine with configuration-based settings."""
    # Base configuration optimized for Azure PostgreSQL
    engine_config = {
        "echo": config.app.debug,  # Enable echo in debug mode
        "future": True,
        "pool_size": 5,  # Reduced for better resource management
        "max_overflow": 10,  # Reduced for better resource management
        "pool_pre_ping": True,
        "pool_recycle": 3600,  # Recycle connections every hour
        "pool_timeout": 30,  # Timeout for getting connection from pool
    }
    
    # Azure PostgreSQL configuration (proven to work in tests)
    if config.is_azure_environment():
        engine_config["connect_args"] = {
            "sslmode": "require",  # Use sslmode instead of ssl for psycopg
            "connect_timeout": 10,
            "application_name": "metadata-service"
        }
        logger.info("Using Azure PostgreSQL configuration with psycopg")
    else:
        engine_config["connect_args"] = {
            "sslmode": config.database.sslmode,
            "application_name": "metadata-service"
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
    """Test database connection with Azure-specific error handling."""
    try:
        logger.info("Testing database connection...")
        logger.info(f"Database host: {config.database.host}")
        logger.info(f"Database port: {config.database.port}")
        logger.info(f"Database name: {config.database.name}")
        logger.info(f"Database user: {config.database.user}")
        logger.info(f"SSL mode: {config.database.sslmode}")
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            logger.info(f"Database test query result: {value}")
            return value == 1
            
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Database connection test failed: {e}")
        logger.error(f"Error type: {error_type}")
        
        # Azure-specific error handling
        if "connection" in str(e).lower():
            logger.error("❌ Azure PostgreSQL connection failed - check network and credentials")
        elif "ssl" in str(e).lower():
            logger.error("❌ SSL connection failed - check SSL configuration")
        elif "authentication" in str(e).lower():
            logger.error("❌ Authentication failed - check database credentials")
        elif "timeout" in str(e).lower():
            logger.error("❌ Connection timeout - check Azure PostgreSQL availability")
        else:
            logger.error(f"❌ Unexpected database error: {error_type}")
            
        return False


async def get_database_info() -> dict:
    """Get database information with Azure-specific error handling."""
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
                "timestamp": str(row[3]),
                "azure_environment": config.is_azure_environment()
            }
            
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Failed to get database info: {e}")
        logger.error(f"Error type: {error_type}")
        
        # Azure-specific error handling
        if "connection" in str(e).lower():
            return {
                "status": "error",
                "error": "Azure PostgreSQL connection failed",
                "error_type": error_type,
                "azure_environment": config.is_azure_environment(),
                "suggestion": "Check network connectivity and Azure PostgreSQL status"
            }
        elif "permission" in str(e).lower():
            return {
                "status": "error",
                "error": "Database permission denied",
                "error_type": error_type,
                "azure_environment": config.is_azure_environment(),
                "suggestion": "Check database user permissions"
            }
        else:
            return {
                "status": "error",
                "error": str(e),
                "error_type": error_type,
                "azure_environment": config.is_azure_environment()
            }


async def init_db() -> None:
    """Initialize database with Azure-specific error handling."""
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
        
        # Import models to create tables (shared with ingestion service)
        from app.models import Base
        
        logger.info("Creating/verifying database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified successfully")
            
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Database initialization failed: {e}")
        logger.error(f"Error type: {error_type}")
        
        # Azure-specific error handling
        if "connection" in str(e).lower():
            logger.error("❌ Azure PostgreSQL connection failed during initialization")
            logger.error("💡 Check Azure PostgreSQL service status and network connectivity")
        elif "permission" in str(e).lower():
            logger.error("❌ Database permission denied during table creation")
            logger.error("💡 Check database user has CREATE TABLE permissions")
        elif "ssl" in str(e).lower():
            logger.error("❌ SSL connection failed during initialization")
            logger.error("💡 Check SSL configuration for Azure PostgreSQL")
        elif "timeout" in str(e).lower():
            logger.error("❌ Connection timeout during initialization")
            logger.error("💡 Check Azure PostgreSQL availability and network latency")
        else:
            logger.error(f"❌ Unexpected database initialization error: {error_type}")
            
        # Don't raise exception, just log the error
        logger.warning("Database initialization failed, but continuing...")

