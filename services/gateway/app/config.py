"""Gateway configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Gateway settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Rate limiting
    rate_limit_per_minute: int = Field(default=60)

    # Redis for rate limiting
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)

    # JWT (preparado para Azure AD B2C o Cognito)
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = Field(default="RS256")

    # Auth (TODO: implementar Azure AD B2C)
    auth_provider: str = Field(default="mock")  # mock, azure-ad-b2c, cognito

    # Backend services
    citizen_service_url: str = Field(default="http://citizen:8000")
    ingestion_service_url: str = Field(default="http://ingestion:8000")
    metadata_service_url: str = Field(default="http://metadata:8000")
    signature_service_url: str = Field(default="http://signature:8000")
    transfer_service_url: str = Field(default="http://transfer:8000")
    sharing_service_url: str = Field(default="http://sharing:8000")
    notification_service_url: str = Field(default="http://notification:8000")
    mintic_client_url: str = Field(default="http://mintic-client:8000")

