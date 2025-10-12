"""Database configuration for signature service."""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL (from environment variable)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana"
)

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Create async session factory
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


async def init_db() -> None:
    """Initialize database (create tables if not exist)."""
    from app.models import SignatureRecord  # Import models
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

