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
    
    # Service URLs (auto-discovery based on environment)
    citizen_service_url: str = Field(default="")
    ingestion_service_url: str = Field(default="")
    metadata_service_url: str = Field(default="")
    transfer_service_url: str = Field(default="")
    mintic_client_service_url: str = Field(default="")
    signature_service_url: str = Field(default="")
    sharing_service_url: str = Field(default="")
    
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
