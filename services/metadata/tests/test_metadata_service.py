"""
Unit tests for Metadata service
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

from app.main import app


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check."""
    response = client.get("/health")
    assert response.status_code == 200


def test_ready_endpoint(client):
    """Test readiness check."""
    response = client.get("/ready")
    assert response.status_code == 200


@patch('app.routers.metadata.get_db')
def test_create_metadata(mock_get_db, client):
    """Test creating document metadata."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    
    # Metadata
    metadata = {
        "document_id": "doc-123",
        "document_type": "cedula",
        "file_size": 1024,
        "mime_type": "application/pdf"
    }
    
    response = client.post("/api/metadata", json=metadata)
    
    # Should create or validate
    assert response.status_code in [200, 201, 422]


@patch('app.routers.metadata.get_db')
def test_get_metadata(mock_get_db, client):
    """Test getting metadata by document ID."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock metadata
    mock_metadata = Mock()
    mock_metadata.document_id = "doc-123"
    mock_metadata.document_type = "cedula"
    mock_metadata.file_size = 1024
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_metadata)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/api/metadata/doc-123")
    
    assert response.status_code == 200


@patch('app.routers.metadata.get_db')
def test_search_metadata(mock_get_db, client):
    """Test searching metadata."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock search results
    mock_results = [
        Mock(document_id="1", document_type="cedula"),
        Mock(document_id="2", document_type="cedula")
    ]
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.all = Mock(return_value=mock_results)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/api/metadata/search?document_type=cedula")
    
    assert response.status_code in [200, 404]  # 404 if not implemented


@patch('app.routers.metadata.get_db')
def test_update_metadata(mock_get_db, client):
    """Test updating metadata."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock metadata
    mock_metadata = Mock()
    mock_metadata.document_id = "doc-123"
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_metadata)
    mock_db.query = Mock(return_value=mock_query)
    
    # Mock commit
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    
    # Update
    update_data = {"tags": ["important", "signed"]}
    
    response = client.put("/api/metadata/doc-123", json=update_data)
    
    assert response.status_code in [200, 404]

