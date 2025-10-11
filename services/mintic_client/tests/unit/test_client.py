"""Unit tests for MinTIC client."""

import pytest
from httpx import AsyncClient, Response
from pytest_httpx import HTTPXMock

from app.client import MinTICClient
from app.config import Settings
from app.models import (
    AuthenticateDocumentRequest,
    RegisterCitizenRequest,
    RegisterOperatorRequest,
    UnregisterCitizenRequest,
)


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        mintic_base_url="https://test.mintic.gov.co",
        mintic_operator_id="test-operator",
        mintic_operator_name="Test Operator",
        mtls_cert_path="/tmp/test.crt",
        mtls_key_path="/tmp/test.key",
        ca_bundle_path="/tmp/ca.crt",
    )


@pytest.fixture
def mintic_client(settings):
    """Create MinTIC client."""
    return MinTICClient(settings)


@pytest.mark.asyncio
async def test_register_citizen_success(mintic_client, httpx_mock: HTTPXMock):
    """Test successful citizen registration."""
    # Mock response
    httpx_mock.add_response(
        method="POST",
        url="https://test.mintic.gov.co/apis/registerCitizen",
        status_code=201,
        text="Ciudadano con id: 123 se ha relacionado con OPerador abc. Creado exitosamente",
    )

    request = RegisterCitizenRequest(
        id=123,
        name="Test User",
        address="Test Address",
        email="test@example.com",
        operatorId="test-operator",
        operatorName="Test Operator",
    )

    result = await mintic_client.register_citizen(request)

    assert result.success is True
    assert result.status_code == 201


@pytest.mark.asyncio
async def test_register_citizen_already_exists(mintic_client, httpx_mock: HTTPXMock):
    """Test citizen already registered."""
    httpx_mock.add_response(
        method="POST",
        url="https://test.mintic.gov.co/apis/registerCitizen",
        status_code=501,
        text="Error al crear Ciudadano con id: 123 ya se encuentra registrado",
    )

    request = RegisterCitizenRequest(
        id=123,
        name="Test User",
        address="Test Address",
        email="test@example.com",
        operatorId="test-operator",
        operatorName="Test Operator",
    )

    result = await mintic_client.register_citizen(request)

    assert result.success is False
    assert result.status_code == 501


@pytest.mark.asyncio
async def test_validate_citizen(mintic_client, httpx_mock: HTTPXMock):
    """Test citizen validation."""
    httpx_mock.add_response(
        method="GET",
        url="https://test.mintic.gov.co/apis/validateCitizen/123",
        status_code=200,
        text="OK",
    )

    result = await mintic_client.validate_citizen(123)

    assert result.success is True
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_authenticate_document(mintic_client, httpx_mock: HTTPXMock):
    """Test document authentication."""
    httpx_mock.add_response(
        method="PUT",
        url="https://test.mintic.gov.co/apis/authenticateDocument",
        status_code=200,
        text="El documento: Test Doc del ciudadano 123 ha sido autenticado exitosamente",
    )

    request = AuthenticateDocumentRequest(
        idCitizen=123,
        UrlDocument="https://s3.amazonaws.com/bucket/doc",
        documentTitle="Test Doc",
    )

    result = await mintic_client.authenticate_document(request)

    assert result.success is True
    assert result.status_code == 200

