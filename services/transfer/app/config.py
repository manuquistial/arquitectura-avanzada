"""Configuration for Transfer Service."""

from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Transfer Service settings."""

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
    
    # Azure Storage configuration
    azure_storage_account_name: str = Field(default="", alias="AZURE_STORAGE_ACCOUNT_NAME", description="Azure Storage account name")
    azure_storage_account_key: Optional[str] = Field(default=None, alias="AZURE_STORAGE_ACCOUNT_KEY", description="Azure Storage account key")
    azure_storage_container_name: str = Field(default="documents", alias="AZURE_STORAGE_CONTAINER_NAME", description="Azure Storage container name")
    azure_storage_connection_string: Optional[str] = Field(default=None, alias="AZURE_STORAGE_CONNECTION_STRING", description="Azure Storage connection string")
    azure_storage_sas_ttl_minutes: int = Field(default=15, alias="AZURE_STORAGE_SAS_TTL_MINUTES", description="SAS token TTL in minutes")
    
    # Azure Service Bus configuration
    servicebus_connection_string: Optional[str] = Field(default=None, alias="SERVICEBUS_CONNECTION_STRING", description="Service Bus connection string")
    servicebus_namespace: Optional[str] = Field(default=None, alias="SERVICEBUS_NAMESPACE", description="Service Bus namespace")
    servicebus_enabled: bool = Field(default=False, alias="SERVICEBUS_ENABLED", description="Enable Service Bus integration")
    
    # Azure Cache for Redis Configuration
    redis_host: str = Field(default="", alias="REDIS_HOST", description="Azure Cache for Redis hostname")
    redis_port: int = Field(default=6380, alias="REDIS_PORT", description="Azure Cache for Redis TLS port")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD", description="Azure Cache for Redis primary key")
    redis_db: int = Field(default=0, alias="REDIS_DB", description="Redis database number")
    redis_ssl: bool = Field(default=True, alias="REDIS_SSL", description="Always true for Azure Cache for Redis")
    redis_enabled: bool = Field(default=True, alias="REDIS_ENABLED", description="Enable Redis cache")
    
    # Transfer-specific settings
    max_document_size_mb: int = Field(default=50, alias="MAX_DOCUMENT_SIZE_MB", description="Maximum document size in MB")
    download_timeout_seconds: int = Field(default=300, alias="DOWNLOAD_TIMEOUT_SECONDS", description="Timeout for document downloads in seconds")
    
    # JWT Configuration
    jwt_secret: str = Field(default="mock_jwt_secret_123", alias="JWT_SECRET", description="JWT secret key for token signing")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM", description="JWT algorithm for token signing")
    jwt_expiration_hours: int = Field(default=24, alias="JWT_EXPIRATION_HOURS", description="JWT token expiration in hours")
    
    # Health check settings
    health_check_timeout: int = Field(default=5, alias="HEALTH_CHECK_TIMEOUT", description="Health check timeout in seconds")
    
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
            return v  # Keep as string for consistency with mintic_client
        return ",".join(v) if isinstance(v, list) else v
    
    @property
    def redis_url(self) -> str:
        """Build Azure Cache for Redis URL."""
        if not self.redis_host or not self.redis_password:
            raise ValueError("Redis host and password must be configured for Azure Cache for Redis")
        return f"rediss://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    def get_database_url(self) -> str:
        """Get the database connection URL."""
        #if self.database_url:
        #    return self.database_url
        
        # Build URL from individual components
        # For asyncpg, use ssl parameter instead of sslmode
        # Based on test_pod_db_connection.py results, asyncpg works with ssl='require'
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