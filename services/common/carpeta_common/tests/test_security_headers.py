"""
Unit tests for Security Headers Middleware
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from carpeta_common.security_headers import (
    SecurityHeadersMiddleware,
    get_security_headers_config,
    validate_cors_origin
)


@pytest.fixture
def app():
    """Create test FastAPI app with security headers."""
    app = FastAPI()
    
    app.add_middleware(
        SecurityHeadersMiddleware,
        environment="production",
        enable_hsts=True,
        enable_csp=True
    )
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}
    
    return app


def test_security_headers_added(app):
    """Test that security headers are added to responses."""
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == 200
    
    # Check security headers
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    
    assert "X-XSS-Protection" in response.headers
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    
    assert "Referrer-Policy" in response.headers
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_hsts_header_production(app):
    """Test HSTS header is added in production."""
    client = TestClient(app)
    response = client.get("/test")
    
    assert "Strict-Transport-Security" in response.headers
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
    assert "includeSubDomains" in response.headers["Strict-Transport-Security"]


def test_hsts_header_development():
    """Test HSTS header is not added in development."""
    app = FastAPI()
    app.add_middleware(
        SecurityHeadersMiddleware,
        environment="development",
        enable_hsts=True
    )
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    # HSTS should not be added in development
    assert "Strict-Transport-Security" not in response.headers


def test_csp_header_added(app):
    """Test Content-Security-Policy header is added."""
    client = TestClient(app)
    response = client.get("/test")
    
    assert "Content-Security-Policy" in response.headers
    
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp


def test_permissions_policy_header(app):
    """Test Permissions-Policy header is added."""
    client = TestClient(app)
    response = client.get("/test")
    
    assert "Permissions-Policy" in response.headers
    
    policy = response.headers["Permissions-Policy"]
    assert "camera=()" in policy
    assert "microphone=()" in policy
    assert "geolocation=()" in policy


def test_server_header_removed(app):
    """Test Server header is removed for security."""
    client = TestClient(app)
    response = client.get("/test")
    
    # Server header should be removed
    assert "Server" not in response.headers


def test_get_security_headers_config_production():
    """Test getting security headers config for production."""
    headers = get_security_headers_config("production")
    
    assert "X-Content-Type-Options" in headers
    assert "X-Frame-Options" in headers
    assert "Strict-Transport-Security" in headers
    assert "Permissions-Policy" in headers


def test_get_security_headers_config_development():
    """Test getting security headers config for development."""
    headers = get_security_headers_config("development")
    
    assert "X-Content-Type-Options" in headers
    assert "X-Frame-Options" in headers
    # HSTS should not be in development
    assert "Strict-Transport-Security" not in headers


def test_validate_cors_origin_exact_match():
    """Test CORS origin validation with exact match."""
    allowed = ["https://example.com", "https://app.example.com"]
    
    assert validate_cors_origin("https://example.com", allowed) is True
    assert validate_cors_origin("https://app.example.com", allowed) is True
    assert validate_cors_origin("https://evil.com", allowed) is False


def test_validate_cors_origin_wildcard():
    """Test CORS origin validation with wildcard."""
    allowed = ["*.example.com"]
    
    assert validate_cors_origin("https://app.example.com", allowed) is True
    assert validate_cors_origin("https://api.example.com", allowed) is True
    assert validate_cors_origin("https://example.com", allowed) is True
    assert validate_cors_origin("https://evil.com", allowed) is False


def test_validate_cors_origin_allow_all():
    """Test CORS origin validation with allow all."""
    allowed = ["*"]
    
    assert validate_cors_origin("https://example.com", allowed) is True
    assert validate_cors_origin("https://evil.com", allowed) is True


def test_csp_with_report_uri():
    """Test CSP with report URI."""
    app = FastAPI()
    app.add_middleware(
        SecurityHeadersMiddleware,
        environment="production",
        csp_report_uri="https://example.com/csp-report"
    )
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    csp = response.headers["Content-Security-Policy"]
    assert "report-uri https://example.com/csp-report" in csp

