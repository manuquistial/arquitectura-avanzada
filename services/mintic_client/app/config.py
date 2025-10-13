"""Configuration for MinTIC Client Service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MinTIC Client settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000")

    # MinTIC Hub (GovCarpeta APIs - public API, no auth required)
    mintic_base_url: str = Field(default="https://govcarpeta-apis-4905ff3c005b.herokuapp.com")
    mintic_operator_id: str = Field(default="operator-demo")
    mintic_operator_name: str = Field(default="Carpeta Ciudadana Demo")

    # Retry configuration
    max_retries: int = Field(default=3)
    retry_backoff_factor: float = Field(default=2.0)
    request_timeout: int = Field(default=10)
    
    # Redis cache
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_ssl: bool = Field(default=False)
    
    # Security
    environment: str = Field(default="development", alias="ENVIRONMENT")
    allow_insecure_operator_urls: bool = Field(
        default=True,
        alias="ALLOW_INSECURE_OPERATOR_URLS",
        description="Allow http:// URLs in development (only https:// in production)"
    )
    
    # Hub rate limiting (protect public hub from saturation)
    hub_rate_limit_per_minute: int = Field(default=10, env="HUB_RATE_LIMIT_PER_MINUTE")
    hub_rate_limit_enabled: bool = Field(default=True, env="HUB_RATE_LIMIT_ENABLED")
