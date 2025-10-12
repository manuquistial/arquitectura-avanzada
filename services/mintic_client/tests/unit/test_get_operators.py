"""Test getOperators normalization and filtering.

Tests:
- (d) getOperators tolerates entries without transferAPIURL
- (d) getOperators filters http:// in production
- (d) getOperators allows http:// in development with warning
"""

import pytest
from pytest_httpx import HTTPXMock

from app.client import MinTICClient
from app.config import Settings


# (d) Test getOperators normalization and filtering
@pytest.mark.asyncio
async def test_get_operators_tolerates_missing_transfer_url(httpx_mock: HTTPXMock):
    """Test that getOperators tolerates operators without transferAPIURL."""
    settings = Settings(
        mintic_base_url="https://test-hub.example.com",
        environment="production",
        allow_insecure_operator_urls=False,
        hub_rate_limit_enabled=False
    )
    client = MinTICClient(settings)
    
    # Mock response with mixed operators (some without transferAPIURL)
    httpx_mock.add_response(
        url="https://test-hub.example.com/apis/getOperators",
        method="GET",
        json=[
            {
                "operatorName": "Operator A",
                "transferAPIURL": "https://operator-a.example.com/transfer"
            },
            {
                "operatorName": "Operator B"
                # Missing transferAPIURL
            },
            {
                "operatorName": "Operator C",
                "transferAPIURL": ""  # Empty string
            },
            {
                "operatorName": "Operator D",
                "transferAPIURL": "https://operator-d.example.com/transfer"
            }
        ]
    )
    
    operators = await client.get_operators()
    
    # Should return only operators with valid transferAPIURL
    assert len(operators) == 2
    assert operators[0].operatorName == "Operator A"
    assert operators[1].operatorName == "Operator D"


@pytest.mark.asyncio
async def test_get_operators_filters_http_in_production(httpx_mock: HTTPXMock):
    """Test that getOperators filters http:// URLs in production."""
    settings = Settings(
        mintic_base_url="https://test-hub.example.com",
        environment="production",
        allow_insecure_operator_urls=False,  # Production: no http://
        hub_rate_limit_enabled=False
    )
    client = MinTICClient(settings)
    
    # Mock response with http:// URLs
    httpx_mock.add_response(
        url="https://test-hub.example.com/apis/getOperators",
        method="GET",
        json=[
            {
                "operatorName": "Secure Operator",
                "transferAPIURL": "https://secure-operator.example.com/transfer"
            },
            {
                "operatorName": "Insecure Operator",
                "transferAPIURL": "http://insecure-operator.example.com/transfer"  # http://
            },
            {
                "operatorName": "Another Secure",
                "transferAPIURL": "https://another-secure.example.com/transfer"
            }
        ]
    )
    
    operators = await client.get_operators()
    
    # Should filter out http:// in production
    assert len(operators) == 2
    assert all(op.transferAPIURL.startswith("https://") for op in operators)
    assert "Insecure Operator" not in [op.operatorName for op in operators]


@pytest.mark.asyncio
async def test_get_operators_allows_http_in_development(httpx_mock: HTTPXMock, caplog):
    """Test that getOperators allows http:// in development with warning."""
    settings = Settings(
        mintic_base_url="https://test-hub.example.com",
        environment="development",
        allow_insecure_operator_urls=True,  # Development: allow http://
        hub_rate_limit_enabled=False
    )
    client = MinTICClient(settings)
    
    # Mock response with http:// URLs
    httpx_mock.add_response(
        url="https://test-hub.example.com/apis/getOperators",
        method="GET",
        json=[
            {
                "operatorName": "Local Operator",
                "transferAPIURL": "http://localhost:8004/transfer"
            },
            {
                "operatorName": "Secure Operator",
                "transferAPIURL": "https://secure.example.com/transfer"
            }
        ]
    )
    
    operators = await client.get_operators()
    
    # Should include http:// in development
    assert len(operators) == 2
    assert any(op.transferAPIURL.startswith("http://") for op in operators)
    
    # Should log warning for http:// URLs
    assert any("http://" in record.message.lower() for record in caplog.records)


@pytest.mark.asyncio
async def test_get_operators_normalizes_whitespace(httpx_mock: HTTPXMock):
    """Test that getOperators normalizes whitespace in operator data."""
    settings = Settings(
        mintic_base_url="https://test-hub.example.com",
        environment="production",
        allow_insecure_operator_urls=False,
        hub_rate_limit_enabled=False
    )
    client = MinTICClient(settings)
    
    # Mock response with extra whitespace
    httpx_mock.add_response(
        url="https://test-hub.example.com/apis/getOperators",
        method="GET",
        json=[
            {
                "operatorName": "  Operator With Spaces  ",
                "transferAPIURL": "  https://operator.example.com/transfer  "
            }
        ]
    )
    
    operators = await client.get_operators()
    
    # Should trim whitespace
    assert len(operators) == 1
    assert operators[0].operatorName == "Operator With Spaces"
    assert operators[0].transferAPIURL == "https://operator.example.com/transfer"


@pytest.mark.asyncio
async def test_get_operators_handles_empty_list(httpx_mock: HTTPXMock):
    """Test that getOperators handles empty operator list."""
    settings = Settings(
        mintic_base_url="https://test-hub.example.com",
        hub_rate_limit_enabled=False
    )
    client = MinTICClient(settings)
    
    # Mock empty response
    httpx_mock.add_response(
        url="https://test-hub.example.com/apis/getOperators",
        method="GET",
        json=[]
    )
    
    operators = await client.get_operators()
    
    assert operators == []


@pytest.mark.asyncio
async def test_get_operators_handles_malformed_entries(httpx_mock: HTTPXMock):
    """Test that getOperators handles malformed operator entries gracefully."""
    settings = Settings(
        mintic_base_url="https://test-hub.example.com",
        environment="production",
        hub_rate_limit_enabled=False
    )
    client = MinTICClient(settings)
    
    # Mock response with malformed entries
    httpx_mock.add_response(
        url="https://test-hub.example.com/apis/getOperators",
        method="GET",
        json=[
            {
                "operatorName": "Good Operator",
                "transferAPIURL": "https://good.example.com/transfer"
            },
            {
                # Missing operatorName
                "transferAPIURL": "https://no-name.example.com/transfer"
            },
            {
                "operatorName": "",  # Empty name
                "transferAPIURL": "https://empty-name.example.com/transfer"
            },
            None,  # Null entry
            {
                "operatorName": "Another Good",
                "transferAPIURL": "https://another-good.example.com/transfer"
            }
        ]
    )
    
    operators = await client.get_operators()
    
    # Should return only valid operators
    assert len(operators) == 2
    assert operators[0].operatorName == "Good Operator"
    assert operators[1].operatorName == "Another Good"

