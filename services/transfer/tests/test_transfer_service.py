"""
Unit tests for Transfer service
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
    assert app.title == "Transfer Service"


def test_models_import():
    """Test models can be imported."""
    from app.models import TransferCitizenRequest, TransferConfirmRequest
    assert TransferCitizenRequest is not None
    assert TransferConfirmRequest is not None


def test_database_import():
    """Test database can be imported."""
    from app.database import get_db
    assert get_db is not None


def test_router_import():
    """Test router can be imported."""
    from app.routers import transfer
    assert transfer.router is not None
