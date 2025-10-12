"""Tests for sharing service."""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.schemas import CreateSharePackageRequest


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


@pytest.fixture
def valid_share_request():
    """Valid share package request."""
    return CreateSharePackageRequest(
        owner_email="owner@example.com",
        document_ids=["doc1", "doc2"],
        expires_at=datetime.utcnow() + timedelta(days=7),
        audience="public",
        requires_auth=False
    )


@pytest.mark.asyncio
async def test_create_share_package_success(client, valid_share_request):
    """Test creating share package successfully."""
    with patch("app.routers.sharing.abac_client.authorize", new_callable=AsyncMock) as mock_abac:
        mock_abac.return_value = (True, "Authorized")
        
        response = client.post(
            "/share/packages",
            json=valid_share_request.model_dump(mode="json")
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "token" in data
        assert "shortlink" in data
        assert data["document_count"] == 2


@pytest.mark.asyncio
async def test_create_share_package_unauthorized(client, valid_share_request):
    """Test creating share package when not authorized."""
    with patch("app.routers.sharing.abac_client.authorize", new_callable=AsyncMock) as mock_abac:
        mock_abac.return_value = (False, "Not owner")
        
        response = client.post(
            "/share/packages",
            json=valid_share_request.model_dump(mode="json")
        )
        
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_share_package_expired_date(client):
    """Test creating share package with expired date."""
    expired_request = CreateSharePackageRequest(
        owner_email="owner@example.com",
        document_ids=["doc1"],
        expires_at=datetime.utcnow() - timedelta(days=1),  # Past date
        audience="public"
    )
    
    response = client.post(
        "/share/packages",
        json=expired_request.model_dump(mode="json")
    )
    
    assert response.status_code == 400
    assert "future" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_access_share_package_not_found(client):
    """Test accessing non-existent share package."""
    response = client.get("/share/s/nonexistent")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_access_share_package_expired(client):
    """Test accessing expired share package."""
    # This would require creating a package with past expiration
    # and testing access - implementation depends on test DB setup
    pass


@pytest.mark.asyncio
async def test_access_share_package_revoked(client):
    """Test accessing revoked share package."""
    # This would require creating a package, revoking it,
    # and testing access - implementation depends on test DB setup
    pass


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

