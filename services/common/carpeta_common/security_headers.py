"""
Security Headers Middleware
Adds security headers to all responses for hardening
"""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: restrictive policy
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restrictive policy
    - X-Permitted-Cross-Domain-Policies: none
    
    Usage:
        from carpeta_common.security_headers import SecurityHeadersMiddleware
        
        app.add_middleware(SecurityHeadersMiddleware, environment="production")
    """
    
    def __init__(
        self,
        app: ASGIApp,
        environment: str = "development",
        enable_hsts: bool = True,
        enable_csp: bool = True,
        csp_report_uri: str = None
    ):
        super().__init__(app)
        self.environment = environment
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
        self.csp_report_uri = csp_report_uri
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # X-Content-Type-Options: Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection: Enable XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy: Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # X-Permitted-Cross-Domain-Policies: Restrict Adobe Flash/PDF
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # Strict-Transport-Security (HSTS) - HTTPS only
        if self.enable_hsts and self.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Content-Security-Policy
        if self.enable_csp:
            csp_directives = self._get_csp_directives()
            response.headers["Content-Security-Policy"] = csp_directives
        
        # Permissions-Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = self._get_permissions_policy()
        
        # Remove server header (security by obscurity)
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response
    
    def _get_csp_directives(self) -> str:
        """
        Get Content Security Policy directives.
        
        Restrictive policy for API backend.
        """
        directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles (FastAPI docs)
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
            "object-src 'none'",
        ]
        
        # Add report URI if configured
        if self.csp_report_uri:
            directives.append(f"report-uri {self.csp_report_uri}")
        
        return "; ".join(directives)
    
    def _get_permissions_policy(self) -> str:
        """
        Get Permissions Policy directives.
        
        Restricts browser features.
        """
        return (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=(), "
            "interest-cohort=()"  # Disable FLoC
        )


def get_security_headers_config(environment: str = "production") -> dict:
    """
    Get recommended security headers configuration.
    
    Args:
        environment: Environment name (development, staging, production)
    
    Returns:
        Dictionary of security headers
    """
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Permitted-Cross-Domain-Policies": "none",
        "Permissions-Policy": (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=(), interest-cohort=()"
        ),
    }
    
    # Add HSTS in production
    if environment == "production":
        headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
    
    return headers


def validate_cors_origin(origin: str, allowed_origins: list[str]) -> bool:
    """
    Validate CORS origin against allowed list.
    
    Args:
        origin: Origin header value (e.g., https://example.com)
        allowed_origins: List of allowed origins
    
    Returns:
        True if origin is allowed
    """
    if "*" in allowed_origins:
        return True
    
    # Exact match
    if origin in allowed_origins:
        return True
    
    # Extract hostname from origin (remove scheme and port)
    from urllib.parse import urlparse
    parsed = urlparse(origin)
    hostname = parsed.netloc.split(':')[0] if parsed.netloc else origin
    
    # Wildcard subdomain matching (e.g., *.example.com)
    for allowed in allowed_origins:
        if allowed.startswith("*."):
            domain = allowed[2:]
            # Match subdomains or the domain itself
            if hostname.endswith(f".{domain}") or hostname == domain:
                return True
    
    return False

