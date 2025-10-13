"""
Unit tests for Sharing service
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check."""
    response = client.get("/health")
    assert response.status_code == 200


def test_app_creation():
    """Test app is created successfully."""
    assert app is not None
    assert app.title == "Sharing Service"


def test_app_routes():
    """Test app has routes configured."""
    routes = [route.path for route in app.routes]
    assert "/health" in routes


def test_config_import():
    """Test config can be imported."""
    from app.config import Settings
    settings = Settings()
    assert settings is not None


def test_models_import():
    """Test models can be imported."""
    from app.models import SharePackage, Shortlink
    assert SharePackage is not None
    assert Shortlink is not None


def test_schemas_import():
    """Test schemas can be imported."""
    from app.schemas import SharePackageCreate
    assert SharePackageCreate is not None


def test_database_import():
    """Test database can be imported."""
    from app.database import get_db
    assert get_db is not None


def test_routers_import():
    """Test routers can be imported."""
    from app.routers import sharing
    assert sharing.router is not None


def test_services_import():
    """Test services can be imported."""
    from app.services.token_generator import generate_secure_token
    assert generate_secure_token is not None
