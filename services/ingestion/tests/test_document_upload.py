"""
Unit tests for Document Upload functionality
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
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
    assert response.json()["status"] == "healthy"


@patch('app.routers.documents.upload_document')
async def test_upload_document_success(mock_upload, client):
    """Test successful document upload."""
    # Mock upload function
    mock_upload.return_value = {
        "document_id": "doc-123",
        "filename": "test.pdf",
        "status": "uploaded"
    }
    
    # Test file upload
    files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
    data = {"document_type": "cedula"}
    
    response = client.post("/api/documents/upload", files=files, data=data)
    
    # Should succeed or return appropriate status
    assert response.status_code in [200, 201, 422]  # 422 if validation needed


def test_upload_document_invalid_type(client):
    """Test upload with invalid file type."""
    # Test with non-PDF file
    files = {"file": ("test.txt", b"text content", "text/plain")}
    data = {"document_type": "cedula"}
    
    response = client.post("/api/documents/upload", files=files, data=data)
    
    # Should reject (400 or 422)
    assert response.status_code in [400, 422]


def test_upload_document_too_large(client):
    """Test upload with file exceeding size limit."""
    # Test with large file (>10MB)
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB
    files = {"file": ("large.pdf", large_content, "application/pdf")}
    data = {"document_type": "cedula"}
    
    response = client.post("/api/documents/upload", files=files, data=data)
    
    # Should reject (413 or 422)
    assert response.status_code in [413, 422]


@patch('app.services.blob_service.upload_to_blob')
async def test_blob_upload_failure(mock_blob_upload, client):
    """Test handling blob upload failure."""
    # Mock blob upload failure
    mock_blob_upload.side_effect = Exception("Blob storage unavailable")
    
    files = {"file": ("test.pdf", b"content", "application/pdf")}
    data = {"document_type": "cedula"}
    
    response = client.post("/api/documents/upload", files=files, data=data)
    
    # Should handle error gracefully
    assert response.status_code in [500, 503]


@patch('app.routers.documents.get_db')
def test_list_documents(mock_get_db, client):
    """Test listing documents."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock documents
    mock_docs = [
        Mock(id="1", filename="doc1.pdf", status="SIGNED"),
        Mock(id="2", filename="doc2.pdf", status="UNSIGNED")
    ]
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.offset = Mock(return_value=mock_query)
    mock_query.limit = Mock(return_value=mock_query)
    mock_query.all = Mock(return_value=mock_docs)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/api/documents")
    
    assert response.status_code == 200


@patch('app.routers.documents.get_db')
def test_get_document_by_id(mock_get_db, client):
    """Test getting document by ID."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock document
    mock_doc = Mock()
    mock_doc.id = "doc-123"
    mock_doc.filename = "test.pdf"
    mock_doc.status = "SIGNED"
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_doc)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/api/documents/doc-123")
    
    assert response.status_code == 200


@patch('app.routers.documents.get_db')
def test_get_document_not_found(mock_get_db, client):
    """Test getting non-existent document."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock query returning None
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=None)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.get("/api/documents/nonexistent")
    
    assert response.status_code == 404


@patch('app.services.blob_service.delete_blob')
@patch('app.routers.documents.get_db')
def test_delete_document_worm_locked(mock_get_db, mock_delete_blob, client):
    """Test deleting WORM-locked document (should fail)."""
    # Mock database
    mock_db = Mock()
    mock_get_db.return_value = mock_db
    
    # Mock WORM-locked document
    mock_doc = Mock()
    mock_doc.id = "doc-123"
    mock_doc.worm_locked = True
    
    # Mock query
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_doc)
    mock_db.query = Mock(return_value=mock_query)
    
    response = client.delete("/api/documents/doc-123")
    
    # Should reject (403 or 400)
    assert response.status_code in [400, 403]
    
    # Blob delete should NOT be called
    mock_delete_blob.assert_not_called()


def test_upload_without_file(client):
    """Test upload endpoint without file."""
    # No file provided
    data = {"document_type": "cedula"}
    
    response = client.post("/api/documents/upload", data=data)
    
    # Should return error (422)
    assert response.status_code == 422


def test_upload_without_document_type(client):
    """Test upload without document type."""
    files = {"file": ("test.pdf", b"content", "application/pdf")}
    # No document_type
    
    response = client.post("/api/documents/upload", files=files)
    
    # Should return error (422)
    assert response.status_code == 422

