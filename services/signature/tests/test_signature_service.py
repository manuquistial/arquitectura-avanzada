"""Unit tests for signature service."""

import pytest


def test_models():
    """Test signature models."""
    from app.models import SignatureRecord
    
    assert hasattr(SignatureRecord, '__tablename__')


def test_schemas():
    """Test signature schemas."""
    from app import schemas
    
    assert schemas is not None
    assert dir(schemas)  # Has some exports


def test_config():
    """Test configuration."""
    from app.config import Settings
    
    settings = Settings()
    assert settings is not None
    assert settings.environment in ['development', 'staging', 'production']
    assert isinstance(settings.cors_origins, str)
