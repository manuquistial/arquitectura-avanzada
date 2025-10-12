"""Configuration for metadata service."""

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Metadata service settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana"
    )

    # OpenSearch
    opensearch_host: str = Field(default="localhost")
    opensearch_port: int = Field(default=9200)
    opensearch_username: str = Field(default="", alias="OS_USERNAME")
    opensearch_password: str = Field(default="", alias="OS_PASSWORD")
    opensearch_url: str = Field(default="", alias="OPENSEARCH_URL")
    opensearch_use_ssl: bool = Field(default=False)
    opensearch_verify_certs: bool = Field(default=False)
    opensearch_index: str = Field(default="documents")
    
    # Redis (for search caching)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_ssl: bool = Field(default=False)

    # Service Bus (for event consumption)
    servicebus_connection_string: str = Field(default="", alias="SERVICEBUS_CONNECTION_STRING")
    
    # Environment
    environment: str = Field(default="development")

