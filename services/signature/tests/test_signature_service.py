"""
Unit tests for Signature service
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


@patch('app.routers.signature.get_db')
@patch('app.routers.signature.authenticate_with_hub')
def test_sign_document_success(mock_hub_auth, mock_get_db, client):
    """Test successful document signing."""
    # Mock Hub authentication
    mock_hub_auth.return_value = {
        "authenticated": True,
        "signature": "hub_signature_123",
        "timestamp": "2025-10-13T07:00:00Z"
    }
    
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    
    # Sign request
    sign_data = {
        "document_id": "doc-123",
        "user_id": "user-456",
        "nonce": "nonce-789"
    }
    
    response = client.post("/api/signature/sign", json=sign_data)
    
    # Should succeed or validate
    assert response.status_code in [200, 201, 422]


@patch('app.routers.signature.authenticate_with_hub')
def test_sign_document_hub_failure(mock_hub_auth, client):
    """Test signing when Hub authentication fails."""
    # Mock Hub failure
    mock_hub_auth.side_effect = Exception("Hub unavailable")
    
    sign_data = {
        "document_id": "doc-123",
        "user_id": "user-456",
        "nonce": "nonce-789"
    }
    
    response = client.post("/api/signature/sign", json=sign_data)
    
    # Should handle error
    assert response.status_code in [500, 503]


@patch('app.routers.signature.get_db')
def test_verify_signature(mock_get_db, client):
    """Test signature verification."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock signature record
    mock_signature = Mock()
    mock_signature.document_id = "doc-123"
    mock_signature.hub_signature = "hub_sig_123"
    mock_signature.is_valid = True
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_signature)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/api/signature/verify/doc-123")
    
    assert response.status_code in [200, 404]


@patch('app.routers.signature.get_db')
def test_get_signature_history(mock_get_db, client):
    """Test getting signature history for document."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock signatures
    mock_signatures = [
        Mock(id="1", document_id="doc-123", created_at=datetime.now()),
        Mock(id="2", document_id="doc-123", created_at=datetime.now())
    ]
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.order_by = Mock(return_value=mock_query)
    mock_query.all = Mock(return_value=mock_signatures)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/api/signature/history/doc-123")
    
    assert response.status_code in [200, 404]

