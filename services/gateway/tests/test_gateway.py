"""Basic tests for gateway service."""

import pytest

def test_imports():
    """Test that main modules can be imported."""
    from app import config, main, proxy, sanitizer
    
    assert config is not None
    assert main is not None
    assert proxy is not None
    assert sanitizer is not None

def test_config_loads():
    """Test configuration loads."""
    from app.config import settings
    
    assert settings is not None
    assert settings.environment in ['development', 'staging', 'production']

