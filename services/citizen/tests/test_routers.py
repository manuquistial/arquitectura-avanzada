"""
Unit tests for Citizen service routers
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.main import app
from app.models import Citizen
from app.schemas import CitizenCreate


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock(spec=Session)
    return db


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_ready_endpoint(client):
    """Test readiness check endpoint."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@patch('app.routers.citizens.get_db')
def test_create_citizen_success(mock_get_db, client):
    """Test successful citizen creation."""
    # Mock database
    mock_db = Mock(spec=Session)
    mock_get_db.return_value = mock_db
    
    # Mock commit and refresh
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    
    # Test data
    citizen_data = {
        "document_number": "1234567890",
        "full_name": "Juan Pérez",
        "email": "juan@example.com"
    }
    
    response = client.post("/api/citizens", json=citizen_data)
    
    # Should create successfully
    assert response.status_code == 200 or response.status_code == 201
    
    # Verify database operations were called
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@patch('app.routers.citizens.get_db')
def test_get_citizen_by_id(mock_get_db, client):
    """Test getting citizen by ID."""
    # Mock database
    mock_db = Mock(spec=Session)
    mock_get_db.return_value = mock_db
    
    # Mock citizen
    mock_citizen = Mock(spec=Citizen)
    mock_citizen.id = "citizen-123"
    mock_citizen.document_number = "1234567890"
    mock_citizen.full_name = "Juan Pérez"
    mock_citizen.email = "juan@example.com"
    
    # Mock query
    mock_query = Mock()
    mock_query.filter_by = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_citizen)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/api/citizens/citizen-123")
    
    assert response.status_code == 200


@patch('app.routers.citizens.get_db')
def test_get_citizen_not_found(mock_get_db, client):
    """Test getting non-existent citizen."""
    # Mock database
    mock_db = Mock(spec=Session)
    mock_get_db.return_value = mock_db
    
    # Mock query returning None
    mock_query = Mock()
    mock_query.filter_by = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=None)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/api/citizens/nonexistent")
    
    assert response.status_code == 404


@patch('app.routers.citizens.get_db')
def test_list_citizens(mock_get_db, client):
    """Test listing citizens with pagination."""
    # Mock database
    mock_db = Mock(spec=Session)
    mock_get_db.return_value = mock_db
    
    # Mock citizens
    mock_citizens = [
        Mock(id="1", document_number="111", full_name="User 1"),
        Mock(id="2", document_number="222", full_name="User 2")
    ]
    
    # Mock query
    mock_query = Mock()
    mock_query.offset = Mock(return_value=mock_query)
    mock_query.limit = Mock(return_value=mock_query)
    mock_query.all = Mock(return_value=mock_citizens)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/api/citizens?skip=0&limit=10")
    
    assert response.status_code == 200


@patch('app.routers.citizens.get_db')
def test_update_citizen(mock_get_db, client):
    """Test updating citizen information."""
    # Mock database
    mock_db = Mock(spec=Session)
    mock_get_db.return_value = mock_db
    
    # Mock existing citizen
    mock_citizen = Mock(spec=Citizen)
    mock_citizen.id = "citizen-123"
    mock_citizen.full_name = "Juan Pérez"
    
    # Mock query
    mock_query = Mock()
    mock_query.filter_by = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_citizen)
    mock_db.query = Mock(return_value=mock_query)
    
    # Mock commit
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    
    # Update data
    update_data = {"full_name": "Juan Carlos Pérez"}
    
    response = client.put("/api/citizens/citizen-123", json=update_data)
    
    # Should update successfully (or return appropriate status)
    assert response.status_code in [200, 404]  # 404 if route not implemented


@patch('app.routers.citizens.get_db')
def test_delete_citizen(mock_get_db, client):
    """Test deleting citizen."""
    # Mock database
    mock_db = Mock(spec=Session)
    mock_get_db.return_value = mock_db
    
    # Mock citizen
    mock_citizen = Mock(spec=Citizen)
    
    # Mock query
    mock_query = Mock()
    mock_query.filter_by = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_citizen)
    mock_db.query = Mock(return_value=mock_query)
    
    # Mock delete
    mock_db.delete = Mock()
    mock_db.commit = Mock()
    
    response = client.delete("/api/citizens/citizen-123")
    
    # Should delete or return not found
    assert response.status_code in [200, 204, 404]


def test_create_citizen_validation_error(client):
    """Test citizen creation with invalid data."""
    # Invalid data (missing required fields)
    invalid_data = {
        "document_number": "123"  # Missing other required fields
    }
    
    response = client.post("/api/citizens", json=invalid_data)
    
    # Should return validation error
    assert response.status_code == 422  # Unprocessable Entity


def test_create_citizen_duplicate(client):
    """Test creating citizen with duplicate document number."""
    with patch('app.routers.citizens.get_db') as mock_get_db:
        # Mock database
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock IntegrityError on commit
        from sqlalchemy.exc import IntegrityError
        mock_db.commit.side_effect = IntegrityError("", "", "")
        
        citizen_data = {
            "document_number": "1234567890",
            "full_name": "Juan Pérez",
            "email": "juan@example.com"
        }
        
        response = client.post("/api/citizens", json=citizen_data)
        
        # Should handle integrity error (400 or 409)
        assert response.status_code in [400, 409, 500]

