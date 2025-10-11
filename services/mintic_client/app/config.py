"""Configuration for MinTIC Client Service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MinTIC Client settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # MinTIC Hub
    mintic_base_url: str = Field(default="https://hub.mintic.gov.co")
    mintic_operator_id: str = Field(default="")
    mintic_operator_name: str = Field(default="")
    mintic_client_id: str = Field(default="")
    mintic_client_secret: str = Field(default="")

    # mTLS Certificates
    mtls_cert_path: str = Field(default="/etc/ssl/certs/client.crt")
    mtls_key_path: str = Field(default="/etc/ssl/private/client.key")
    ca_bundle_path: str = Field(default="/etc/ssl/certs/ca-bundle.crt")

    # Retry configuration
    max_retries: int = Field(default=3)
    retry_backoff_factor: float = Field(default=2.0)
    request_timeout: int = Field(default=30)

