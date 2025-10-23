"""
HTTP Client with M2M Authentication
Automatic M2M header generation for inter-service communication
"""

import logging
from typing import Any, Optional

import httpx

from .m2m_auth import M2MAuthGenerator, get_m2m_generator

logger = logging.getLogger(__name__)


class M2MHttpClient:
    """
    HTTP client with automatic M2M authentication headers
    
    Usage:
        client = M2MHttpClient(service_id="gateway", secret_key="secret")
        response = await client.post(
            "http://citizen-service/api/citizens",
            json={"name": "John"}
        )
    """
    
    def __init__(
        self,
        service_id: str,
        secret_key: str,
        timeout: float = 30.0,
        base_url: Optional[str] = None
    ):
        """
        Initialize M2M HTTP client
        
        Args:
            service_id: Identifier of this service
            secret_key: Shared secret key for HMAC
            timeout: Request timeout in seconds
            base_url: Base URL for requests (optional)
        """
        self.auth_generator = M2MAuthGenerator(service_id, secret_key)
        self.timeout = timeout
        self.base_url = base_url
        
        # Create httpx client
        # Note: base_url is stored but not used in client creation
        # This prevents httpx from failing when base_url is None
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True
        )
    
    def _add_m2m_headers(self, headers: dict, body: bytes = b"") -> dict:
        """
        Add M2M authentication headers
        
        Args:
            headers: Existing headers
            body: Request body
        
        Returns:
            Headers with M2M auth added
        """
        m2m_headers = self.auth_generator.generate_headers(body)
        return {**headers, **m2m_headers}
    
    async def get(
        self,
        url: str,
        headers: Optional[dict] = None,
        **kwargs
    ) -> httpx.Response:
        """
        GET request with M2M auth
        
        Args:
            url: URL to request
            headers: Additional headers
            **kwargs: Additional httpx arguments
        
        Returns:
            httpx Response
        """
        headers = headers or {}
        headers = self._add_m2m_headers(headers)
        
        logger.debug(f"M2M GET {url}")
        return await self.client.get(url, headers=headers, **kwargs)
    
    async def post(
        self,
        url: str,
        json: Optional[dict] = None,
        data: Optional[Any] = None,
        headers: Optional[dict] = None,
        **kwargs
    ) -> httpx.Response:
        """
        POST request with M2M auth
        
        Args:
            url: URL to request
            json: JSON body
            data: Form data
            headers: Additional headers
            **kwargs: Additional httpx arguments
        
        Returns:
            httpx Response
        """
        import json as json_module
        
        headers = headers or {}
        
        # Serialize body for signature
        if json is not None:
            body = json_module.dumps(json, sort_keys=True).encode()
        elif data is not None:
            body = str(data).encode()
        else:
            body = b""
        
        # Add M2M headers
        headers = self._add_m2m_headers(headers, body)
        
        logger.debug(f"M2M POST {url}")
        return await self.client.post(url, json=json, data=data, headers=headers, **kwargs)
    
    async def put(
        self,
        url: str,
        json: Optional[dict] = None,
        data: Optional[Any] = None,
        headers: Optional[dict] = None,
        **kwargs
    ) -> httpx.Response:
        """
        PUT request with M2M auth
        """
        import json as json_module
        
        headers = headers or {}
        
        if json is not None:
            body = json_module.dumps(json, sort_keys=True).encode()
        elif data is not None:
            body = str(data).encode()
        else:
            body = b""
        
        headers = self._add_m2m_headers(headers, body)
        
        logger.debug(f"M2M PUT {url}")
        return await self.client.put(url, json=json, data=data, headers=headers, **kwargs)
    
    async def delete(
        self,
        url: str,
        headers: Optional[dict] = None,
        **kwargs
    ) -> httpx.Response:
        """
        DELETE request with M2M auth
        """
        headers = headers or {}
        headers = self._add_m2m_headers(headers)
        
        logger.debug(f"M2M DELETE {url}")
        return await self.client.delete(url, headers=headers, **kwargs)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager enter"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Convenience function

async def m2m_request(
    method: str,
    url: str,
    service_id: Optional[str] = None,
    secret_key: Optional[str] = None,
    **kwargs
) -> httpx.Response:
    """
    Make a single M2M-authenticated HTTP request
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: URL to request
        service_id: Service identifier (or from env)
        secret_key: Secret key (or from env)
        **kwargs: Additional arguments for httpx
    
    Returns:
        httpx Response
    
    Example:
        response = await m2m_request(
            "POST",
            "http://citizen-service/api/citizens",
            json={"name": "John"}
        )
    """
    import os
    
    service_id = service_id or os.getenv("SERVICE_ID", "unknown-service")
    secret_key = secret_key or os.getenv("M2M_SECRET_KEY", "default-secret-key")
    
    async with M2MHttpClient(service_id, secret_key) as client:
        if method.upper() == "GET":
            return await client.get(url, **kwargs)
        elif method.upper() == "POST":
            return await client.post(url, **kwargs)
        elif method.upper() == "PUT":
            return await client.put(url, **kwargs)
        elif method.upper() == "DELETE":
            return await client.delete(url, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

