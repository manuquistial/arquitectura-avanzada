"""Test MinTIC client response handling.

Tests:
- (a) Client processes plain text and 204 responses
- (b) No retry on 501 (invalid parameters)
- (c) Retry on 5xx errors
"""

import pytest
from pytest_httpx import HTTPXMock
import httpx

from app.client import MinTICClient
from app.config import Settings
from app.models import RegisterCitizenRequest, MinTICResponse


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        mintic_base_url="https://test-hub.example.com",
        request_timeout=5,
        hub_rate_limit_enabled=False  # Disable for tests
    )


@pytest.fixture
def client(settings):
    """Create MinTIC client."""
    return MinTICClient(settings)


# (a) Test plain text and 204 responses
@pytest.mark.asyncio
async def test_client_handles_plain_text_response(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that client handles plain text (non-JSON) responses."""
    # Mock plain text response
    httpx_mock.add_response(
        url="https://test-hub.example.com/apis/registerCitizen",
        method="POST",
        status_code=201,
        text="Ciudadano registrado exitosamente"
    )
    
    request = RegisterCitizenRequest(
        id=1234567890,
        name="Test User",
        address="Test Address",
        email="test@example.com",
        operatorId="test-op",
        operatorName="Test Operator"
    )
    
    result = await client.register_citizen(request)
    
    assert result is not None
    assert result.ok is True
    assert result.status == 201
    assert result.message == "Ciudadano registrado exitosamente"
    assert result.data is None  # No JSON data


@pytest.mark.asyncio
async def test_client_handles_204_no_content(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that client handles 204 No Content responses."""
    # Mock 204 response with empty body
    httpx_mock.add_response(
        url="https://test-hub.example.com/apis/unregisterCitizen",
        method="DELETE",
        status_code=204,
        text=""
    )
    
    from app.models import UnregisterCitizenRequest
    request = UnregisterCitizenRequest(id=1234567890)
    
    result = await client.unregister_citizen(request)
    
    assert result is not None
    assert result.ok is True
    assert result.status == 204
    assert "Sin contenido" in result.message or result.message == ""
    assert result.data is None


@pytest.mark.asyncio
async def test_client_handles_mixed_json_and_text(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that client handles JSON responses with message field."""
    # Mock JSON response
    httpx_mock.add_response(
        url="https://test-hub.example.com/apis/registerCitizen",
        method="POST",
        status_code=501,
        json={"message": "Error al crear Ciudadano con id: 1234567890 ya se encuentra registrado"}
    )
    
    request = RegisterCitizenRequest(
        id=1234567890,
        name="Test User",
        address="Test Address",
        email="test@example.com",
        operatorId="test-op",
        operatorName="Test Operator"
    )
    
    result = await client.register_citizen(request)
    
    assert result is not None
    assert result.ok is False
    assert result.status == 501
    assert "ya se encuentra registrado" in result.message


# (b) Test no retry on 501
@pytest.mark.asyncio
async def test_no_retry_on_501_invalid_parameters(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that client does NOT retry on 501 (invalid parameters)."""
    call_count = 0
    
    def response_callback(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            status_code=501,
            text="Error al crear Ciudadano - parámetros inválidos"
        )
    
    httpx_mock.add_callback(response_callback, url="https://test-hub.example.com/apis/registerCitizen")
    
    request = RegisterCitizenRequest(
        id=1234567890,
        name="Test User",
        address="Test Address",
        email="test@example.com",
        operatorId="test-op",
        operatorName="Test Operator"
    )
    
    result = await client.register_citizen(request)
    
    # Should only call once (no retries)
    assert call_count == 1
    assert result is not None
    assert result.status == 501
    assert result.ok is False


@pytest.mark.asyncio
async def test_no_retry_on_4xx_client_errors(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that client does NOT retry on 4xx errors."""
    call_count = 0
    
    def response_callback(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=400, text="Bad Request")
    
    httpx_mock.add_callback(response_callback, url="https://test-hub.example.com/apis/registerCitizen")
    
    request = RegisterCitizenRequest(
        id=1234567890,
        name="Test User",
        address="Test Address",
        email="test@example.com",
        operatorId="test-op",
        operatorName="Test Operator"
    )
    
    result = await client.register_citizen(request)
    
    # Should only call once (no retries for 4xx)
    assert call_count == 1
    assert result is not None
    assert result.status == 400


# (c) Test retry on 5xx
@pytest.mark.asyncio
async def test_retry_on_500_server_error(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that client DOES retry on 500 server errors."""
    call_count = 0
    
    def response_callback(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        
        # Fail first 2 times, succeed on 3rd
        if call_count < 3:
            return httpx.Response(status_code=500, text="Internal Server Error")
        else:
            return httpx.Response(status_code=201, text="Ciudadano registrado exitosamente")
    
    httpx_mock.add_callback(response_callback, url="https://test-hub.example.com/apis/registerCitizen")
    
    request = RegisterCitizenRequest(
        id=1234567890,
        name="Test User",
        address="Test Address",
        email="test@example.com",
        operatorId="test-op",
        operatorName="Test Operator"
    )
    
    result = await client.register_citizen(request)
    
    # Should retry 2 times (total 3 calls)
    assert call_count == 3
    assert result is not None
    assert result.status == 201
    assert result.ok is True


@pytest.mark.asyncio
async def test_retry_on_503_service_unavailable(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that client retries on 503 service unavailable."""
    call_count = 0
    
    def response_callback(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        
        # Fail first time, succeed on 2nd
        if call_count == 1:
            return httpx.Response(status_code=503, text="Service Unavailable")
        else:
            return httpx.Response(status_code=201, json={"message": "Success"})
    
    httpx_mock.add_callback(response_callback, url="https://test-hub.example.com/apis/registerCitizen")
    
    request = RegisterCitizenRequest(
        id=1234567890,
        name="Test User",
        address="Test Address",
        email="test@example.com",
        operatorId="test-op",
        operatorName="Test Operator"
    )
    
    result = await client.register_citizen(request)
    
    # Should retry once (total 2 calls)
    assert call_count == 2
    assert result.status == 201


@pytest.mark.asyncio
async def test_max_retries_exhausted_on_5xx(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that client stops after max retries on persistent 5xx."""
    call_count = 0
    
    def response_callback(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=500, text="Internal Server Error")
    
    httpx_mock.add_callback(response_callback, url="https://test-hub.example.com/apis/registerCitizen")
    
    request = RegisterCitizenRequest(
        id=1234567890,
        name="Test User",
        address="Test Address",
        email="test@example.com",
        operatorId="test-op",
        operatorName="Test Operator"
    )
    
    # Should raise exception after max retries
    with pytest.raises(Exception):
        await client.register_citizen(request)
    
    # Should try 3 times (initial + 2 retries)
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_on_timeout(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that client retries on timeout errors."""
    call_count = 0
    
    def response_callback(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            raise httpx.TimeoutException("Request timeout")
        else:
            return httpx.Response(status_code=201, text="Success")
    
    httpx_mock.add_callback(response_callback, url="https://test-hub.example.com/apis/registerCitizen")
    
    request = RegisterCitizenRequest(
        id=1234567890,
        name="Test User",
        address="Test Address",
        email="test@example.com",
        operatorId="test-op",
        operatorName="Test Operator"
    )
    
    result = await client.register_citizen(request)
    
    # Should retry once (total 2 calls)
    assert call_count == 2
    assert result.status == 201

