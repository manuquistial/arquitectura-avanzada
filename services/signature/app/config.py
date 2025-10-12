"""Configuration for signature service."""

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Signature service settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Environment
    environment: str = Field(default="development")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana"
    )
    
    # Azure Blob Storage (for SAS tokens)
    azure_storage_account_name: str = Field(default="")
    azure_storage_account_key: str = Field(default="")
    sas_ttl_minutes: int = Field(default=15, alias="SAS_TTL_MINUTES")
    azure_storage_container: str = Field(default="documents")
    
    # MinTIC Hub (public API, no authentication required)
    mintic_hub_url: str = Field(default="https://govcarpeta-apis-4905ff3c005b.herokuapp.com")
    mintic_operator_id: str = Field(default="operator-demo")
    mintic_operator_name: str = Field(default="Carpeta Ciudadana Demo")
    
    # Signing (mock RSA or K8s secret)
    signing_private_key_path: str = Field(default="")  # Path to RSA private key in K8s secret
    signing_algorithm: str = Field(default="RS256")
    
    # Redis (for idempotency cache)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_ssl: bool = Field(default=False)
    
    # Service Bus (mock for development)
    service_bus_enabled: bool = Field(default=False)
    service_bus_connection_string: str = Field(default="")
    service_bus_topic_name: str = Field(default="document-events")
    
    # Internal services
    metadata_service_url: str = Field(default="http://metadata:8000")

