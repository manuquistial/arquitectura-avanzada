"""Gateway configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Gateway settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Environment
    environment: str = Field(default="development")
    
    # Rate limiting (deprecated, now using AdvancedRateLimiter)
    rate_limit_per_minute: int = Field(default=60)
    
    # Redis (for rate limiting)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_ssl: bool = Field(default=False)
    
    # Service URLs (from ConfigMap app-flags)
    citizen_service_url: str = Field(default="http://localhost:8001", alias="CITIZEN_URL")
    ingestion_service_url: str = Field(default="http://localhost:8002", alias="INGESTION_URL")
    metadata_service_url: str = Field(default="http://localhost:8003", alias="METADATA_URL")
    transfer_service_url: str = Field(default="http://localhost:8004", alias="TRANSFER_URL")
    mintic_client_url: str = Field(default="http://localhost:8005", alias="MINTIC_CLIENT_URL")
    signature_service_url: str = Field(default="http://localhost:8006", alias="SIGNATURE_URL")
    sharing_service_url: str = Field(default="http://localhost:8011", alias="SHARING_URL")
    notification_service_url: str = Field(default="http://localhost:8010", alias="NOTIFICATION_URL")
    
    # CORS (from ConfigMap cors-origins)
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")
    
    # JWT validation (for auth middleware)
    jwt_secret_key: str = Field(default="dev-secret-key-change-in-production")
    jwt_algorithm: str = Field(default="HS256")
    
    # Public routes (no authentication required)
    public_routes: list[str] = Field(
        default=[
            "/health",
            "/docs",
            "/openapi.json",
            "/api/citizens/register",
            "/api/auth/login",
            "/api/auth/token",
            "/ops/ratelimit/status"
        ]
    )
