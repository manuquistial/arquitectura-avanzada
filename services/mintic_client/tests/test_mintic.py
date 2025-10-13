"""
Unit tests for MinTIC Client Service
"""

import pytest


def test_imports():
    """Test basic imports work."""
    from app.config import Settings
    from app.models import RegisterCitizenRequest, MinTICResponse
    from app.client import MinTICClient
    assert Settings is not None
    assert RegisterCitizenRequest is not None
    assert MinTICResponse is not None
    assert MinTICClient is not None


def test_config_creation():
    """Test config can be created."""
    from app.config import Settings
    settings = Settings()
    assert settings.mintic_base_url is not None
    assert settings.mintic_operator_id is not None


def test_models_structure():
    """Test models have expected structure."""
    from app.models import RegisterCitizenRequest
    # Check model has expected fields
    assert hasattr(RegisterCitizenRequest, 'model_fields')


def test_client_instantiation():
    """Test client can be instantiated."""
    from app.client import MinTICClient
    from app.config import Settings
    settings = Settings()
    client = MinTICClient(settings=settings)
    assert client is not None


def test_sanitizer_import():
    """Test sanitizer can be imported."""
    from app.sanitizer import DataSanitizer
    assert DataSanitizer is not None


def test_telemetry_import():
    """Test telemetry can be imported."""
    from app import telemetry
    assert telemetry is not None


def test_rate_limiter_import():
    """Test rate limiter can be imported."""
    from app.hub_rate_limiter import HubRateLimiter
    assert HubRateLimiter is not None


def test_app_creation():
    """Test FastAPI app module exists."""
    # Test that main module can be imported
    from app import main
    assert main is not None
    # Test create_app exists
    assert hasattr(main, 'create_app')
