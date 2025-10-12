"""
Tests for M2M Authentication
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from carpeta_common.m2m_auth import (
    M2MAuthGenerator,
    M2MAuthValidator,
)


@pytest.fixture
def secret_key():
    return "test-secret-key-12345"


@pytest.fixture
def service_id():
    return "test-service"


@pytest.fixture
def generator(service_id, secret_key):
    return M2MAuthGenerator(service_id, secret_key)


@pytest.fixture
def validator(secret_key):
    return M2MAuthValidator(secret_key, max_timestamp_age=300)


class TestM2MAuthGenerator:
    """Test M2M auth generator"""
    
    def test_generate_nonce(self, generator):
        """Test nonce generation"""
        nonce = generator.generate_nonce()
        
        assert nonce is not None
        assert len(nonce) == 64  # 32 bytes = 64 hex chars
        assert isinstance(nonce, str)
        
        # Nonces should be unique
        nonce2 = generator.generate_nonce()
        assert nonce != nonce2
    
    def test_generate_timestamp(self, generator):
        """Test timestamp generation"""
        timestamp = generator.generate_timestamp()
        
        assert timestamp is not None
        assert timestamp.isdigit()
        
        # Should be close to current time
        current_time = int(time.time())
        ts = int(timestamp)
        assert abs(current_time - ts) < 2  # Within 2 seconds
    
    def test_generate_signature(self, generator):
        """Test signature generation"""
        nonce = "test-nonce-123"
        timestamp = "1234567890"
        body = b'{"test": "data"}'
        
        signature = generator.generate_signature(nonce, timestamp, body)
        
        assert signature is not None
        assert len(signature) == 64  # SHA256 = 64 hex chars
        assert isinstance(signature, str)
        
        # Same inputs should produce same signature
        signature2 = generator.generate_signature(nonce, timestamp, body)
        assert signature == signature2
        
        # Different inputs should produce different signature
        signature3 = generator.generate_signature("different-nonce", timestamp, body)
        assert signature != signature3
    
    def test_generate_headers(self, generator, service_id):
        """Test complete header generation"""
        headers = generator.generate_headers(b'{"test": "data"}')
        
        assert "X-Service-Id" in headers
        assert "X-Nonce" in headers
        assert "X-Timestamp" in headers
        assert "X-Signature" in headers
        
        assert headers["X-Service-Id"] == service_id
        assert len(headers["X-Nonce"]) == 64
        assert headers["X-Timestamp"].isdigit()
        assert len(headers["X-Signature"]) == 64


class TestM2MAuthValidator:
    """Test M2M auth validator"""
    
    def test_validate_timestamp_valid(self, validator):
        """Test valid timestamp"""
        current_timestamp = str(int(time.time()))
        
        # Should not raise
        validator.validate_timestamp(current_timestamp)
    
    def test_validate_timestamp_too_old(self, validator):
        """Test timestamp too old"""
        old_timestamp = str(int(time.time()) - 400)  # 400 seconds ago
        
        with pytest.raises(Exception) as exc_info:
            validator.validate_timestamp(old_timestamp)
        
        assert "too old" in str(exc_info.value.detail).lower()
    
    def test_validate_timestamp_future(self, validator):
        """Test timestamp in the future"""
        future_timestamp = str(int(time.time()) + 100)
        
        with pytest.raises(Exception) as exc_info:
            validator.validate_timestamp(future_timestamp)
        
        assert "future" in str(exc_info.value.detail).lower()
    
    def test_validate_timestamp_invalid_format(self, validator):
        """Test invalid timestamp format"""
        invalid_timestamp = "not-a-number"
        
        with pytest.raises(Exception) as exc_info:
            validator.validate_timestamp(invalid_timestamp)
        
        assert "invalid" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_validate_nonce_without_redis(self, validator):
        """Test nonce validation without Redis (should skip)"""
        # Should not raise (Redis not configured)
        await validator.validate_nonce("test-service", "test-nonce")
    
    @pytest.mark.asyncio
    async def test_validate_nonce_with_redis(self, validator):
        """Test nonce validation with Redis"""
        # Mock Redis client
        redis_mock = AsyncMock()
        redis_mock.exists.return_value = False
        redis_mock.setex.return_value = True
        
        validator.redis_client = redis_mock
        
        # Should not raise (nonce doesn't exist)
        await validator.validate_nonce("test-service", "new-nonce")
        
        # Verify Redis calls
        redis_mock.exists.assert_called_once()
        redis_mock.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_nonce_replay_attack(self, validator):
        """Test nonce already used (replay attack)"""
        # Mock Redis client
        redis_mock = AsyncMock()
        redis_mock.exists.return_value = True  # Nonce already exists
        
        validator.redis_client = redis_mock
        
        # Should raise HTTPException
        with pytest.raises(Exception) as exc_info:
            await validator.validate_nonce("test-service", "used-nonce")
        
        assert "replay" in str(exc_info.value.detail).lower()
    
    def test_validate_signature_valid(self, validator, service_id, secret_key):
        """Test valid signature"""
        # Generate valid signature
        generator = M2MAuthGenerator(service_id, secret_key)
        nonce = "test-nonce"
        timestamp = str(int(time.time()))
        body = b'{"test": "data"}'
        
        signature = generator.generate_signature(nonce, timestamp, body)
        
        # Should not raise
        validator.validate_signature(service_id, nonce, timestamp, signature, body)
    
    def test_validate_signature_invalid(self, validator, service_id):
        """Test invalid signature"""
        nonce = "test-nonce"
        timestamp = str(int(time.time()))
        body = b'{"test": "data"}'
        invalid_signature = "invalid-signature-123"
        
        # Should raise HTTPException
        with pytest.raises(Exception) as exc_info:
            validator.validate_signature(service_id, nonce, timestamp, invalid_signature, body)
        
        assert "invalid signature" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_validate_headers_complete_valid(self, validator, service_id, secret_key):
        """Test complete header validation (valid)"""
        # Generate valid headers
        generator = M2MAuthGenerator(service_id, secret_key)
        nonce = generator.generate_nonce()
        timestamp = generator.generate_timestamp()
        body = b'{"test": "data"}'
        signature = generator.generate_signature(nonce, timestamp, body)
        
        # Should return service_id
        result = await validator.validate_headers(
            service_id=service_id,
            nonce=nonce,
            timestamp=timestamp,
            signature=signature,
            body=body
        )
        
        assert result == service_id
    
    @pytest.mark.asyncio
    async def test_validate_headers_missing(self, validator):
        """Test missing headers"""
        # Should raise HTTPException
        with pytest.raises(Exception) as exc_info:
            await validator.validate_headers(
                service_id=None,
                nonce=None,
                timestamp=None,
                signature=None
            )
        
        assert "missing" in str(exc_info.value.detail).lower()

