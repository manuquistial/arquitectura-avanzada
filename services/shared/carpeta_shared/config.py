"""Configuration management - Updated for Azure."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureConfig(BaseSettings):
    """Azure configuration."""

    model_config = SettingsConfigDict(env_prefix="AZURE_")

    # Storage (Azure Blob)
    storage_account_name: str = Field(default="mock_storage_account")
    storage_account_key: str = Field(default="mock_storage_key_123")
    storage_connection_string: str = Field(default="mock_connection_string")
    storage_container_name: str = Field(default="documents")

    # Service Bus (Azure messaging)
    servicebus_connection_string: str = Field(default="mock_servicebus_connection")
    servicebus_namespace: str = Field(default="mock_namespace")
    servicebus_queue_name: str = Field(default="events-queue")
    servicebus_topic_name: str = Field(default="notifications-topic")

    # Key Vault (equivalente a ACM PCA)
    keyvault_url: str = Field(default="https://mock-keyvault.vault.azure.net/")

    # Azure AD B2C - REMOVED


# AWS configuration removed - using Azure only


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="DB_")

    host: str = Field(default="mock-postgres-host.database.azure.com")
    port: int = Field(default=5432)
    name: str = Field(default="carpeta_ciudadana")
    user: str = Field(default="mock_user")
    password: str = Field(default="mock_password_123")

    @property
    def url(self) -> str:
        """Get database URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class SearchConfig(BaseSettings):
    """Search configuration (OpenSearch o Azure Cognitive Search)."""

    model_config = SettingsConfigDict(env_prefix="SEARCH_")

    host: str = Field(default="localhost")
    port: int = Field(default=9200)
    use_ssl: bool = Field(default=False)
    verify_certs: bool = Field(default=False)
    api_key: str = Field(default="")  # Para Azure Cognitive Search


class RedisConfig(BaseSettings):
    """Azure Cache for Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = Field(default="mock-redis-host.redis.cache.windows.net", description="Azure Cache for Redis hostname (e.g., mycache.redis.cache.windows.net)")
    port: int = Field(default=6380, description="Azure Cache for Redis TLS port")
    db: int = Field(default=0, description="Redis database number")
    password: str = Field(default="mock_redis_password_123", description="Azure Cache for Redis primary key")
    ssl: bool = Field(default=True, description="Always true for Azure Cache for Redis")
    
    @property
    def url(self) -> str:
        """Build Azure Cache for Redis URL."""
        return f"rediss://:{self.password}@{self.host}:{self.port}/{self.db}"


class OTelConfig(BaseSettings):
    """OpenTelemetry configuration."""

    model_config = SettingsConfigDict(env_prefix="OTEL_")

    enabled: bool = Field(default=True)
    exporter_otlp_endpoint: str = Field(default="http://localhost:4317")
    service_name: str = Field(default="carpeta-ciudadana")


class MinTICConfig(BaseSettings):
    """MinTIC Hub configuration."""

    model_config = SettingsConfigDict(env_prefix="MINTIC_")

    base_url: str = Field(default="https://mock-mintic-hub.example.com")
    operator_id: str = Field(default="mock_operator")
    operator_name: str = Field(default="Mock Operator")
    client_id: str = Field(default="mock_client_id_123")
    client_secret: str = Field(default="mock_client_secret_123")
    mtls_cert_path: str = Field(default="/etc/ssl/certs/client.crt")
    mtls_key_path: str = Field(default="/etc/ssl/private/client.key")
    ca_bundle_path: str = Field(default="/etc/ssl/certs/ca-bundle.crt")


class SecurityConfig(BaseSettings):
    """Security configuration."""

    model_config = SettingsConfigDict(env_prefix="SECURITY_")

    jwt_secret: str = Field(default="mock_jwt_secret_123")
    jwt_algorithm: str = Field(default="RS256")
    jwt_expiration_seconds: int = Field(default=3600)
    rate_limit_per_minute: int = Field(default=60)


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cloud_provider: str = Field(default="azure")  # Azure only

    # Azure configuration
    azure: AzureConfig = Field(default_factory=AzureConfig)
    
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    otel: OTelConfig = Field(default_factory=OTelConfig)
    mintic: MinTICConfig = Field(default_factory=MinTICConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
