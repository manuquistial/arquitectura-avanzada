"""Configuration for Notification Service."""

from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Notification Service settings."""

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix=""
    )

    # CORS
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000")
    
    # Application settings
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Azure Service Bus configuration
    servicebus_connection_string: Optional[str] = Field(default=None, alias="SERVICEBUS_CONNECTION_STRING", description="Service Bus connection string")
    servicebus_namespace: Optional[str] = Field(default=None, alias="SERVICEBUS_NAMESPACE", description="Service Bus namespace")
    servicebus_enabled: bool = Field(default=False, alias="SERVICEBUS_ENABLED", description="Enable Service Bus integration")
    
    # Queue names
    citizen_events_queue: str = Field(default="citizen-events", alias="CITIZEN_EVENTS_QUEUE")
    max_messages_per_batch: int = Field(default=10, alias="MAX_MESSAGES_PER_BATCH")
    max_wait_time: float = Field(default=60.0, alias="MAX_WAIT_TIME")
    
    # Database configuration (for accessing citizen data if needed)
    database_host: str = Field(default="mock-postgres-host.database.azure.com", alias="DB_HOST", description="Database hostname")
    database_port: int = Field(default=5432, alias="DB_PORT", description="Database port")
    database_name: str = Field(default="carpeta_ciudadana", alias="DB_NAME", description="Database name")
    database_user: str = Field(default="mock_user", alias="DB_USER", description="Database user")
    database_password: str = Field(default="mock_password_123", alias="DB_PASSWORD", description="Database password")
    database_sslmode: str = Field(default="require", alias="DB_SSLMODE", description="Database SSL mode")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO", description="Enable SQLAlchemy echo")
    
    # Legacy support for DATABASE_URL
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL", description="Full database URL")
    
    # Email/SMTP configuration (future - for sending emails)
    smtp_enabled: bool = Field(default=False, alias="SMTP_ENABLED", description="Enable SMTP for email notifications")
    smtp_host: Optional[str] = Field(default=None, alias="SMTP_HOST", description="SMTP server hostname")
    smtp_port: int = Field(default=587, alias="SMTP_PORT", description="SMTP server port")
    smtp_user: Optional[str] = Field(default=None, alias="SMTP_USER", description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, alias="SMTP_PASSWORD", description="SMTP password")
    smtp_from: Optional[str] = Field(default=None, alias="SMTP_FROM", description="From email address")
    
    # Citizen Service URL (for API calls if needed)
    citizen_service_url: str = Field(default="http://localhost:8000", alias="CITIZEN_SERVICE_URL")
    
    # Auth Service URL (for user data if needed)
    auth_service_url: str = Field(default="http://localhost:8001", alias="AUTH_SERVICE_URL")
    
    # Kubernetes settings
    pod_name: Optional[str] = Field(default=None, alias="POD_NAME", description="Kubernetes pod name")
    pod_namespace: Optional[str] = Field(default=None, alias="POD_NAMESPACE", description="Kubernetes namespace")
    node_name: Optional[str] = Field(default=None, alias="NODE_NAME", description="Kubernetes node name")
    
    # Azure Workload Identity
    azure_client_id: Optional[str] = Field(default=None, alias="AZURE_CLIENT_ID", description="Azure client ID")
    azure_tenant_id: Optional[str] = Field(default=None, alias="AZURE_TENANT_ID", description="Azure tenant ID")
    
    @validator("database_sslmode")
    def validate_sslmode(cls, v):
        """Validate SSL mode."""
        valid_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
        if v not in valid_modes:
            raise ValueError(f"Invalid SSL mode: {v}. Must be one of {valid_modes}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return v
        return ",".join(v) if isinstance(v, list) else v
    
    def get_database_url(self) -> str:
        """Get the database connection URL."""
        # Build URL from individual components (asyncpg uses ssl param)
        return f"postgresql+asyncpg://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}?ssl=require"
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    def is_azure_environment(self) -> bool:
        """Check if running in Azure environment."""
        return "postgres.database.azure.com" in self.database_host


# Global configuration instance
config = Settings()


def get_config() -> Settings:
    """Get the application configuration."""
    return config


def get_settings() -> Settings:
    """Get application settings (alias for compatibility)."""
    return config


def reload_config():
    """Reload configuration from environment variables."""
    global config
    config = Settings()
    return config

