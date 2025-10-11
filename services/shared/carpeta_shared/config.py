"""Configuration management - Updated for Azure."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureConfig(BaseSettings):
    """Azure configuration."""

    model_config = SettingsConfigDict(env_prefix="AZURE_")

    # Storage (equivalente a S3)
    storage_account_name: str = Field(default="")
    storage_account_key: str = Field(default="")
    storage_connection_string: str = Field(default="")
    storage_container_name: str = Field(default="documents")

    # Service Bus (equivalente a SQS/SNS)
    servicebus_connection_string: str = Field(default="")
    servicebus_namespace: str = Field(default="")
    servicebus_queue_name: str = Field(default="events-queue")
    servicebus_topic_name: str = Field(default="notifications-topic")

    # Key Vault (equivalente a ACM PCA)
    keyvault_url: str = Field(default="")

    # Azure AD B2C (equivalente a Cognito)
    tenant_id: str = Field(default="")
    client_id: str = Field(default="")
    client_secret: str = Field(default="")
    b2c_tenant_name: str = Field(default="")
    b2c_policy_name: str = Field(default="B2C_1_signupsignin")


# Mantener AWS Config para retrocompatibilidad
class AWSConfig(BaseSettings):
    """AWS configuration (legacy)."""

    model_config = SettingsConfigDict(env_prefix="AWS_")

    region: str = Field(default="us-east-1")
    s3_bucket: str = Field(default="carpeta-ciudadana-documents")
    sqs_queue_url: str = Field(default="")
    sns_topic_arn: str = Field(default="")
    cognito_user_pool_id: str = Field(default="")
    cognito_client_id: str = Field(default="")
    acm_pca_arn: str = Field(default="")


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="DB_")

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="carpeta_ciudadana")
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")

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
    """Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: str | None = Field(default=None)


class OTelConfig(BaseSettings):
    """OpenTelemetry configuration."""

    model_config = SettingsConfigDict(env_prefix="OTEL_")

    enabled: bool = Field(default=True)
    exporter_otlp_endpoint: str = Field(default="http://localhost:4317")
    service_name: str = Field(default="carpeta-ciudadana")


class MinTICConfig(BaseSettings):
    """MinTIC Hub configuration."""

    model_config = SettingsConfigDict(env_prefix="MINTIC_")

    base_url: str = Field(default="https://hub.mintic.gov.co")
    operator_id: str = Field(default="")
    operator_name: str = Field(default="")
    client_id: str = Field(default="")
    client_secret: str = Field(default="")
    mtls_cert_path: str = Field(default="/etc/ssl/certs/client.crt")
    mtls_key_path: str = Field(default="/etc/ssl/private/client.key")
    ca_bundle_path: str = Field(default="/etc/ssl/certs/ca-bundle.crt")


class SecurityConfig(BaseSettings):
    """Security configuration."""

    model_config = SettingsConfigDict(env_prefix="SECURITY_")

    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = Field(default="RS256")
    jwt_expiration_seconds: int = Field(default=3600)
    rate_limit_per_minute: int = Field(default=60)


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cloud_provider: str = Field(default="azure")  # "aws" o "azure"

    # Azure (nuevo)
    azure: AzureConfig = Field(default_factory=AzureConfig)
    
    # AWS (legacy, mantener para retrocompatibilidad)
    aws: AWSConfig = Field(default_factory=AWSConfig)
    
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    otel: OTelConfig = Field(default_factory=OTelConfig)
    mintic: MinTICConfig = Field(default_factory=MinTICConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
