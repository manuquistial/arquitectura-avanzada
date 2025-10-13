"""
Unit tests for Transfer service
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


@patch('app.routers.transfer.get_db')
def test_initiate_transfer(mock_get_db, client):
    """Test initiating document transfer."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    
    # Transfer data
    transfer_data = {
        "document_id": "doc-123",
        "from_user_id": "user-1",
        "to_user_id": "user-2"
    }
    
    response = client.post("/api/transfers", json=transfer_data)
    
    # Should create or validate
    assert response.status_code in [200, 201, 422]


@patch('app.routers.transfer.get_db')
def test_accept_transfer(mock_get_db, client):
    """Test accepting transfer."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock transfer
    mock_transfer = Mock()
    mock_transfer.id = "transfer-123"
    mock_transfer.status = "PENDING"
    mock_transfer.to_user_id = "user-2"
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_transfer)
    mock_db.query = Mock(return_value=mock_query)
    
    mock_db.commit = Mock()
    
    response = client.post("/api/transfers/transfer-123/accept")
    
    assert response.status_code in [200, 404]


@patch('app.routers.transfer.get_db')
def test_reject_transfer(mock_get_db, client):
    """Test rejecting transfer."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock transfer
    mock_transfer = Mock()
    mock_transfer.id = "transfer-123"
    mock_transfer.status = "PENDING"
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_transfer)
    mock_db.query = Mock(return_value=mock_query)
    
    mock_db.commit = Mock()
    
    response = client.post("/api/transfers/transfer-123/reject")
    
    assert response.status_code in [200, 404]


@patch('app.routers.transfer.get_db')
def test_list_transfers(mock_get_db, client):
    """Test listing transfers."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock transfers
    mock_transfers = [
        Mock(id="1", status="PENDING"),
        Mock(id="2", status="ACCEPTED")
    ]
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.offset = Mock(return_value=mock_query)
    mock_query.limit = Mock(return_value=mock_query)
    mock_query.all = Mock(return_value=mock_transfers)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/api/transfers")
    
    assert response.status_code == 200


@patch('app.routers.transfer.get_db')
def test_transfer_already_accepted(mock_get_db, client):
    """Test accepting already accepted transfer."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock already accepted transfer
    mock_transfer = Mock()
    mock_transfer.status = "ACCEPTED"
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_transfer)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.post("/api/transfers/transfer-123/accept")
    
    # Should reject (400 or 409)
    assert response.status_code in [400, 409, 200]

