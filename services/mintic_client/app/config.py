"""Configuration for MinTIC Client Service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MinTIC Client settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # MinTIC Hub (GovCarpeta APIs - public API, no auth required)
    mintic_base_url: str = Field(default="https://govcarpeta-apis-4905ff3c005b.herokuapp.com")
    mintic_operator_id: str = Field(default="operator-demo")
    mintic_operator_name: str = Field(default="Carpeta Ciudadana Demo")

    # Retry configuration
    max_retries: int = Field(default=3)
    retry_backoff_factor: float = Field(default=2.0)
    request_timeout: int = Field(default=30)

