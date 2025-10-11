"""Unit tests for transfer service."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_transfer_citizen_missing_idempotency_key(client):
    """Test transfer without idempotency key."""
    response = client.post(
        "/api/transferCitizen",
        json={
            "id": 123,
            "citizenName": "Test User",
            "citizenEmail": "test@example.com",
            "urlDocuments": {"doc1": ["https://example.com/doc1"]},
            "confirmAPI": "https://example.com/confirm",
        },
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 422  # Missing header


def test_transfer_confirm(client):
    """Test transfer confirmation."""
    response = client.post(
        "/api/transferCitizenConfirm",
        json={"id": 123, "req_status": 1},
    )
    assert response.status_code == 200
    assert "confirmed" in response.json()["message"]


def test_transfer_confirm_failure(client):
    """Test transfer confirmation with failure."""
    response = client.post(
        "/api/transferCitizenConfirm",
        json={"id": 123, "req_status": 0},
    )
    assert response.status_code == 200
    assert "failed" in response.json()["message"]

