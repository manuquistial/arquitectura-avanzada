"""Authentication middleware."""

import logging
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import Settings

logger = logging.getLogger(__name__)

# Public routes that don't require authentication
PUBLIC_ROUTES = ["/health", "/docs", "/openapi.json"]


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware."""

    def __init__(self, app, settings: Settings) -> None:
        """Initialize middleware."""
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request."""
        # Skip auth for public routes
        if any(request.url.path.startswith(route) for route in PUBLIC_ROUTES):
            return await call_next(request)

        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid authorization header"},
            )

        token = auth_header.replace("Bearer ", "")

        # Verify JWT token
        try:
            payload = self.verify_token(token)
            # Add user info to request state
            request.state.user = payload
            logger.info(f"Authenticated user: {payload.get('sub')}")
        except JWTError as e:
            logger.error(f"Token verification failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token"},
            )

        return await call_next(request)

    def verify_token(self, token: str) -> dict:
        """Verify JWT token.

        In production, verify against Cognito JWKs.
        """
        try:
            # Decode without verification for development
            # In production, fetch and use Cognito public keys
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm],
                options={"verify_signature": False},  # TODO: Enable in production
            )
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise

