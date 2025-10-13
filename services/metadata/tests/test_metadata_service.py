"""Unit tests for metadata service."""

import pytest


def test_models_structure():
    """Test DocumentMetadata model."""
    from app.models import DocumentMetadata
    
    assert hasattr(DocumentMetadata, '__tablename__')
    assert hasattr(DocumentMetadata, 'id')
    assert hasattr(DocumentMetadata, 'filename')
    assert hasattr(DocumentMetadata, 'citizen_id')


def test_schemas():
    """Test schemas."""
    from app.schemas import DocumentResponse, SearchResult
    
    assert DocumentResponse is not None
    assert SearchResult is not None


def test_database_module():
    """Test database functions."""
    from app import database
    
    assert hasattr(database, 'get_db')
    assert hasattr(database, 'engine')


def test_config_loads():
    """Test config loads."""
    from app.config import Settings
    
    settings = Settings()
    assert settings.environment in ['development', 'staging', 'production']
    assert isinstance(settings.database_url, str)
    assert isinstance(settings.opensearch_host, str)
    assert isinstance(settings.cors_origins, str)
