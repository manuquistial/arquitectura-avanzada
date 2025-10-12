"""
Unit tests for Auth service endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_ready_endpoint(client):
    """Test readiness check."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["oidc_enabled"] is True


def test_root_endpoint(client):
    """Test root endpoint returns service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "auth"
    assert "endpoints" in data
    assert "oidc_discovery" in data["endpoints"]


def test_oidc_discovery(client):
    """Test OIDC discovery endpoint."""
    response = client.get("/.well-known/openid-configuration")
    assert response.status_code == 200
    
    data = response.json()
    assert "issuer" in data
    assert "authorization_endpoint" in data
    assert "token_endpoint" in data
    assert "jwks_uri" in data
    assert "response_types_supported" in data
    assert "scopes_supported" in data


def test_jwks_endpoint(client):
    """Test JWKS endpoint."""
    response = client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    
    data = response.json()
    assert "keys" in data
    assert isinstance(data["keys"], list)


def test_token_endpoint_authorization_code(client):
    """Test token endpoint with authorization_code grant."""
    token_data = {
        "grant_type": "authorization_code",
        "code": "test_code_123"
    }
    
    response = client.post("/api/auth/token", json=token_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"


def test_token_endpoint_refresh_token(client):
    """Test token endpoint with refresh_token grant."""
    token_data = {
        "grant_type": "refresh_token",
        "refresh_token": "test_refresh_token"
    }
    
    response = client.post("/api/auth/token", json=token_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_token_endpoint_client_credentials(client):
    """Test token endpoint with client_credentials grant."""
    token_data = {
        "grant_type": "client_credentials",
        "client_id": "test_client",
        "client_secret": "test_secret"
    }
    
    response = client.post("/api/auth/token", json=token_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_token_endpoint_missing_code(client):
    """Test token endpoint with missing authorization code."""
    token_data = {
        "grant_type": "authorization_code"
        # Missing 'code'
    }
    
    response = client.post("/api/auth/token", json=token_data)
    
    assert response.status_code == 400


def test_token_endpoint_invalid_grant_type(client):
    """Test token endpoint with invalid grant type."""
    token_data = {
        "grant_type": "invalid_grant"
    }
    
    response = client.post("/api/auth/token", json=token_data)
    
    assert response.status_code == 400


def test_userinfo_endpoint(client):
    """Test userinfo endpoint with valid token."""
    response = client.get(
        "/api/auth/userinfo",
        headers={"Authorization": "Bearer test_token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "sub" in data
    assert "email" in data


def test_userinfo_endpoint_missing_auth(client):
    """Test userinfo endpoint without authorization."""
    response = client.get("/api/auth/userinfo")
    
    assert response.status_code == 401


def test_userinfo_endpoint_invalid_scheme(client):
    """Test userinfo endpoint with invalid auth scheme."""
    response = client.get(
        "/api/auth/userinfo",
        headers={"Authorization": "Basic dGVzdDp0ZXN0"}  # Basic auth
    )
    
    assert response.status_code == 401


def test_logout_endpoint(client):
    """Test logout endpoint."""
    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": "Bearer test_token"}
    )
    
    assert response.status_code == 200


def test_create_session(client):
    """Test creating session."""
    session_data = {
        "user_id": "user-123",
        "email": "user@example.com",
        "roles": ["user"]
    }
    
    response = client.post("/api/sessions", json=session_data)
    
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["user_id"] == "user-123"


def test_get_session(client):
    """Test getting session by ID."""
    response = client.get("/api/sessions/test-session-id")
    
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data


def test_delete_session(client):
    """Test deleting session."""
    response = client.delete("/api/sessions/test-session-id")
    
    assert response.status_code == 200


def test_refresh_session(client):
    """Test refreshing session."""
    response = client.post("/api/sessions/test-session-id/refresh")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Session refreshed"

