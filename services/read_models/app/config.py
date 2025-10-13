"""Configuration for read models service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

    
    # CORS
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000")

class Settings(BaseSettings):
    """Read models service settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database (optimized read models)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana"
    )
    
    # Azure Service Bus
    servicebus_connection_string: str = Field(default="", alias="SERVICEBUS_CONNECTION_STRING")
    
    # Redis (for cache and idempotency)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_ssl: bool = Field(default=False)
    
    # Environment
    environment: str = Field(default="development")
