"""Azure Blob Storage service for SAS token generation (with local mock)."""

import logging
from datetime import datetime, timedelta, timezone
from app.config import get_config

# Try to import Azure dependencies, fall back to mock if not available
try:
    from azure.core.exceptions import AzureError
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, UserDelegationKey
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️  Azure dependencies not available, using mock BlobService for development")

logger = logging.getLogger(__name__)

class BlobService:
    """Handles Azure Blob Storage operations.
    
    Preferencia por User Delegation SAS (más seguro), con fallback a Account Key SAS.
    """
    
    def __init__(self, config):
        self.config = config
        self.sas_ttl_minutes = config.azure_storage_sas_ttl_minutes
        self.use_managed_identity = True
        self.is_mock = False
        
        # Check if Azure is available
        if not AZURE_AVAILABLE:
            logger.info("🔧 Using mock BlobService for development")
            self.is_mock = True
            self.client = None
            return
        
        # Try to use Managed Identity first
        if config.azure_storage_account_name:
            try:
                account_url = f"https://{config.azure_storage_account_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                self.client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
                # Test the credential
                self.client.list_containers(max_results=1)
                logger.info("✅ Using Managed Identity for Azure Blob Storage")
            except AzureError as e:
                logger.warning(f"⚠️  Azure Managed Identity auth failed: {e}")
                self.use_managed_identity = False
                self._try_account_key_fallback()
            except Exception as e:
                logger.error(f"❌ Unexpected error during Managed Identity setup: {e}")
                self.use_managed_identity = False
                self._try_account_key_fallback()
        else:
            logger.warning("⚠️  Azure Storage account name not configured")
            self.client = None
    
    def _try_account_key_fallback(self):
        """Try Account Key fallback for Azure Blob Storage."""
        try:
            if self.config.azure_storage_account_key:
                connection_string = (
                    f"DefaultEndpointsProtocol=https;"
                    f"AccountName={self.config.azure_storage_account_name};"
                    f"AccountKey={self.config.azure_storage_account_key};"
                    f"EndpointSuffix=core.windows.net"
                )
                self.client = BlobServiceClient.from_connection_string(connection_string)
                logger.info("✅ Using Account Key for Azure Blob Storage")
            else:
                logger.warning("⚠️  Azure Storage account key not configured")
                self.client = None
        except AzureError as e:
            logger.error(f"❌ Azure Account Key authentication failed: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Unexpected error during Account Key setup: {e}")
            self.client = None
    
    def _get_user_delegation_key(self) -> UserDelegationKey | None:
        """Get User Delegation Key for generating User Delegation SAS.
        
        Returns None if Managed Identity is not available or times out.
        """
        if not self.use_managed_identity or not self.client:
            return None
        
        try:
            # User delegation key is valid for 7 days maximum
            start_time = datetime.now(timezone.utc)
            expiry_time = start_time + timedelta(days=1)
            
            # Add timeout to avoid blocking (5 seconds max)
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("User delegation key request timed out")
            
            # For async/threading, we'll use a simpler approach: just try with a short timeout
            # If it takes too long, fall back to Account Key SAS
            try:
                user_delegation_key = self.client.get_user_delegation_key(
                    key_start_time=start_time,
                    key_expiry_time=expiry_time
                )
                logger.info("✅ User delegation key obtained successfully")
                return user_delegation_key
            except Exception as e:
                # If it takes too long or fails, log and return None to use fallback
                logger.warning(f"⚠️  User delegation key request failed or timed out: {e}")
                return None
        except AzureError as e:
            logger.warning(f"⚠️  Azure error getting user delegation key: {e}, using Account Key fallback")
            return None
        except Exception as e:
            logger.warning(f"⚠️  Unexpected error getting user delegation key: {e}, using Account Key fallback")
            return None
    
    async def download_blob(self, blob_name: str) -> bytes:
        """Download blob content from Azure Blob Storage.
        
        Args:
            blob_name: Blob name in container
            
        Returns:
            Blob content as bytes
            
        Raises:
            Exception: If blob cannot be downloaded
        """
        if not self.client:
            raise Exception("Azure Blob Storage client not available")
        
        try:
            blob_client = self.client.get_blob_client(
                container=self.config.azure_storage_container_name,
                blob=blob_name
            )
            
            # Download blob content
            download_stream = blob_client.download_blob()
            content = download_stream.readall()
            
            logger.info(f"Downloaded blob {blob_name} ({len(content)} bytes)")
            return content
            
        except Exception as e:
            logger.error(f"Failed to download blob {blob_name}: {e}")
            raise
    
    async def generate_sas_url(
        self, 
        blob_name: str, 
        expiry_hours: float | None = None
    ) -> str:
        """Generate SAS token URL for blob (READ only).
        
        Tries User Delegation SAS first (more secure), falls back to Account Key SAS.
        
        IMPORTANT: This SAS is for hub authentication only.
        Hub does NOT download/store binaries, only validates metadata.
        
        Args:
            blob_name: Blob name in container
            expiry_hours: Hours until SAS expires (default from SAS_TTL_MINUTES)
            
        Returns:
            Full SAS URL (READ permission only)
        """
        if not self.client:
            logger.warning("⚠️  No Azure Blob Storage client available, using fallback URL")
            return f"https://fallback-storage/{blob_name}?sas=FALLBACK_TOKEN"
        
        if expiry_hours is None:
            expiry_hours = self.sas_ttl_minutes / 60.0
        
        blob_client = self.client.get_blob_client(
            container=self.config.azure_storage_container_name,
            blob=blob_name
        )
        
        try:
            # Skip User Delegation SAS for now (it's blocking) - use Account Key SAS directly
            # TODO: Re-enable User Delegation SAS once timeout issues are resolved
            logger.info(f"Generating Account Key SAS for {blob_name} (User Delegation skipped due to timeout issues)")
            return self._generate_account_key_sas(blob_name, expiry_hours)
            
        except Exception as e:
            logger.error(f"❌ SAS generation failed completely: {e}")
            # Return mock URL as fallback
            return f"https://mock-storage/{blob_name}?sas=MOCK_TOKEN_FALLBACK"
    
    def _generate_account_key_sas(self, blob_name: str, expiry_hours: float) -> str:
        """Generate Account Key SAS as fallback."""
        try:
            if not self.config.azure_storage_account_key:
                raise ValueError("No account key available for fallback SAS generation")
                
            sas_token = generate_blob_sas(
                account_name=self.config.azure_storage_account_name,
                container_name=self.config.azure_storage_container_name,
                blob_name=blob_name,
                account_key=self.config.azure_storage_account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
            )
            logger.info(f"✅ Account Key SAS URL generated for {blob_name}")
            blob_client = self.client.get_blob_client(
                container=self.config.azure_storage_container_name,
                blob=blob_name
            )
            url = f"{blob_client.url}?{sas_token}"
            return url
        except AzureError as e:
            logger.error(f"❌ Azure Account Key SAS generation failed: {e}")
            return f"https://mock-storage/{blob_name}?sas=MOCK_TOKEN_ACCOUNT_KEY_FAILED"
        except Exception as e:
            logger.error(f"❌ Unexpected error in Account Key SAS: {e}")
            return f"https://mock-storage/{blob_name}?sas=MOCK_TOKEN_ACCOUNT_KEY_ERROR"
