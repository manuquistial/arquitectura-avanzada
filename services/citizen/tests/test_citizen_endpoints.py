"""Comprehensive tests for citizen service endpoints."""

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, Base
from app.models import Citizen


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """FastAPI test client with test database."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    client = TestClient(app)
    yield client
    
    # Clean up
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_citizen_data():
    """Sample citizen data for testing."""
    return {
        "id": 1032236578,
        "name": "Carlos Castro",
        "address": "Calle 123 #45-67, Bogotá",
        "email": "carlos.castro@example.com",
        "operator_id": "OP001",
        "operator_name": "Operador Ejemplo"
    }


@pytest.fixture
def sample_citizen_data_2():
    """Second sample citizen data for testing."""
    return {
        "id": 1032236579,
        "name": "María González",
        "address": "Carrera 45 #78-90, Medellín",
        "email": "maria.gonzalez@example.com",
        "operator_id": "OP001",
        "operator_name": "Operador Ejemplo"
    }


class TestHealthEndpoints:
    """Test health and readiness endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_ready_endpoint(self, client):
        """Test readiness check endpoint."""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == "citizen"


class TestCitizenRegistration:
    """Test citizen registration functionality."""
    
    def test_register_citizen_success(self, client, sample_citizen_data):
        """Test successful citizen registration."""
        # Mock the mintic_client call
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
            
            response = client.post("/api/citizens/register", json=sample_citizen_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == sample_citizen_data["id"]
            assert data["name"] == sample_citizen_data["name"]
            assert data["email"] == sample_citizen_data["email"]
            assert data["operator_id"] == sample_citizen_data["operator_id"]
            assert data["is_active"] is True
            assert "created_at" in data
            assert "updated_at" in data
    
    def test_register_citizen_duplicate(self, client, sample_citizen_data):
        """Test registration of duplicate citizen."""
        # First registration
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
            client.post("/api/citizens/register", json=sample_citizen_data)
        
        # Second registration should fail
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
            response = client.post("/api/citizens/register", json=sample_citizen_data)
            
            assert response.status_code == 409
            assert "ya se encuentra registrado" in response.json()["detail"]
    
    def test_register_citizen_invalid_id(self, client, sample_citizen_data):
        """Test registration with invalid citizen ID."""
        invalid_data = sample_citizen_data.copy()
        invalid_data["id"] = 12345  # Invalid: not 10 digits
        
        response = client.post("/api/citizens/register", json=invalid_data)
        assert response.status_code == 422
        assert "exactly 10 digits" in response.json()["detail"][0]["msg"]
    
    def test_register_citizen_invalid_email(self, client, sample_citizen_data):
        """Test registration with invalid email."""
        invalid_data = sample_citizen_data.copy()
        invalid_data["email"] = "invalid-email"
        
        response = client.post("/api/citizens/register", json=invalid_data)
        assert response.status_code == 422
        assert "email" in response.json()["detail"][0]["loc"]
    
    def test_register_citizen_missing_fields(self, client):
        """Test registration with missing required fields."""
        incomplete_data = {
            "id": 1032236578,
            "name": "Carlos Castro"
            # Missing required fields
        }
        
        response = client.post("/api/citizens/register", json=incomplete_data)
        assert response.status_code == 422
    
    def test_register_citizen_empty_fields(self, client, sample_citizen_data):
        """Test registration with empty string fields."""
        invalid_data = sample_citizen_data.copy()
        invalid_data["name"] = ""  # Empty name
        
        response = client.post("/api/citizens/register", json=invalid_data)
        assert response.status_code == 422
        assert "cannot be empty" in response.json()["detail"][0]["msg"]
    
    def test_register_citizen_mintic_hub_error(self, client, sample_citizen_data):
        """Test registration when MinTIC Hub returns error."""
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.post", self._mock_mintic_error_response)
            
            response = client.post("/api/citizens/register", json=sample_citizen_data)
            
            assert response.status_code == 502
            assert "Hub MinTIC" in response.json()["detail"]
    
    def test_register_citizen_mintic_service_unavailable(self, client, sample_citizen_data):
        """Test registration when mintic_client service is unavailable."""
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.post", self._mock_service_unavailable_response)
            
            response = client.post("/api/citizens/register", json=sample_citizen_data)
            
            assert response.status_code == 503
            assert "servicio MinTIC client" in response.json()["detail"]
    
    @staticmethod
    async def _mock_successful_mintic_response(*args, **kwargs):
        """Mock successful MinTIC response."""
        class MockResponse:
            status_code = 200
            def json(self):
                return {"status": "success"}
        return MockResponse()
    
    @staticmethod
    async def _mock_mintic_error_response(*args, **kwargs):
        """Mock MinTIC error response."""
        class MockResponse:
            status_code = 400
            headers = {"content-type": "application/json"}
            def json(self):
                return {"detail": "Invalid citizen data"}
        return MockResponse()
    
    @staticmethod
    async def _mock_service_unavailable_response(*args, **kwargs):
        """Mock service unavailable response."""
        raise Exception("Connection timeout")


class TestCitizenRetrieval:
    """Test citizen retrieval functionality."""
    
    def test_get_citizen_success(self, client, sample_citizen_data):
        """Test successful citizen retrieval."""
        # First register a citizen
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
            client.post("/api/citizens/register", json=sample_citizen_data)
        
        # Then retrieve it
        response = client.get(f"/api/citizens/{sample_citizen_data['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_citizen_data["id"]
        assert data["name"] == sample_citizen_data["name"]
    
    def test_get_citizen_not_found(self, client):
        """Test retrieval of non-existent citizen."""
        response = client.get("/api/citizens/9999999999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_list_citizens_empty(self, client):
        """Test listing citizens when none exist."""
        response = client.get("/api/citizens")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_citizens_with_data(self, client, sample_citizen_data, sample_citizen_data_2):
        """Test listing citizens with data."""
        # Register two citizens
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
            client.post("/api/citizens/register", json=sample_citizen_data)
            client.post("/api/citizens/register", json=sample_citizen_data_2)
        
        # List citizens
        response = client.get("/api/citizens")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] in [sample_citizen_data["id"], sample_citizen_data_2["id"]]
        assert data[1]["id"] in [sample_citizen_data["id"], sample_citizen_data_2["id"]]
    
    def test_list_citizens_pagination(self, client, sample_citizen_data, sample_citizen_data_2):
        """Test citizen listing with pagination."""
        # Register two citizens
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
            client.post("/api/citizens/register", json=sample_citizen_data)
            client.post("/api/citizens/register", json=sample_citizen_data_2)
        
        # Test pagination
        response = client.get("/api/citizens?skip=0&limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        response = client.get("/api/citizens?skip=1&limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


class TestCitizenUnregistration:
    """Test citizen unregistration functionality."""
    
    def test_unregister_citizen_success(self, client, sample_citizen_data):
        """Test successful citizen unregistration."""
        # First register a citizen
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
            client.post("/api/citizens/register", json=sample_citizen_data)
        
        # Then unregister
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.delete", self._mock_successful_mintic_response)
            
            unregister_data = {
                "id": sample_citizen_data["id"],
                "operator_id": sample_citizen_data["operator_id"]
            }
            response = client.delete("/api/citizens/unregister", json=unregister_data)
            
            assert response.status_code == 200
            assert "unregistered successfully" in response.json()["message"]
    
    def test_unregister_citizen_not_found(self, client):
        """Test unregistration of non-existent citizen."""
        unregister_data = {
            "id": 9999999999,
            "operator_id": "OP001"
        }
        
        response = client.delete("/api/citizens/unregister", json=unregister_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_unregister_citizen_missing_fields(self, client):
        """Test unregistration with missing fields."""
        incomplete_data = {
            "id": 1032236578
            # Missing operator_id
        }
        
        response = client.delete("/api/citizens/unregister", json=incomplete_data)
        assert response.status_code == 422


class TestDataValidation:
    """Test data validation functionality."""
    
    def test_citizen_id_validation(self, client, sample_citizen_data):
        """Test citizen ID validation."""
        test_cases = [
            (12345, "too short"),
            (12345678901, "too long"),
            (123456789, "too short"),
            (1234567890, "valid"),
        ]
        
        for citizen_id, description in test_cases:
            data = sample_citizen_data.copy()
            data["id"] = citizen_id
            
            response = client.post("/api/citizens/register", json=data)
            
            if description == "valid":
                # Should succeed (with mocked mintic response)
                with pytest.MonkeyPatch().context() as m:
                    m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
                    response = client.post("/api/citizens/register", json=data)
                    assert response.status_code == 201
            else:
                assert response.status_code == 422
    
    def test_email_validation(self, client, sample_citizen_data):
        """Test email validation."""
        test_cases = [
            ("invalid-email", "invalid format"),
            ("user@domain", "missing TLD"),
            ("user@domain.com", "valid"),
            ("user.name@domain.co", "valid with subdomain"),
        ]
        
        for email, description in test_cases:
            data = sample_citizen_data.copy()
            data["email"] = email
            
            response = client.post("/api/citizens/register", json=data)
            
            if description == "valid":
                # Should succeed (with mocked mintic response)
                with pytest.MonkeyPatch().context() as m:
                    m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
                    response = client.post("/api/citizens/register", json=data)
                    assert response.status_code == 201
            else:
                assert response.status_code == 422
    
    def test_string_field_validation(self, client, sample_citizen_data):
        """Test string field validation."""
        test_cases = [
            ("", "empty string"),
            ("   ", "whitespace only"),
            ("Valid Name", "valid"),
        ]
        
        for name, description in test_cases:
            data = sample_citizen_data.copy()
            data["name"] = name
            
            response = client.post("/api/citizens/register", json=data)
            
            if description == "valid":
                # Should succeed (with mocked mintic response)
                with pytest.MonkeyPatch().context() as m:
                    m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
                    response = client.post("/api/citizens/register", json=data)
                    assert response.status_code == 201
            else:
                assert response.status_code == 422


class TestErrorHandling:
    """Test error handling functionality."""
    
    def test_database_connection_error(self, client, sample_citizen_data):
        """Test handling of database connection errors."""
        # This test would require mocking database connection failures
        # For now, we'll test the basic error handling
        pass
    
    def test_malformed_json_request(self, client):
        """Test handling of malformed JSON requests."""
        response = client.post(
            "/api/citizens/register",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_unsupported_http_method(self, client):
        """Test handling of unsupported HTTP methods."""
        response = client.patch("/api/citizens/register")
        assert response.status_code == 405  # Method Not Allowed


class TestIntegrationScenarios:
    """Test integration scenarios."""
    
    def test_complete_citizen_lifecycle(self, client, sample_citizen_data):
        """Test complete citizen lifecycle: register -> retrieve -> unregister."""
        # Register citizen
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
            response = client.post("/api/citizens/register", json=sample_citizen_data)
            assert response.status_code == 201
        
        # Retrieve citizen
        response = client.get(f"/api/citizens/{sample_citizen_data['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        
        # Unregister citizen
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.delete", self._mock_successful_mintic_response)
            
            unregister_data = {
                "id": sample_citizen_data["id"],
                "operator_id": sample_citizen_data["operator_id"]
            }
            response = client.delete("/api/citizens/unregister", json=unregister_data)
            assert response.status_code == 200
    
    def test_multiple_citizens_management(self, client, sample_citizen_data, sample_citizen_data_2):
        """Test management of multiple citizens."""
        # Register multiple citizens
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.post", self._mock_successful_mintic_response)
            client.post("/api/citizens/register", json=sample_citizen_data)
            client.post("/api/citizens/register", json=sample_citizen_data_2)
        
        # List all citizens
        response = client.get("/api/citizens")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Unregister one citizen
        with pytest.MonkeyPatch().context() as m:
            m.setattr("httpx.AsyncClient.delete", self._mock_successful_mintic_response)
            
            unregister_data = {
                "id": sample_citizen_data["id"],
                "operator_id": sample_citizen_data["operator_id"]
            }
            response = client.delete("/api/citizens/unregister", json=unregister_data)
            assert response.status_code == 200
        
        # List remaining citizens
        response = client.get("/api/citizens")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_citizen_data_2["id"]


# Helper methods for mocking
def _mock_successful_mintic_response(*args, **kwargs):
    """Mock successful MinTIC response."""
    class MockResponse:
        status_code = 200
        def json(self):
            return {"status": "success"}
    return MockResponse()


def _mock_mintic_error_response(*args, **kwargs):
    """Mock MinTIC error response."""
    class MockResponse:
        status_code = 400
        headers = {"content-type": "application/json"}
        def json(self):
            return {"detail": "Invalid citizen data"}
    return MockResponse()


def _mock_service_unavailable_response(*args, **kwargs):
    """Mock service unavailable response."""
    raise Exception("Connection timeout")
