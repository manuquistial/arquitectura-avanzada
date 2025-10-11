"""Configuration for citizen service."""

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_service_url(service_name: str, default_port: int) -> str:
    """Get service URL based on environment.
    
    Development: http://localhost:{port}
    Kubernetes: http://carpeta-ciudadana-{service}:8000
    """
    env = os.getenv("ENVIRONMENT", "development")
    if env == "development":
        return f"http://localhost:{default_port}"
    else:
        # Kubernetes service discovery
        namespace = os.getenv("NAMESPACE", "carpeta-ciudadana")
        release_name = os.getenv("HELM_RELEASE_NAME", "carpeta-ciudadana")
        return f"http://{release_name}-{service_name}:8000"


class Settings(BaseSettings):
    """Citizen service settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana"
    )

    # Service URLs (auto-detect environment)
    mintic_client_url: str = Field(
        default_factory=lambda: os.getenv("MINTIC_CLIENT_URL") or get_service_url("mintic-client", 8005)
    )
    
    # Environment
    environment: str = Field(default="development")

