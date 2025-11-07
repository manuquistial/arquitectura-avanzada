"""Configuration for Metadata Service."""

from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Metadata Service settings."""

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
    
    # Database configuration (using same Azure PostgreSQL as other services)
    database_host: str = Field(default="mock-postgres-host.database.azure.com", alias="DB_HOST", description="Database hostname")
    database_port: int = Field(default=5432, alias="DB_PORT", description="Database port")
    database_name: str = Field(default="carpeta_ciudadana", alias="DB_NAME", description="Database name")
    database_user: str = Field(default="mock_user", alias="DB_USER", description="Database user")
    database_password: str = Field(default="mock_password_123", alias="DB_PASSWORD", description="Database password")
    database_sslmode: str = Field(default="require", alias="DB_SSLMODE", description="Database SSL mode")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO", description="Enable SQLAlchemy echo")
    
    # Legacy support for DATABASE_URL
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL", description="Full database URL")
    
    # Azure Service Bus configuration
    servicebus_connection_string: Optional[str] = Field(default=None, alias="SERVICEBUS_CONNECTION_STRING", description="Service Bus connection string")
    servicebus_namespace: Optional[str] = Field(default=None, alias="SERVICEBUS_NAMESPACE", description="Service Bus namespace")
    servicebus_enabled: bool = Field(default=False, alias="SERVICEBUS_ENABLED", description="Enable Service Bus integration")
    
    # Queue names
    document_events_queue: str = Field(default="document-events", alias="DOCUMENT_EVENTS_QUEUE")
    signature_events_queue: str = Field(default="signature-events", alias="SIGNATURE_EVENTS_QUEUE", description="Queue for signature events (optional)")
    consume_signature_events: bool = Field(default=False, alias="CONSUME_SIGNATURE_EVENTS", description="Enable consumption of signature-events")
    max_messages_per_batch: int = Field(default=10, alias="MAX_MESSAGES_PER_BATCH")
    max_wait_time: float = Field(default=60.0, alias="MAX_WAIT_TIME")
    
    # Redis (for idempotency and cache)
    redis_host: str = Field(default="", alias="REDIS_HOST", description="Azure Cache for Redis hostname")
    redis_port: int = Field(default=6380, alias="REDIS_PORT", description="Azure Cache for Redis TLS port")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD", description="Azure Cache for Redis primary key")
    redis_db: int = Field(default=0, alias="REDIS_DB", description="Redis database number")
    redis_ssl: bool = Field(default=True, alias="REDIS_SSL", description="Always true for Azure Cache for Redis")
    redis_enabled: bool = Field(default=True, alias="REDIS_ENABLED", description="Enable Redis cache")
    
    # Ingestion Service (for API calls if needed)
    ingestion_service_url: str = Field(default="http://localhost:8000", alias="INGESTION_SERVICE_URL")
    
    # OpenSearch (future - for advanced search)
    opensearch_enabled: bool = Field(default=False, alias="OPENSEARCH_ENABLED")
    opensearch_url: Optional[str] = Field(default=None, alias="OPENSEARCH_URL")
    
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
        if v is None:
            return "http://localhost:3000,http://localhost:8000"  # Default value
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            return ",".join(v)
        # If it's neither string nor list, return as-is (Pydantic will use default)
        return v
    
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

