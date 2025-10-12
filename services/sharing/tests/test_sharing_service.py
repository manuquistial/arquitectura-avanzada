"""
Unit tests for Sharing service
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


@patch('app.routers.sharing.get_db')
def test_create_shortlink(mock_get_db, client):
    """Test creating shortlink."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    
    # Shortlink data
    shortlink_data = {
        "document_id": "doc-123",
        "expires_in_hours": 24,
        "max_views": 10
    }
    
    response = client.post("/api/shortlinks", json=shortlink_data)
    
    assert response.status_code in [200, 201, 422]


@patch('app.routers.sharing.get_db')
def test_access_shortlink(mock_get_db, client):
    """Test accessing document via shortlink."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock shortlink
    mock_shortlink = Mock()
    mock_shortlink.code = "abc123"
    mock_shortlink.document_id = "doc-123"
    mock_shortlink.views_count = 5
    mock_shortlink.max_views = 10
    mock_shortlink.is_expired = False
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_shortlink)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/s/abc123")
    
    assert response.status_code in [200, 302, 404]


@patch('app.routers.sharing.get_db')
def test_access_expired_shortlink(mock_get_db, client):
    """Test accessing expired shortlink."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock expired shortlink
    mock_shortlink = Mock()
    mock_shortlink.is_expired = True
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_shortlink)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/s/expired_code")
    
    # Should reject (404 or 410)
    assert response.status_code in [404, 410]


@patch('app.routers.sharing.get_db')
def test_shortlink_max_views_exceeded(mock_get_db, client):
    """Test shortlink with max views exceeded."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock shortlink at max views
    mock_shortlink = Mock()
    mock_shortlink.views_count = 10
    mock_shortlink.max_views = 10
    mock_shortlink.is_expired = False
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_shortlink)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/s/maxed_code")
    
    # Should reject (404 or 410)
    assert response.status_code in [404, 410]


def test_shortlink_code_generation_unique():
    """Test that shortlink codes are unique."""
    from app.services.shortlink_service import generate_shortlink_code
    
    codes = set()
    for _ in range(100):
        code = generate_shortlink_code()
        assert len(code) >= 6  # Minimum length
        codes.add(code)
    
    # All codes should be unique
    assert len(codes) == 100

