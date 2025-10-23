"""Database configuration for MinTIC Client service."""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.config import Settings
from app.database_models import Base

logger = logging.getLogger(__name__)

# Global variables for database connection
engine = None
SessionLocal = None

# Create settings instance
settings = Settings()

def init_database():
    """Initialize database connection and create tables."""
    global engine, SessionLocal
    
    # Create database URL (using psycopg driver like ingestion service)
    database_url = f"postgresql+psycopg://{settings.database_user}:{settings.database_password}@{settings.database_host}:{settings.database_port}/{settings.database_name}?sslmode=require"
    
    try:
        # Create engine
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=settings.database_echo
        )
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise


def get_db():
    """Get database session."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_database():
    """Close database connection."""
    global engine
    if engine:
        engine.dispose()
        logger.info("Database connection closed")
