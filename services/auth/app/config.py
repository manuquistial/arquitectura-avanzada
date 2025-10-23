"""Configuration for Auth Service."""

from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Auth Service settings."""

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
    
    # Service configuration
    service_id: str = Field(default="auth", alias="SERVICE_ID", description="Service ID")
    service_port: int = Field(default=8011, alias="SERVICE_PORT", description="Service port")
    
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
    
    # Redis configuration
    redis_host: str = Field(default="localhost", alias="REDIS_HOST", description="Redis host")
    redis_port: int = Field(default=6379, alias="REDIS_PORT", description="Redis port")
    redis_password: str = Field(default="mock_redis_password", alias="REDIS_PASSWORD", description="Redis password")
    redis_db: int = Field(default=1, alias="REDIS_DB", description="Redis database number")
    redis_ssl: bool = Field(default=False, alias="REDIS_SSL", description="Redis SSL enabled")
    redis_enabled: bool = Field(default=True, alias="REDIS_ENABLED", description="Enable Redis cache")
    
    # JWT configuration
    jwt_algorithm: str = Field(default="RS256", alias="JWT_ALGORITHM", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES", description="Access token expiration in minutes")
    jwt_refresh_token_expire_days: int = Field(default=30, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS", description="Refresh token expiration in days")
    jwt_private_key_path: str = Field(default="/etc/auth/private_key.pem", alias="JWT_PRIVATE_KEY_PATH", description="Private key path")
    jwt_public_key_path: str = Field(default="/etc/auth/public_key.pem", alias="JWT_PUBLIC_KEY_PATH", description="Public key path")
    
    # OIDC configuration
    oidc_issuer_url: str = Field(default="http://localhost:8011", alias="OIDC_ISSUER_URL", description="OIDC issuer URL")
    
    # Azure AD B2C configuration - REMOVED
    
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
    
    def get_database_url(self) -> str:
        """Get the database connection URL."""
        if self.database_url:
            return self.database_url
        
        # Build URL from individual components
        return f"postgresql+psycopg://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}?sslmode={self.database_sslmode}"
    
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