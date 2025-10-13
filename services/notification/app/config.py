"""Configuration for notification service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

    
    # CORS
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000")

class Settings(BaseSettings):
    """Notification service settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database (for delivery log)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana"
    )
    
    # Service Bus
    servicebus_connection_string: str = Field(default="", alias="SERVICEBUS_CONNECTION_STRING")
    
    # Email (SMTP)
    smtp_enabled: bool = Field(default=False)
    smtp_host: str = Field(default="localhost")
    smtp_port: int = Field(default=1025)  # Mailhog default
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_use_tls: bool = Field(default=False)
    smtp_from_email: str = Field(default="noreply@carpeta-ciudadana.local")
    smtp_from_name: str = Field(default="Carpeta Ciudadana")
    
    # Webhook
    webhook_enabled: bool = Field(default=True)
    webhook_url: str = Field(default="", alias="NOTIF_WEBHOOK_URL")
    webhook_timeout: int = Field(default=10)
    webhook_retry_max: int = Field(default=3)
    
    # Retry configuration
    max_retries: int = Field(default=3)
    retry_backoff_factor: float = Field(default=2.0)
    
    # OpenTelemetry
    otel_enabled: bool = Field(default=True)
    otel_service_name: str = Field(default="notification-service")
    otel_endpoint: str = Field(default="http://localhost:4317")
    
    # Environment
    environment: str = Field(default="development")
