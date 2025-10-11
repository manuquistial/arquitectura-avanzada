"""Service proxy for routing requests."""

import logging
from typing import Any

import httpx
from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.config import Settings

logger = logging.getLogger(__name__)


class ProxyService:
    """Proxy service for routing requests to backend services."""

    def __init__(self, settings: Settings) -> None:
        """Initialize proxy."""
        self.settings = settings
        self.service_map = {
            "citizen": settings.citizen_service_url,
            "ingestion": settings.ingestion_service_url,
            "metadata": settings.metadata_service_url,
            "signature": settings.signature_service_url,
            "transfer": settings.transfer_service_url,
            "sharing": settings.sharing_service_url,
            "notification": settings.notification_service_url,
            "mintic": settings.mintic_client_url,
        }

    async def forward_request(self, request: Request, path: str) -> JSONResponse:
        """Forward request to appropriate backend service."""
        # Determine target service from path
        service = self._get_service_from_path(path)
        if not service:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Service not found"},
            )

        target_url = f"{service}/{path}"
        logger.info(f"Proxying {request.method} request to {target_url}")

        try:
            # Forward request
            async with httpx.AsyncClient() as client:
                # Get request body if present
                body = None
                if request.method in ["POST", "PUT", "PATCH"]:
                    body = await request.body()

                response = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=dict(request.headers),
                    params=dict(request.query_params),
                    content=body,
                    timeout=30.0,
                )

                return JSONResponse(
                    status_code=response.status_code,
                    content=response.json() if response.content else {},
                )

        except httpx.HTTPError as e:
            logger.error(f"Error forwarding request: {e}")
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": "Service unavailable"},
            )

    def _get_service_from_path(self, path: str) -> str | None:
        """Get service URL from request path."""
        parts = path.strip("/").split("/")
        if len(parts) < 2:
            return None

        # Path format: /api/{service}/...
        if parts[0] == "api":
            service_name = parts[1]
            return self.service_map.get(service_name)

        return None

