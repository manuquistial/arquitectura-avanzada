"""Service proxy for routing requests."""

import logging
from typing import Any
import json

import httpx
from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.config import Settings
from app.sanitizer import sanitize_log_data, truncate_for_logging, sanitize_hub_payload

logger = logging.getLogger(__name__)


class ProxyService:
    """Proxy service for routing requests to backend services."""

    def __init__(self, settings: Settings) -> None:
        """Initialize proxy."""
        self.settings = settings
        self.service_map = {
            "citizens": settings.citizen_service_url,  # Plural (match API path)
            "documents": settings.ingestion_service_url,  # documents endpoint
            "metadata": settings.metadata_service_url,
            "signature": settings.signature_service_url,
            "transfer": settings.transfer_service_url,
            "sharing": settings.sharing_service_url,
            "notification": settings.notification_service_url,
            "mintic": settings.mintic_client_url,
        }

    async def forward_request(self, request: Request, path: str) -> JSONResponse:
        """Forward request to appropriate backend service.
        
        - Sanitizes data before forwarding to external services (MinTIC Hub)
        - Logs truncated messages (max 200 chars, PII redacted)
        - Validates and trims payloads
        """
        # Determine target service from path
        service = self._get_service_from_path(path)
        if not service:
            logger.warning(f"Service not found for path: {truncate_for_logging(path)}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Service not found"},
            )

        target_url = f"{service}/{path}"
        
        # Truncated logging (max 200 chars, no PII)
        log_msg = f"Proxying {request.method} to {truncate_for_logging(target_url)}"
        logger.info(log_msg)

        try:
            # Forward request
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get request body if present
                body = None
                sanitized_body = None
                
                if request.method in ["POST", "PUT", "PATCH"]:
                    body = await request.body()
                    
                    # Parse and sanitize if sending to hub/mintic
                    if "mintic" in path or "hub" in path:
                        try:
                            json_body = json.loads(body)
                            sanitized_body = sanitize_hub_payload(json_body)
                            body = json.dumps(sanitized_body).encode()
                            logger.info(f"Sanitized payload for hub: {truncate_for_logging(str(sanitized_body))}")
                        except json.JSONDecodeError:
                            logger.warning("Could not parse body as JSON for sanitization")

                # Forward with sanitized data
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=self._sanitize_headers(dict(request.headers)),
                    params=dict(request.query_params),
                    content=body,
                )
                
                # Log response (truncated)
                response_preview = truncate_for_logging(response.text)
                logger.info(
                    f"Response from {service}: status={response.status_code}, "
                    f"body={response_preview}"
                )

                return JSONResponse(
                    status_code=response.status_code,
                    content=response.json() if response.content else {},
                    headers={"X-Gateway-Proxied": "true"},
                )

        except httpx.TimeoutException as e:
            logger.error(f"Timeout forwarding to {service}: {truncate_for_logging(str(e))}")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={"detail": "Service timeout"},
            )
        except httpx.HTTPError as e:
            logger.error(f"Error forwarding to {service}: {truncate_for_logging(str(e))}")
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"detail": "Service unavailable"},
            )
    
    def _sanitize_headers(self, headers: dict) -> dict:
        """Sanitize headers before forwarding (remove sensitive data)."""
        # Remove headers that shouldn't be forwarded
        skip_headers = {
            'host', 'connection', 'content-length', 
            'authorization',  # Will be re-added by target service if needed
        }
        
        return {
            k: v for k, v in headers.items() 
            if k.lower() not in skip_headers
        }

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

