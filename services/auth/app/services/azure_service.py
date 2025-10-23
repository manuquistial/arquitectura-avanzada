"""
Azure Services Integration
Handles Azure AD B2C and Kubernetes Secrets integration
Note: We use Kubernetes Secrets, not Azure Key Vault
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class KubernetesSecretsService:
    """Kubernetes Secrets integration for secrets management."""
    
    def __init__(self):
        self.secrets_mount_path = "/var/secrets"
        self._validate_mount_path()
    
    def _validate_mount_path(self):
        """Validate Kubernetes secrets mount path."""
        try:
            if os.path.exists(self.secrets_mount_path):
                logger.info(f"✅ Kubernetes secrets mounted at: {self.secrets_mount_path}")
                return True
            else:
                logger.warning(f"⚠️ Kubernetes secrets not mounted at: {self.secrets_mount_path}")
                return False
        except Exception as e:
            logger.error(f"❌ Error validating secrets mount: {e}")
            return False
    
    async def get_secret(self, secret_name: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        Retrieve secret from Kubernetes Secrets.
        
        Args:
            secret_name: Name of the secret file
            default_value: Default value if secret not found
            
        Returns:
            Secret value or default_value
        """
        try:
            # Try to read from Kubernetes secrets mount
            secret_path = os.path.join(self.secrets_mount_path, secret_name)
            
            if os.path.exists(secret_path):
                with open(secret_path, 'r') as f:
                    secret_value = f.read().strip()
                logger.info(f"✅ Retrieved Kubernetes secret: {secret_name}")
                return secret_value
            else:
                # Fallback to environment variable
                env_var = os.getenv(secret_name.upper().replace('-', '_'))
                if env_var:
                    logger.info(f"✅ Retrieved secret from environment: {secret_name}")
                    return env_var
                else:
                    logger.warning(f"⚠️ Secret not found: {secret_name}, using default")
                    return default_value
                    
        except Exception as e:
            logger.error(f"❌ Error retrieving secret {secret_name}: {e}")
            return default_value
    
    async def get_database_credentials(self) -> Dict[str, str]:
        """Get database credentials from Kubernetes Secrets."""
        try:
            credentials = {}
            
            # Get database password from Kubernetes secret
            db_password = await self.get_secret("database-password")
            if db_password:
                credentials["password"] = db_password
            
            # Get database user from Kubernetes secret
            db_user = await self.get_secret("database-user", "psqladmin")
            credentials["user"] = db_user
            
            # Get database host from Kubernetes secret
            db_host = await self.get_secret("database-host", "mock-postgres-host.database.azure.com")
            credentials["host"] = db_host
            
            # Get database name from Kubernetes secret
            db_name = await self.get_secret("database-name", "carpeta_ciudadana")
            credentials["name"] = db_name
            
            return credentials
            
        except Exception as e:
            logger.error(f"❌ Error getting database credentials: {e}")
            return {}
    
    async def get_jwt_secrets(self) -> Dict[str, str]:
        """Get JWT signing secrets from Kubernetes Secrets."""
        try:
            secrets = {}
            
            # Get JWT secret key from Kubernetes secret
            jwt_secret = await self.get_secret("jwt-secret-key")
            if jwt_secret:
                secrets["secret_key"] = jwt_secret
            
            # Get JWT algorithm from Kubernetes secret
            jwt_algorithm = await self.get_secret("jwt-algorithm", "HS256")
            secrets["algorithm"] = jwt_algorithm
            
            return secrets
            
        except Exception as e:
            logger.error(f"❌ Error getting JWT secrets: {e}")
            return {}
    
    async def get_redis_credentials(self) -> Dict[str, str]:
        """Get Redis credentials from Kubernetes Secrets."""
        try:
            credentials = {}
            
            # Get Redis password from Kubernetes secret
            redis_password = await self.get_secret("redis-password")
            if redis_password:
                credentials["password"] = redis_password
            
            # Get Redis host from Kubernetes secret
            redis_host = await self.get_secret("redis-host", "localhost")
            credentials["host"] = redis_host
            
            # Get Redis port from Kubernetes secret
            redis_port = await self.get_secret("redis-port", "6379")
            credentials["port"] = redis_port
            
            return credentials
            
        except Exception as e:
            logger.error(f"❌ Error getting Redis credentials: {e}")
            return {}


