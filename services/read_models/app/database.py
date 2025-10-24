"""Database configuration for read models service."""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlalchemy.ext.declarative import declarative_base

from app.config import Settings

logger = logging.getLogger(__name__)

# Get configuration
settings = Settings()

# Get database URL from configuration
DATABASE_URL = settings.get_database_url()

# Create async engine with optimized configuration
def create_database_engine():
    """Create database engine with configuration-based settings."""
    # Base configuration optimized for Azure PostgreSQL
    engine_config = {
        "echo": False,  # Disable SQL echo for production  # Enable echo in debug mode
        "future": True,
        "pool_size": 2,  # Minimal pool for limited resources  # Reduced for better resource management
        "max_overflow": 3,  # Minimal overflow for limited resources  # Reduced for better resource management
        "pool_pre_ping": True,
        "pool_recycle": 1800,  # Recycle connections every 30 minutes  # Recycle connections every hour
        "pool_timeout": 10,  # Shorter timeout for faster failure  # Timeout for getting connection from pool
    }
    
    # Azure PostgreSQL configuration (proven to work in tests)
    if settings.is_azure_environment():
        engine_config["connect_args"] = {
            "sslmode": "require",  # Use sslmode instead of ssl for psycopg
            "connect_timeout": 10,
            "application_name": "read-models-service"
        }
        logger.info("Using Azure PostgreSQL configuration with psycopg")
    else:
        engine_config["connect_args"] = {
            "sslmode": settings.database_sslmode,
            "application_name": "read-models-service"
        }
        logger.info("Using local PostgreSQL configuration")
    
    return create_async_engine(DATABASE_URL, **engine_config)

# Create engine with error handling for Azure services
try:
    engine = create_database_engine()
    logger.info("✅ Database engine created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create database engine: {e}")
    # Fallback to simple engine for local development
    from sqlalchemy.ext.asyncio import create_async_engine
    fallback_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana"
    engine = create_async_engine(fallback_url, echo=True, future=True)
    logger.warning("⚠️ Using fallback database engine for local development")

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base for models
Base = declarative_base()


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
        logger.info(f"Database host: {settings.database_host}")
        logger.info(f"Database port: {settings.database_port}")
        logger.info(f"Database name: {settings.database_name}")
        logger.info(f"Database user: {settings.database_user}")
        logger.info(f"SSL mode: {settings.database_sslmode}")
        
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
        logger.info(f"Database URL: {settings.get_database_url()[:50]}...")
        logger.info(f"Azure environment: {settings.is_azure_environment()}")
        
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

