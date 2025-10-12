"""Configuration for auth service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Auth service settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # OIDC Issuer
    issuer: str = Field(default="https://auth.carpeta-ciudadana.local")
    
    # JWT Configuration
    jwt_algorithm: str = Field(default="RS256")
    jwt_access_token_expire_minutes: int = Field(default=30)
    jwt_refresh_token_expire_minutes: int = Field(default=43200)  # 30 days
    
    # RSA Keys (generated on first run or loaded from K8s secret)
    private_key_path: str = Field(default="")
    public_key_path: str = Field(default="")
    
    # Database (for users)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana"
    )
    
    # Redis (for JWKS cache and token blacklist)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_ssl: bool = Field(default=False)
    
    # Environment
    environment: str = Field(default="development")

