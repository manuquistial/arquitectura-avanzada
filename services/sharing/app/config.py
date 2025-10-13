"""Configuration for sharing service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

    
    # CORS
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000")

class Settings(BaseSettings):
    """Sharing service settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana"
    )
    
    # Azure Blob Storage (for SAS generation)
    azure_storage_account_name: str = Field(default="")
    azure_storage_account_key: str = Field(default="")
    azure_storage_container: str = Field(default="documents")
    
    # Redis (for shortlink cache)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_ssl: bool = Field(default=False)
    
    # IAM service (for ABAC)
    iam_service_url: str = Field(default="http://iam:8000")
    
    # Service Bus
    servicebus_connection_string: str = Field(default="", alias="SERVICEBUS_CONNECTION_STRING")
    
    # Shortlink
    shortlink_base_url: str = Field(default="https://carpeta.local")
    shortlink_token_length: int = Field(default=12)
    
    # SAS token defaults
    sas_default_expiry_hours: int = Field(default=24)
    
    # Watermark (optional feature)
    watermark_enabled: bool = Field(default=False)
    watermark_text: str = Field(default="Carpeta Ciudadana")
    
    # Environment
    environment: str = Field(default="development")
