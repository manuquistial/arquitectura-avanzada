"""Configuration for Auth Service"""

import os
from functools import lru_cache
from typing import List


class Settings:
    """Auth service settings"""
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Service configuration
    service_id: str = "auth"
    service_port: int = 8011
    
    # OIDC configuration
    oidc_issuer_url: str = os.getenv(
        "OIDC_ISSUER_URL",
        "http://localhost:8011"
    )
    
    # JWT configuration
    jwt_algorithm: str = "RS256"
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE", "60"))
    jwt_refresh_token_expire_days: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    
    # Private key for signing (TODO: Load from Key Vault)
    jwt_private_key_path: str = os.getenv("JWT_PRIVATE_KEY_PATH", "/etc/auth/private_key.pem")
    jwt_public_key_path: str = os.getenv("JWT_PUBLIC_KEY_PATH", "/etc/auth/public_key.pem")
    
    # Azure AD B2C (for token validation)
    azure_b2c_tenant_name: str = os.getenv("AZURE_AD_B2C_TENANT_NAME", "")
    azure_b2c_tenant_id: str = os.getenv("AZURE_AD_B2C_TENANT_ID", "")
    azure_b2c_client_id: str = os.getenv("AZURE_AD_B2C_CLIENT_ID", "")
    
    # Database (for sessions)
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:pass@localhost/carpeta_ciudadana"
    )
    
    # Redis (for session storage)
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    redis_db: int = int(os.getenv("REDIS_SESSION_DB", "1"))
    
    # CORS
    cors_origins: List[str] = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "*"
    ).split(",")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
