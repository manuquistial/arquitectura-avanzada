"""
MinTIC Hub Client with Circuit Breaker Protection
Prevents cascading failures when Hub is down/slow
"""

import logging
from typing import Optional, Dict, Any

import httpx
from carpeta_common.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    get_circuit_breaker
)

logger = logging.getLogger(__name__)


class MinTICClientWithCircuitBreaker:
    """
    MinTIC Hub client with circuit breaker protection.
    
    Features:
    - Circuit breaker for Hub calls
    - Fallback strategies when Hub is down
    - Timeout handling
    - Retry logic
    - Metrics for monitoring
    
    Usage:
        client = MinTICClientWithCircuitBreaker(hub_url)
        
        try:
            result = client.authenticate_document(doc_id, nonce)
        except CircuitBreakerError:
            # Hub is down, use cached result or fail gracefully
            pass
    """
    
    def __init__(
        self,
        hub_url: str,
        timeout: float = 10.0,
        enable_circuit_breaker: bool = True
    ):
        """
        Initialize MinTIC client.
        
        Args:
            hub_url: MinTIC Hub base URL
            timeout: Request timeout in seconds
            enable_circuit_breaker: Enable circuit breaker protection
        """
        self.hub_url = hub_url.rstrip('/')
        self.timeout = timeout
        self.enable_circuit_breaker = enable_circuit_breaker
        
        # HTTP client
        self.http_client = httpx.Client(timeout=timeout)
        
        # Circuit breaker configuration
        if enable_circuit_breaker:
            config = CircuitBreakerConfig(
                failure_threshold=5,            # Open after 5 failures
                success_threshold=2,            # Close after 2 successes
                timeout=60.0,                   # Try half-open after 60s
                expected_exception=Exception,   # Catch all exceptions
                sliding_window_size=10,
                failure_rate_threshold=0.5      # Open if 50% failure rate
            )
            
            self.circuit_breaker = get_circuit_breaker(
                "mintic_hub",
                config=config,
                fallback=self._fallback_response
            )
        else:
            self.circuit_breaker = None
        
        logger.info(f"MinTIC client initialized (hub: {hub_url}, circuit_breaker: {enable_circuit_breaker})")
    
    def _fallback_response(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Fallback response when circuit is open.
        
        Returns cached/default response to allow graceful degradation.
        """
        logger.warning("MinTIC Hub circuit breaker OPEN, using fallback response")
        
        return {
            "status": "unavailable",
            "message": "MinTIC Hub is temporarily unavailable",
            "fallback": True,
            "timestamp": None
        }
    
    def authenticate_document(
        self,
        document_id: str,
        nonce: str,
        timestamp: str
    ) -> Dict[str, Any]:
        """
        Authenticate document with MinTIC Hub.
        
        Protected by circuit breaker.
        
        Args:
            document_id: Document ID
            nonce: Unique nonce
            timestamp: Request timestamp
        
        Returns:
            Hub authentication response
        
        Raises:
            CircuitBreakerError: If circuit is open
            httpx.HTTPError: If request fails
        """
        def _call():
            logger.info(f"Authenticating document with Hub: {document_id}")
            
            response = self.http_client.post(
                f"{self.hub_url}/api/v1/authenticate",
                json={
                    "document_id": document_id,
                    "nonce": nonce,
                    "timestamp": timestamp
                },
                headers={
                    "X-Service-Id": "carpeta-ciudadana",
                    "Content-Type": "application/json"
                }
            )
            
            response.raise_for_status()
            return response.json()
        
        if self.circuit_breaker:
            return self.circuit_breaker.call(_call)
        else:
            return _call()
    
    def sign_document(
        self,
        document_id: str,
        user_id: str,
        signature_type: str
    ) -> Dict[str, Any]:
        """
        Request document signature from Hub.
        
        Protected by circuit breaker.
        
        Args:
            document_id: Document ID
            user_id: User ID
            signature_type: Signature type
        
        Returns:
            Signature response
        """
        def _call():
            logger.info(f"Signing document via Hub: {document_id}")
            
            response = self.http_client.post(
                f"{self.hub_url}/api/v1/sign",
                json={
                    "document_id": document_id,
                    "user_id": user_id,
                    "signature_type": signature_type
                }
            )
            
            response.raise_for_status()
            return response.json()
        
        if self.circuit_breaker:
            return self.circuit_breaker.call(_call)
        else:
            return _call()
    
    def verify_signature(
        self,
        document_id: str,
        signature: str
    ) -> Dict[str, Any]:
        """
        Verify document signature with Hub.
        
        Protected by circuit breaker.
        
        Args:
            document_id: Document ID
            signature: Signature to verify
        
        Returns:
            Verification response
        """
        def _call():
            logger.info(f"Verifying signature via Hub: {document_id}")
            
            response = self.http_client.post(
                f"{self.hub_url}/api/v1/verify",
                json={
                    "document_id": document_id,
                    "signature": signature
                }
            )
            
            response.raise_for_status()
            return response.json()
        
        if self.circuit_breaker:
            return self.circuit_breaker.call(_call)
        else:
            return _call()
    
    def health_check(self) -> bool:
        """
        Check MinTIC Hub health.
        
        Not protected by circuit breaker (used for monitoring).
        
        Returns:
            True if Hub is healthy
        """
        try:
            response = self.http_client.get(f"{self.hub_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Hub health check failed: {e}")
            return False
    
    def get_circuit_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get circuit breaker statistics.
        
        Returns:
            Circuit breaker stats or None if disabled
        """
        if self.circuit_breaker:
            return self.circuit_breaker.get_stats()
        return None
    
    def reset_circuit(self):
        """Manually reset circuit breaker to CLOSED state."""
        if self.circuit_breaker:
            self.circuit_breaker.reset()
            logger.info("MinTIC Hub circuit breaker reset to CLOSED")
    
    def close(self):
        """Close HTTP client."""
        self.http_client.close()


# Example FastAPI endpoint with circuit breaker
"""
from fastapi import APIRouter, HTTPException
from app.client_with_circuit_breaker import MinTICClientWithCircuitBreaker
from carpeta_common.circuit_breaker import CircuitBreakerError

router = APIRouter()
mintic_client = MinTICClientWithCircuitBreaker(hub_url="https://hub.mintic.gov.co")

@router.post("/documents/{document_id}/authenticate")
async def authenticate_document(document_id: str, nonce: str, timestamp: str):
    try:
        result = mintic_client.authenticate_document(document_id, nonce, timestamp)
        
        if result.get("fallback"):
            # Circuit breaker triggered, Hub is down
            return {
                "status": "pending",
                "message": "Authentication pending - Hub temporarily unavailable"
            }
        
        return result
    
    except CircuitBreakerError:
        raise HTTPException(
            status_code=503,
            detail="MinTIC Hub is temporarily unavailable"
        )
    
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/circuit-breaker/stats")
async def circuit_breaker_stats():
    stats = mintic_client.get_circuit_stats()
    return stats or {"message": "Circuit breaker not enabled"}

@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker():
    mintic_client.reset_circuit()
    return {"message": "Circuit breaker reset to CLOSED"}
"""

