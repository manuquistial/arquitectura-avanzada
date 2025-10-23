"""Configuration for metadata service - Updated for Azure PostgreSQL."""

import os
from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration - Same as ingestion service."""
    
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database connection parameters - Azure PostgreSQL
    host: str = Field(default="mock-postgres-host.database.azure.com", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="carpeta_ciudadana", description="Database name")
    user: str = Field(default="mock_user", description="Database user")
    password: str = Field(default="mock_password_123", description="Database password")
    sslmode: str = Field(default="require", description="SSL mode")
    
    # Legacy support for DATABASE_URL
    url: Optional[str] = Field(default=None, alias="DATABASE_URL", description="Full database URL")
    
    @validator("sslmode")
    def validate_sslmode(cls, v):
        """Validate SSL mode."""
        valid_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
        if v not in valid_modes:
            raise ValueError(f"Invalid SSL mode: {v}. Must be one of {valid_modes}")
        return v
    
    @property
    def connection_url(self) -> str:
        """Get the database connection URL."""
        if self.url:
            return self.url
        
        # Build URL from individual components - using psycopg for Azure PostgreSQL
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}?sslmode={self.sslmode}"
    
    @property
    def is_azure_postgresql(self) -> bool:
        """Check if this is an Azure PostgreSQL connection."""
        return "postgres.database.azure.com" in self.host


class OpenSearchConfig(BaseSettings):
    """OpenSearch configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="OPENSEARCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    host: str = Field(default="localhost", description="OpenSearch host")
    port: int = Field(default=9200, description="OpenSearch port")
    username: str = Field(default="", description="OpenSearch username")
    password: str = Field(default="", description="OpenSearch password")
    use_ssl: bool = Field(default=False, description="Use SSL for OpenSearch")
    verify_certs: bool = Field(default=False, description="Verify SSL certificates")
    index: str = Field(default="documents", description="OpenSearch index name")


class RedisConfig(BaseSettings):
    """Redis configuration for caching."""
    
    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: str = Field(default="", description="Redis password")
    ssl: bool = Field(default=False, description="Use SSL for Redis")


class ServiceBusConfig(BaseSettings):
    """Azure Service Bus configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="SERVICEBUS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    connection_string: Optional[str] = Field(default=None, description="Service Bus connection string")
    namespace: Optional[str] = Field(default=None, description="Service Bus namespace")
    enabled: bool = Field(default=False, description="Enable Service Bus integration")


class ApplicationConfig(BaseSettings):
    """Application configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application settings
    environment: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS origins"
    )
    
    # Kubernetes settings
    pod_name: Optional[str] = Field(default=None, description="Kubernetes pod name")
    pod_namespace: Optional[str] = Field(default=None, description="Kubernetes namespace")
    node_name: Optional[str] = Field(default=None, description="Kubernetes node name")
    
    # Azure Workload Identity
    azure_client_id: Optional[str] = Field(default=None, description="Azure client ID")
    azure_tenant_id: Optional[str] = Field(default=None, description="Azure tenant ID")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


class MetadataConfig(BaseSettings):
    """Main configuration for metadata service."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    opensearch: OpenSearchConfig = Field(default_factory=OpenSearchConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    servicebus: ServiceBusConfig = Field(default_factory=ServiceBusConfig)
    app: ApplicationConfig = Field(default_factory=ApplicationConfig)
    
    # Service-specific settings
    cache_ttl_seconds: int = Field(default=120, description="Cache TTL in seconds")
    search_page_size: int = Field(default=20, description="Default search page size")
    max_search_results: int = Field(default=1000, description="Maximum search results")
    
    def get_database_url(self) -> str:
        """Get the database connection URL."""
        return self.database.connection_url
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app.environment.lower() == "production"
    
    def is_azure_environment(self) -> bool:
        """Check if running in Azure environment."""
        return self.database.is_azure_postgresql


# Global configuration instance
config = MetadataConfig()


def get_config() -> MetadataConfig:
    """Get the application configuration."""
    return config


def reload_config():
    """Reload configuration from environment variables."""
    global config
    config = MetadataConfig()
    return config


# Legacy Settings class for backward compatibility
class Settings:
    """Legacy settings class for backward compatibility."""
    
    def __init__(self):
        self._config = get_config()
    
    @property
    def database_url(self) -> str:
        return self._config.get_database_url()
    
    @property
    def opensearch_host(self) -> str:
        return self._config.opensearch.host
    
    @property
    def opensearch_port(self) -> int:
        return self._config.opensearch.port
    
    @property
    def opensearch_username(self) -> str:
        return self._config.opensearch.username
    
    @property
    def opensearch_password(self) -> str:
        return self._config.opensearch.password
    
    @property
    def opensearch_use_ssl(self) -> bool:
        return self._config.opensearch.use_ssl
    
    @property
    def opensearch_verify_certs(self) -> bool:
        return self._config.opensearch.verify_certs
    
    @property
    def opensearch_index(self) -> str:
        return self._config.opensearch.index
    
    @property
    def redis_host(self) -> str:
        return self._config.redis.host
    
    @property
    def redis_port(self) -> int:
        return self._config.redis.port
    
    @property
    def redis_password(self) -> str:
        return self._config.redis.password
    
    @property
    def redis_ssl(self) -> bool:
        return self._config.redis.ssl
    
    @property
    def servicebus_connection_string(self) -> str:
        return self._config.servicebus.connection_string or ""
    
    @property
    def environment(self) -> str:
        return self._config.app.environment
    
    @property
    def cors_origins(self) -> str:
        return ",".join(self._config.app.cors_origins)

