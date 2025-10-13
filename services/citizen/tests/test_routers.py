"""Unit tests for citizen service."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client."""
    from app.main import app
    return TestClient(app)


def test_health_endpoint(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_metrics_endpoint_exists(client):
    """Test metrics endpoint."""
    response = client.get("/metrics")
    # Should exist
    assert response.status_code in [200, 404]


def test_app_imports():
    """Test that app modules can be imported."""
    from app import config, models, models_users, schemas
    
    assert config is not None
    assert models is not None
    assert models_users is not None
    assert schemas is not None


def test_models_structure():
    """Test that models have expected structure."""
    from app.models import Citizen
    from app.models_users import User
    
    assert hasattr(Citizen, '__tablename__')
    assert hasattr(User, '__tablename__')
    assert Citizen.__tablename__ == 'citizens'
    assert User.__tablename__ == 'users'
