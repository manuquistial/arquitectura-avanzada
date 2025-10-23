"""Configuration for MinTIC Client Service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MinTIC Client settings."""

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix=""
    )

    # CORS
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000")

    # MinTIC Hub (GovCarpeta APIs - public API, no auth required)
    mintic_base_url: str = Field(default="https://mock-mintic-hub.example.com")
    mintic_operator_id: str = Field(default="operator-demo")
    mintic_operator_name: str = Field(default="Carpeta Ciudadana Demo")

    # Retry configuration
    max_retries: int = Field(default=3)
    retry_backoff_factor: float = Field(default=2.0)
    request_timeout: int = Field(default=10)
    
    # Azure Cache for Redis
    redis_host: str = Field(default="mock-redis-host.redis.cache.windows.net", alias="REDIS_HOST", description="Azure Cache for Redis hostname")
    redis_port: int = Field(default=6380, alias="REDIS_PORT", description="Azure Cache for Redis TLS port")
    redis_password: str = Field(default="mock_redis_password_123", alias="REDIS_PASSWORD", description="Azure Cache for Redis primary key")
    redis_ssl: bool = Field(default=True, alias="REDIS_SSL", description="Always true for Azure Cache for Redis")
    redis_enabled: bool = Field(default=True, alias="REDIS_ENABLED", description="Enable Redis cache")
    
    # Security
    environment: str = Field(default="development", alias="ENVIRONMENT")
    allow_insecure_operator_urls: bool = Field(
        default=True,
        alias="ALLOW_INSECURE_OPERATOR_URLS",
        description="Allow http:// URLs in development (only https:// in production)"
    )
    
    # Hub rate limiting (protect public hub from saturation)
    hub_rate_limit_per_minute: int = Field(default=10, alias="HUB_RATE_LIMIT_PER_MINUTE")
    hub_rate_limit_enabled: bool = Field(default=True, alias="HUB_RATE_LIMIT_ENABLED")
    
    # Internal service URLs (development local)
    metadata_url: str = Field(default="http://localhost:8001", alias="METADATA_URL")
    citizen_url: str = Field(default="http://localhost:8000", alias="CITIZEN_URL")
    transfer_url: str = Field(default="http://localhost:8002", alias="TRANSFER_URL")
    signature_url: str = Field(default="http://localhost:8003", alias="SIGNATURE_URL")
    document_url: str = Field(default="http://localhost:8004", alias="DOCUMENT_URL")
    
    # Hub URL (alias for mintic_base_url)
    hub_url: str = Field(default="https://mock-mintic-hub.example.com", alias="HUB_URL")
    operator_id: str = Field(default="operator-demo", alias="OPERATOR_ID")
    
    # Database configuration (using same Azure PostgreSQL as other services)
    database_host: str = Field(default="mock-postgres-host.database.azure.com", alias="DB_HOST")
    database_port: int = Field(default=5432, alias="DB_PORT")
    database_name: str = Field(default="carpeta_ciudadana", alias="DB_NAME")
    database_user: str = Field(default="mock_user", alias="DB_USER")
    database_password: str = Field(default="mock_password_123", alias="DB_PASSWORD")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")