class AzureADB2CService:
    """Azure AD B2C integration for authentication."""
    
    def __init__(self):
        self.tenant_name = config.azure_ad_b2c_tenant_name
        self.tenant_id = config.azure_ad_b2c_tenant_id
        self.client_id = config.azure_ad_b2c_client_id
        self._validate_config()
    
    def _validate_config(self):
        """Validate Azure AD B2C configuration."""
        try:
            if not self.tenant_name:
                logger.warning("Azure AD B2C tenant_name not configured")
                return False
            
            if not self.client_id:
                logger.warning("Azure AD B2C client_id not configured")
                return False
            
            logger.info(f"✅ Azure AD B2C configured: {self.tenant_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Azure AD B2C configuration error: {e}")
            return False
    
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """
        Generate Azure AD B2C authorization URL.
        
        Args:
            redirect_uri: Callback URL after authentication
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        try:
            if not self.tenant_name or not self.client_id:
                raise ValueError("Azure AD B2C not properly configured")
            
            # Build authorization URL
            base_url = f"https://{self.tenant_name}.b2clogin.com/{self.tenant_name}.onmicrosoft.com"
            policy = "B2C_1_signupsignin"  # Default policy
            
            params = {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": "openid profile email",
                "response_mode": "query"
            }
            
            if state:
                params["state"] = state
            
            # Build query string
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            auth_url = f"{base_url}/{policy}/oauth2/v2.0/authorize?{query_string}"
            
            logger.info(f"✅ Generated Azure AD B2C authorization URL")
            return auth_url
            
        except Exception as e:
            logger.error(f"❌ Error generating Azure AD B2C URL: {e}")
            raise
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Azure AD B2C
            redirect_uri: Callback URL used in authorization
            
        Returns:
            Token response or None if failed
        """
        try:
            if not self.tenant_name or not self.client_id:
                raise ValueError("Azure AD B2C not properly configured")
            
            import httpx
            
            # Azure AD B2C token endpoint
            token_url = f"https://{self.tenant_name}.b2clogin.com/{self.tenant_name}.onmicrosoft.com/B2C_1_signupsignin/oauth2/v2.0/token"
            
            # Prepare token request
            token_data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "code": code,
                "redirect_uri": redirect_uri,
                "scope": "openid profile email"
            }
            
            # Make HTTP request to Azure AD B2C
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    token_response = response.json()
                    logger.info(f"✅ Exchanged code for token with Azure AD B2C")
                    return token_response
                else:
                    logger.error(f"❌ Azure AD B2C token exchange failed: {response.status_code} - {response.text}")
                    return None
            
        except httpx.TimeoutException:
            logger.error("❌ Azure AD B2C token exchange timeout")
            return None
        except httpx.RequestError as e:
            logger.error(f"❌ Azure AD B2C token exchange request error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error exchanging code for token: {e}")
            return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from Azure AD B2C.
        
        Args:
            access_token: Valid access token
            
        Returns:
            User information or None if failed
        """
        try:
            if not access_token:
                raise ValueError("Access token required")
            
            import httpx
            
            # Azure AD B2C userinfo endpoint
            userinfo_url = f"https://{self.tenant_name}.b2clogin.com/{self.tenant_name}.onmicrosoft.com/B2C_1_signupsignin/openid/v2.0/userinfo"
            
            # Make HTTP request to Azure AD B2C userinfo endpoint
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    user_info = response.json()
                    logger.info(f"✅ Retrieved user info from Azure AD B2C")
                    return user_info
                else:
                    logger.error(f"❌ Azure AD B2C userinfo failed: {response.status_code} - {response.text}")
                    return None
            
        except httpx.TimeoutException:
            logger.error("❌ Azure AD B2C userinfo timeout")
            return None
        except httpx.RequestError as e:
            logger.error(f"❌ Azure AD B2C userinfo request error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error getting user info: {e}")
            return None


class AzureService:
    """Main Azure service integration with Kubernetes Secrets."""
    
    def __init__(self):
        self.kubernetes_secrets = KubernetesSecretsService()
        self.ad_b2c = AzureADB2CService()
    
    async def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration with Kubernetes Secrets integration."""
        try:
            # Get credentials from Kubernetes Secrets
            credentials = await self.kubernetes_secrets.get_database_credentials()
            
            # Merge with existing config
            db_config = {
                "host": credentials.get("host", config.database.host),
                "port": config.database.port,
                "name": credentials.get("name", config.database.name),
                "user": credentials.get("user", config.database.user),
                "password": credentials.get("password", config.database.password),
                "sslmode": config.database.sslmode
            }
            
            logger.info("✅ Database configuration retrieved with Kubernetes Secrets")
            return db_config
            
        except Exception as e:
            logger.error(f"❌ Error getting database config: {e}")
            # Fallback to default config
            return {
                "host": config.database.host,
                "port": config.database.port,
                "name": config.database.name,
                "user": config.database.user,
                "password": config.database.password,
                "sslmode": config.database.sslmode
            }
    
    async def get_jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration with Kubernetes Secrets integration."""
        try:
            # Get JWT secrets from Kubernetes Secrets
            secrets = await self.kubernetes_secrets.get_jwt_secrets()
            
            # Merge with existing config
            jwt_config = {
                "secret_key": secrets.get("secret_key", config.jwt_private_key_path),
                "algorithm": secrets.get("algorithm", config.jwt_algorithm),
                "expire_minutes": config.jwt_access_token_expire_minutes
            }
            
            logger.info("✅ JWT configuration retrieved with Kubernetes Secrets")
            return jwt_config
            
        except Exception as e:
            logger.error(f"❌ Error getting JWT config: {e}")
            # Fallback to default config
            return {
                "secret_key": config.jwt_private_key_path,
                "algorithm": config.jwt_algorithm,
                "expire_minutes": config.jwt_access_token_expire_minutes
            }
    
    async def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration with Kubernetes Secrets integration."""
        try:
            # Get Redis credentials from Kubernetes Secrets
            credentials = await self.kubernetes_secrets.get_redis_credentials()
            
            # Merge with existing config
            redis_config = {
                "host": credentials.get("host", config.redis.host),
                "port": int(credentials.get("port", config.redis.port)),
                "password": credentials.get("password", config.redis.password),
                "db": config.redis.db,
                "decode_responses": config.redis.decode_responses
            }
            
            logger.info("✅ Redis configuration retrieved with Kubernetes Secrets")
            return redis_config
            
        except Exception as e:
            logger.error(f"❌ Error getting Redis config: {e}")
            # Fallback to default config
            return {
                "host": config.redis.host,
                "port": config.redis.port,
                "password": config.redis.password,
                "db": config.redis.db,
                "decode_responses": config.redis.decode_responses
            }
    
    def is_kubernetes_available(self) -> bool:
        """Check if Kubernetes secrets are available."""
        return os.path.exists(self.kubernetes_secrets.secrets_mount_path)
    
    def is_azure_b2c_available(self) -> bool:
        """Check if Azure AD B2C is properly configured."""
        return bool(self.ad_b2c.tenant_name and self.ad_b2c.client_id)


# Global Azure service instance
azure_service = AzureService()
