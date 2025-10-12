"""Database connection for sharing service."""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.models import Base

logger = logging.getLogger(__name__)

# Settings
settings = Settings()

# Import utilities from common package (with fallback)
try:
    from carpeta_common.db_utils import (
        get_database_url,
        create_db_engine,
        create_session_factory,
        create_db_dependency,
        init_db_tables
    )
    COMMON_AVAILABLE = True
except ImportError:
    COMMON_AVAILABLE = False
    logger.warning("carpeta_common not installed, using fallback")

if COMMON_AVAILABLE:
    # Use common utilities
    DATABASE_URL = get_database_url()
    engine = create_db_engine(DATABASE_URL)
    async_session = create_session_factory(engine)
else:
    # Fallback implementation
    DATABASE_URL = settings.database_url
    engine = create_async_engine(DATABASE_URL, echo=True, future=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Initialize database tables for sharing service."""
    if COMMON_AVAILABLE:
        await init_db_tables(engine, Base)
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database initialized")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session (FastAPI dependency)."""
    if COMMON_AVAILABLE:
        async for session in create_db_dependency(async_session):
            yield session
    else:
        async with async_session() as session:
            yield session

