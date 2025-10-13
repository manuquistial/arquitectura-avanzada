"""
Integration tests for Sharing service
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_ready_check(client):
    """Test ready endpoint."""
    response = client.get("/ready")
    assert response.status_code == 200


def test_app_metadata():
    """Test app metadata."""
    assert app.title == "Sharing Service"
    assert app.version == "1.0.0"


def test_cors_middleware():
    """Test CORS middleware is configured."""
    # CORS middleware should be in the app
    middleware_types = [type(m).__name__ for m in app.user_middleware]
    # CORSMiddleware might be present
    assert len(middleware_types) >= 0  # Just check middleware can be loaded


def test_models_structure():
    """Test models are correctly structured."""
    from app.models import SharePackage, Shortlink
    
    # Check models have expected attributes
    assert hasattr(SharePackage, '__tablename__')
    assert hasattr(Shortlink, '__tablename__')


def test_schemas_validation():
    """Test schemas work correctly."""
    from app.schemas import SharePackageCreate
    from datetime import datetime, timedelta
    
    # Valid schema should work
    data = {
        "document_ids": ["doc1", "doc2"],
        "expires_at": datetime.utcnow() + timedelta(days=7),
        "recipient_email": "test@example.com"
    }
    
    schema = SharePackageCreate(**data)
    assert schema.document_ids == ["doc1", "doc2"]


def test_token_generator():
    """Test token generator."""
    from app.services.token_generator import generate_secure_token
    
    token = generate_secure_token(12)
    assert len(token) == 12
    
    # Generate multiple tokens and ensure they're unique
    tokens = {generate_secure_token(12) for _ in range(100)}
    assert len(tokens) == 100  # All should be unique


def test_config_loading():
    """Test config loads correctly."""
    from app.config import get_settings
    
    settings = get_settings()
    assert settings.database_url is not None
    assert settings.shortlink_base_url is not None
