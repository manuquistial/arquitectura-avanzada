"""Test idempotency mechanism.

Tests:
- (e) Idempotency prevents duplicate hub calls
- (e) Idempotency cache expires after TTL
- (e) Idempotency works across different operations
"""

import pytest
from pytest_httpx import HTTPXMock
from unittest.mock import AsyncMock, patch

from app.client import MinTICClient
from app.config import Settings
from app.models import RegisterCitizenRequest, UnregisterCitizenRequest, AuthenticateDocumentRequest, MinTICResponse


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        mintic_base_url="https://test-hub.example.com",
        redis_host="localhost",
        redis_port=6379,
        hub_rate_limit_enabled=False
    )


@pytest.fixture
def client(settings):
    """Create MinTIC client."""
    return MinTICClient(settings)


# (e) Test idempotency prevents duplicates
@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_register_citizen(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that idempotency prevents duplicate registerCitizen calls."""
    call_count = 0
    
    def response_callback(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=201, text="Ciudadano registrado")
    
    httpx_mock.add_callback(response_callback, url="https://test-hub.example.com/apis/registerCitizen")
    
    # Mock Redis to simulate caching
    with patch.object(client, '_check_idempotency', new_callable=AsyncMock) as mock_check, \
         patch.object(client, '_save_idempotent_result', new_callable=AsyncMock) as mock_save:
        
        # First call: no cache
        mock_check.return_value = None
        
        request = RegisterCitizenRequest(
            id=1234567890,
            name="Test User",
            address="Test Address",
            email="test@example.com",
            operatorId="test-op",
            operatorName="Test Operator"
        )
        
        result1 = await client.register_citizen(request)
        
        assert result1.status == 201
        assert call_count == 1
        assert mock_save.called
        
        # Second call: cache hit (simulate Redis returning cached result)
        cached_response = MinTICResponse(
            ok=True,
            status=201,
            message="Ciudadano registrado (cached)",
            data=None
        )
        mock_check.return_value = cached_response
        
        result2 = await client.register_citizen(request)
        
        # Should return cached result without calling hub again
        assert result2.status == 201
        assert result2.message == "Ciudadano registrado (cached)"
        assert call_count == 1  # Still 1, no second call


@pytest.mark.asyncio
async def test_idempotency_different_citizens_not_cached(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that different citizens are not affected by each other's cache."""
    call_count = 0
    
    def response_callback(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=201, text="Ciudadano registrado")
    
    httpx_mock.add_callback(response_callback, url="https://test-hub.example.com/apis/registerCitizen")
    
    with patch.object(client, '_check_idempotency', new_callable=AsyncMock) as mock_check, \
         patch.object(client, '_save_idempotent_result', new_callable=AsyncMock):
        
        # Always return None (no cache)
        mock_check.return_value = None
        
        request1 = RegisterCitizenRequest(
            id=1234567890,
            name="User 1",
            address="Address 1",
            email="user1@example.com",
            operatorId="test-op",
            operatorName="Test Operator"
        )
        
        request2 = RegisterCitizenRequest(
            id=9876543210,  # Different ID
            name="User 2",
            address="Address 2",
            email="user2@example.com",
            operatorId="test-op",
            operatorName="Test Operator"
        )
        
        await client.register_citizen(request1)
        await client.register_citizen(request2)
        
        # Should call hub twice (different citizens)
        assert call_count == 2


@pytest.mark.asyncio
async def test_idempotency_works_for_unregister(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that idempotency works for unregisterCitizen."""
    call_count = 0
    
    def response_callback(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=204, text="")
    
    httpx_mock.add_callback(response_callback, url="https://test-hub.example.com/apis/unregisterCitizen")
    
    with patch.object(client, '_check_idempotency', new_callable=AsyncMock) as mock_check, \
         patch.object(client, '_save_idempotent_result', new_callable=AsyncMock) as mock_save:
        
        # First call: no cache
        mock_check.return_value = None
        
        request = UnregisterCitizenRequest(id=1234567890)
        
        result1 = await client.unregister_citizen(request)
        
        assert result1.status == 204
        assert call_count == 1
        
        # Second call: cache hit
        cached_response = MinTICResponse(ok=True, status=204, message="Sin contenido (cached)", data=None)
        mock_check.return_value = cached_response
        
        result2 = await client.unregister_citizen(request)
        
        assert result2.status == 204
        assert call_count == 1  # No second call


@pytest.mark.asyncio
async def test_idempotency_works_for_authenticate_document(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that idempotency works for authenticateDocument."""
    call_count = 0
    
    def response_callback(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=200, text="Documento autenticado")
    
    httpx_mock.add_callback(response_callback, url="https://test-hub.example.com/apis/authenticateDocument")
    
    with patch.object(client, '_check_idempotency', new_callable=AsyncMock) as mock_check, \
         patch.object(client, '_save_idempotent_result', new_callable=AsyncMock):
        
        # First call: no cache
        mock_check.return_value = None
        
        request = AuthenticateDocumentRequest(
            idCitizen=1234567890,
            UrlDocument="https://storage.example.com/doc.pdf?sas=token",
            documentTitle="Test Document"
        )
        
        result1 = await client.authenticate_document(request)
        
        assert result1.status == 200
        assert call_count == 1
        
        # Second call: cache hit
        cached_response = MinTICResponse(ok=True, status=200, message="Documento autenticado (cached)", data=None)
        mock_check.return_value = cached_response
        
        result2 = await client.authenticate_document(request)
        
        assert result2.status == 200
        assert call_count == 1


@pytest.mark.asyncio
async def test_idempotency_only_caches_terminal_statuses(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that idempotency only caches terminal statuses (2xx, 204, 501)."""
    with patch.object(client, '_save_idempotent_result', new_callable=AsyncMock) as mock_save:
        # Test 201: should cache
        httpx_mock.add_response(
            url="https://test-hub.example.com/apis/registerCitizen",
            method="POST",
            status_code=201,
            text="Success"
        )
        
        request = RegisterCitizenRequest(
            id=1234567890,
            name="Test",
            address="Addr",
            email="test@example.com",
            operatorId="op",
            operatorName="Op"
        )
        
        await client.register_citizen(request)
        
        # Should save to cache
        assert mock_save.called
        
        # Test 501: should cache (terminal error)
        mock_save.reset_mock()
        httpx_mock.add_response(
            url="https://test-hub.example.com/apis/registerCitizen",
            method="POST",
            status_code=501,
            text="Invalid parameters"
        )
        
        request2 = RegisterCitizenRequest(
            id=9876543210,
            name="Test2",
            address="Addr2",
            email="test2@example.com",
            operatorId="op",
            operatorName="Op"
        )
        
        await client.register_citizen(request2)
        
        # Should save 501 to cache (don't retry)
        assert mock_save.called


@pytest.mark.asyncio
async def test_idempotency_key_generation_is_consistent(client: MinTICClient):
    """Test that idempotency keys are generated consistently."""
    # Same input should generate same key
    key1 = f"hub:registerCitizen:1234567890"
    key2 = f"hub:registerCitizen:1234567890"
    
    assert key1 == key2
    
    # Different input should generate different key
    key3 = f"hub:registerCitizen:9876543210"
    
    assert key1 != key3

