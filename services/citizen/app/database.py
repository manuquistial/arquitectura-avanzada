"""Database configuration for citizen service."""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

# Import utilities from common package (install with: poetry add ../common)
try:
    from carpeta_common.db_utils import (
        get_database_url,
        create_db_engine,
        create_session_factory,
        create_base,
        create_db_dependency,
        init_db_tables
    )
    COMMON_AVAILABLE = True
except ImportError:
    # Fallback if common not installed
    import os
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    COMMON_AVAILABLE = False

logger = logging.getLogger(__name__)

if COMMON_AVAILABLE:
    # Use common utilities
    DATABASE_URL = get_database_url()
    engine = create_db_engine(DATABASE_URL)
    async_session = create_session_factory(engine)
    Base = create_base()
else:
    # Fallback implementation
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana"
    )
    engine = create_async_engine(DATABASE_URL, echo=True, future=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    Base = declarative_base()


async def init_db() -> None:
    """Initialize database tables for citizen service."""
    if COMMON_AVAILABLE:
        await init_db_tables(engine, Base)
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session (FastAPI dependency)."""
    if COMMON_AVAILABLE:
        async for session in create_db_dependency(async_session):
            yield session
    else:
        async with async_session() as session:
            yield session

