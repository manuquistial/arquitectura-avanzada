"""Database utilities for SQLAlchemy async with PostgreSQL.

Provides shared database setup utilities while maintaining service independence.
Each service still has its own database.py with its specific models.
"""

import os
from typing import AsyncGenerator, Any

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def get_database_url(default: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana") -> str:
    """Get database URL from environment variable.
    
    Args:
        default: Default URL if not set in environment
        
    Returns:
        Database connection URL
    """
    return os.getenv("DATABASE_URL", default)


def create_db_engine(
    database_url: str,
    echo: bool = True,
    pool_size: int = 5,
    max_overflow: int = 10
) -> AsyncEngine:
    """Create SQLAlchemy async engine.
    
    Args:
        database_url: PostgreSQL connection URL
        echo: Log SQL statements
        pool_size: Connection pool size
        max_overflow: Max overflow connections
        
    Returns:
        AsyncEngine instance
    """
    return create_async_engine(
        database_url,
        echo=echo,
        future=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,  # Verify connections before using
    )


def create_session_factory(engine: AsyncEngine) -> sessionmaker:
    """Create async session factory.
    
    Args:
        engine: SQLAlchemy async engine
        
    Returns:
        Session factory
    """
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def create_base() -> Any:
    """Create declarative base for models.
    
    Returns:
        Declarative base class
    """
    return declarative_base()


async def create_db_dependency(session_factory: sessionmaker) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.
    
    Usage:
        async_session = create_session_factory(engine)
        get_db = lambda: create_db_dependency(async_session)
        
        @router.get("/")
        async def endpoint(db: Annotated[AsyncSession, Depends(get_db)]):
            ...
    
    Args:
        session_factory: Session factory from create_session_factory
        
    Yields:
        Database session
    """
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db_tables(engine: AsyncEngine, base: Any) -> None:
    """Initialize database tables.
    
    Args:
        engine: SQLAlchemy async engine
        base: Declarative base with models
    """
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)

