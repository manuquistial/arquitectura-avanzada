"""
Machine-to-Machine Authentication
HMAC-based authentication with nonce deduplication
"""

import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Header, HTTPException, Request, status

logger = logging.getLogger(__name__)


class M2MAuthGenerator:
    """
    Generates M2M authentication headers
    
    Headers generated:
    - X-Service-Id: Service identifier
    - X-Nonce: Random nonce for replay protection
    - X-Timestamp: Unix timestamp
    - X-Signature: HMAC-SHA256(service_id + nonce + timestamp + body)
    """
    
    def __init__(self, service_id: str, secret_key: str):
        """
        Initialize M2M auth generator
        
        Args:
            service_id: Identifier of the calling service
            secret_key: Shared secret key for HMAC
        """
        self.service_id = service_id
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
    
    def generate_nonce(self, length: int = 32) -> str:
        """
        Generate cryptographically secure random nonce
        
        Args:
            length: Length of nonce in bytes
        
        Returns:
            Hex-encoded nonce
        """
        return secrets.token_hex(length)
    
    def generate_timestamp(self) -> str:
        """
        Generate current Unix timestamp
        
        Returns:
            Unix timestamp as string
        """
        return str(int(time.time()))
    
    def generate_signature(
        self,
        nonce: str,
        timestamp: str,
        body: bytes = b""
    ) -> str:
        """
        Generate HMAC-SHA256 signature
        
        Signature = HMAC-SHA256(secret, service_id + nonce + timestamp + body)
        
        Args:
            nonce: Nonce value
            timestamp: Unix timestamp
            body: Request body (optional)
        
        Returns:
            Hex-encoded HMAC signature
        """
        # Build message to sign
        message = f"{self.service_id}|{nonce}|{timestamp}".encode()
        
        # Add body if present
        if body:
            message += b"|" + body
        
        # Generate HMAC
        signature = hmac.new(
            self.secret_key,
            message,
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def generate_headers(self, body: bytes = b"") -> dict[str, str]:
        """
        Generate complete M2M auth headers
        
        Args:
            body: Request body
        
        Returns:
            Dictionary of headers
        """
        nonce = self.generate_nonce()
        timestamp = self.generate_timestamp()
        signature = self.generate_signature(nonce, timestamp, body)
        
        return {
            "X-Service-Id": self.service_id,
            "X-Nonce": nonce,
            "X-Timestamp": timestamp,
            "X-Signature": signature
        }


class M2MAuthValidator:
    """
    Validates M2M authentication headers
    
    Features:
    - HMAC signature verification
    - Timestamp validation (replay protection)
    - Nonce deduplication (requires Redis)
    """
    
    def __init__(
        self,
        secret_key: str,
        max_timestamp_age: int = 300,  # 5 minutes
        redis_client: Optional[any] = None,
        nonce_ttl: int = 600  # 10 minutes
    ):
        """
        Initialize M2M auth validator
        
        Args:
            secret_key: Shared secret key for HMAC
            max_timestamp_age: Maximum age of timestamp in seconds
            redis_client: Redis client for nonce deduplication (optional)
            nonce_ttl: TTL for nonce in Redis (seconds)
        """
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self.max_timestamp_age = max_timestamp_age
        self.redis_client = redis_client
        self.nonce_ttl = nonce_ttl
    
    def validate_timestamp(self, timestamp: str) -> None:
        """
        Validate timestamp is recent
        
        Args:
            timestamp: Unix timestamp as string
        
        Raises:
            HTTPException: If timestamp is invalid or too old
        """
        try:
            ts = int(timestamp)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid timestamp format"
            )
        
        current_time = int(time.time())
        age = current_time - ts
        
        # Check if timestamp is in the past
        if age < 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Timestamp is in the future"
            )
        
        # Check if timestamp is too old
        if age > self.max_timestamp_age:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Timestamp too old (max age: {self.max_timestamp_age}s)"
            )
    
    async def validate_nonce(self, service_id: str, nonce: str) -> None:
        """
        Validate nonce hasn't been used before (replay protection)
        
        Args:
            service_id: Service identifier
            nonce: Nonce value
        
        Raises:
            HTTPException: If nonce has been used before
        """
        if not self.redis_client:
            # Skip nonce validation if Redis not available
            logger.warning("⚠️  Redis not configured, skipping nonce validation")
            return
        
        try:
            # Build Redis key
            key = f"m2m:nonce:{service_id}:{nonce}"
            
            # Check if nonce exists
            exists = await self.redis_client.exists(key)
            
            if exists:
                logger.warning(f"🔴 Replay attack detected: nonce={nonce}, service={service_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Nonce already used (replay attack)"
                )
            
            # Store nonce with TTL
            await self.redis_client.setex(key, self.nonce_ttl, "1")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error validating nonce: {e}")
            # Don't fail on Redis errors (degraded mode)
            logger.warning("⚠️  Continuing without nonce validation (Redis error)")
    
    def validate_signature(
        self,
        service_id: str,
        nonce: str,
        timestamp: str,
        signature: str,
        body: bytes = b""
    ) -> None:
        """
        Validate HMAC signature
        
        Args:
            service_id: Service identifier
            nonce: Nonce value
            timestamp: Unix timestamp
            signature: HMAC signature to verify
            body: Request body
        
        Raises:
            HTTPException: If signature is invalid
        """
        # Build message to verify
        message = f"{service_id}|{nonce}|{timestamp}".encode()
        
        # Add body if present
        if body:
            message += b"|" + body
        
        # Calculate expected signature
        expected_signature = hmac.new(
            self.secret_key,
            message,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures (constant-time comparison)
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(f"🔴 Invalid signature from service: {service_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
    
    async def validate_headers(
        self,
        service_id: Optional[str],
        nonce: Optional[str],
        timestamp: Optional[str],
        signature: Optional[str],
        body: bytes = b""
    ) -> str:
        """
        Validate all M2M headers
        
        Args:
            service_id: X-Service-Id header
            nonce: X-Nonce header
            timestamp: X-Timestamp header
            signature: X-Signature header
            body: Request body
        
        Returns:
            service_id of authenticated service
        
        Raises:
            HTTPException: If any validation fails
        """
        # Check all headers are present
        if not all([service_id, nonce, timestamp, signature]):
            missing = []
            if not service_id: missing.append("X-Service-Id")
            if not nonce: missing.append("X-Nonce")
            if not timestamp: missing.append("X-Timestamp")
            if not signature: missing.append("X-Signature")
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing M2M headers: {', '.join(missing)}"
            )
        
        # Validate timestamp
        self.validate_timestamp(timestamp)
        
        # Validate nonce (replay protection)
        await self.validate_nonce(service_id, nonce)
        
        # Validate signature
        self.validate_signature(service_id, nonce, timestamp, signature, body)
        
        logger.info(f"✅ M2M auth validated: service={service_id}")
        
        return service_id


class M2MAuthMiddleware:
    """
    FastAPI dependency for M2M authentication
    
    Usage:
        from carpeta_common.m2m_auth import get_m2m_auth
        
        @app.post("/internal/endpoint")
        async def internal_endpoint(
            service_id: str = Depends(get_m2m_auth)
        ):
            return {"caller": service_id}
    """
    
    def __init__(self, validator: M2MAuthValidator):
        self.validator = validator
    
    async def __call__(
        self,
        request: Request,
        x_service_id: Optional[str] = Header(None),
        x_nonce: Optional[str] = Header(None),
        x_timestamp: Optional[str] = Header(None),
        x_signature: Optional[str] = Header(None)
    ) -> str:
        """
        Validate M2M headers and return service_id
        
        Args:
            request: FastAPI request
            x_service_id: X-Service-Id header
            x_nonce: X-Nonce header
            x_timestamp: X-Timestamp header
            x_signature: X-Signature header
        
        Returns:
            service_id of authenticated service
        """
        # Read body
        body = await request.body()
        
        # Validate headers
        service_id = await self.validator.validate_headers(
            service_id=x_service_id,
            nonce=x_nonce,
            timestamp=x_timestamp,
            signature=x_signature,
            body=body
        )
        
        return service_id


# Helper functions for easy integration

def create_m2m_generator(service_id: str, secret_key: str) -> M2MAuthGenerator:
    """
    Create M2M auth generator
    
    Args:
        service_id: Service identifier
        secret_key: Shared secret key
    
    Returns:
        M2MAuthGenerator instance
    """
    return M2MAuthGenerator(service_id, secret_key)


def create_m2m_validator(
    secret_key: str,
    redis_client: Optional[any] = None,
    max_timestamp_age: int = 300
) -> M2MAuthValidator:
    """
    Create M2M auth validator
    
    Args:
        secret_key: Shared secret key
        redis_client: Redis client (optional)
        max_timestamp_age: Max timestamp age in seconds
    
    Returns:
        M2MAuthValidator instance
    """
    return M2MAuthValidator(
        secret_key=secret_key,
        redis_client=redis_client,
        max_timestamp_age=max_timestamp_age
    )


# Global instances (initialized on first use)
_m2m_generator: Optional[M2MAuthGenerator] = None
_m2m_validator: Optional[M2MAuthValidator] = None
_m2m_middleware: Optional[M2MAuthMiddleware] = None


def get_m2m_generator() -> M2MAuthGenerator:
    """Get or create M2M generator"""
    global _m2m_generator
    
    if _m2m_generator is None:
        import os
        service_id = os.getenv("SERVICE_ID", "unknown-service")
        secret_key = os.getenv("M2M_SECRET_KEY", "mock_m2m_secret_key_123")
        _m2m_generator = M2MAuthGenerator(service_id, secret_key)
    
    return _m2m_generator


def get_m2m_validator() -> M2MAuthValidator:
    """Get or create M2M validator"""
    global _m2m_validator
    
    if _m2m_validator is None:
        import os
        secret_key = os.getenv("M2M_SECRET_KEY", "mock_m2m_secret_key_123")
        
        # Try to get Redis client
        try:
            from carpeta_common.redis_client import get_redis_client
            redis_client = get_redis_client()
        except Exception:
            redis_client = None
        
        _m2m_validator = M2MAuthValidator(
            secret_key=secret_key,
            redis_client=redis_client,
            max_timestamp_age=int(os.getenv("M2M_MAX_TIMESTAMP_AGE", "300"))
        )
    
    return _m2m_validator


def get_m2m_auth(
    request: Request,
    x_service_id: Optional[str] = Header(None),
    x_nonce: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None),
    x_signature: Optional[str] = Header(None)
) -> str:
    """
    FastAPI dependency for M2M authentication
    
    Usage:
        @app.post("/internal/endpoint")
        async def endpoint(service_id: str = Depends(get_m2m_auth)):
            return {"caller": service_id}
    
    Returns:
        service_id of authenticated service
    """
    global _m2m_middleware
    
    if _m2m_middleware is None:
        validator = get_m2m_validator()
        _m2m_middleware = M2MAuthMiddleware(validator)
    
    # Call middleware
    import asyncio
    return asyncio.create_task(
        _m2m_middleware(request, x_service_id, x_nonce, x_timestamp, x_signature)
    )

