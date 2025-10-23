"""Azure Blob Storage client for document storage."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    generate_blob_sas,
    UserDelegationKey,
)

logger = logging.getLogger(__name__)


class AzureBlobDocumentClient:
    """Azure Blob Storage client for document storage with presigned URLs.
    
    Preferencia por User Delegation SAS (más seguro), con fallback a Account Key SAS.
    """

    def __init__(
        self,
        account_name: str,
        account_key: str | None = None,
        container_name: str = "documents",
        connection_string: str | None = None,
        sas_ttl_minutes: int = 15,
    ) -> None:
        """Initialize Azure Blob client.
        
        Args:
            account_name: Azure Storage account name
            account_key: Storage account key (optional, for fallback)
            container_name: Container name
            connection_string: Connection string (optional, for fallback)
            sas_ttl_minutes: SAS token TTL in minutes (default: 15)
        """
        self.account_name = account_name
        self.account_key = account_key
        self.container_name = container_name
        self.sas_ttl_minutes = sas_ttl_minutes
        self.use_managed_identity = True
        
        # Use account key directly for simplicity
        if account_key:
            account_url = f"https://{account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=account_key
            )
            self.use_managed_identity = False
            logger.info("Using account key for Azure Blob Storage")
        elif connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )
            self.use_managed_identity = False
            logger.info("Using connection string for Azure Blob Storage")
        else:
            # Try Managed Identity as last resort
            try:
                account_url = f"https://{account_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
                self.use_managed_identity = True
                logger.info("Using Managed Identity for Azure Blob Storage")
            except Exception as e:
                logger.error(f"All authentication methods failed: {e}")
                raise ValueError("No valid authentication method provided for Azure Blob Storage")
    
    def _get_user_delegation_key(self) -> UserDelegationKey | None:
        """Get User Delegation Key for generating User Delegation SAS.
        
        Returns None if Managed Identity is not available.
        """
        if not self.use_managed_identity:
            return None
        
        try:
            # User delegation key is valid for 7 days maximum
            start_time = datetime.now(timezone.utc)
            expiry_time = start_time + timedelta(days=1)
            
            user_delegation_key = self.blob_service_client.get_user_delegation_key(
                key_start_time=start_time,
                key_expiry_time=expiry_time
            )
            return user_delegation_key
        except AzureError as e:
            logger.error(f"Failed to get user delegation key: {e}")
            return None

    def generate_presigned_put(
        self,
        citizen_id: int,
        filename: str,
        content_type: str,
        expires_in: int | None = None,
    ) -> dict[str, str]:
        """Generate presigned URL for uploading a document.
        
        Tries User Delegation SAS first, falls back to Account Key SAS.

        Returns:
        {
            "upload_url": "https://...",
            "document_id": "uuid",
            "blob_name": "citizens/{citizen_id}/documents/{uuid}/{filename}"
        }
        """
        if expires_in is None:
            expires_in = self.sas_ttl_minutes * 60
            
        doc_id = str(uuid4())
        blob_name = f"citizens/{citizen_id}/documents/{doc_id}/{filename}"
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )

        try:
            # Try User Delegation SAS first (more secure)
            user_delegation_key = self._get_user_delegation_key()
            
            if user_delegation_key:
                start_time = datetime.now(timezone.utc)
                expiry_time = start_time + timedelta(seconds=expires_in)
                
                sas_token = blob_client.generate_sas(
                    user_delegation_key=user_delegation_key,
                    permission=BlobSasPermissions(write=True, create=True, add=True),
                    expiry=expiry_time,
                    start=start_time,
                    content_type=content_type,
                )
                logger.info(f"Generated User Delegation SAS for PUT: {blob_name}")
            else:
                # Fallback to Account Key SAS
                if not self.account_key:
                    raise ValueError("No account key available for fallback SAS generation")
                    
                sas_token = generate_blob_sas(
                    account_name=self.account_name,
                    container_name=self.container_name,
                    blob_name=blob_name,
                    account_key=self.account_key,
                    permission=BlobSasPermissions(write=True, create=True, add=True),
                    expiry=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
                    content_type=content_type,
                )
                logger.info(f"Generated Account Key SAS for PUT: {blob_name}")
            
            url = f"{blob_client.url}?{sas_token}"

            return {
                "upload_url": url,
                "document_id": doc_id,
                "blob_name": blob_name,
            }
        except Exception as e:
            logger.error(f"Error generating presigned PUT URL: {e}")
            raise

    def generate_presigned_get(
        self,
        blob_name: str,
        expires_in: int | None = None,
    ) -> str:
        """Generate presigned URL for downloading a document.
        
        Tries User Delegation SAS first, falls back to Account Key SAS.
        """
        if expires_in is None:
            expires_in = self.sas_ttl_minutes * 60
            
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        try:
            # Try User Delegation SAS first (more secure)
            user_delegation_key = self._get_user_delegation_key()
            
            if user_delegation_key:
                start_time = datetime.now(timezone.utc)
                expiry_time = start_time + timedelta(seconds=expires_in)
                
                sas_token = blob_client.generate_sas(
                    user_delegation_key=user_delegation_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=expiry_time,
                    start=start_time,
                )
                logger.info(f"Generated User Delegation SAS for GET: {blob_name}")
            else:
                # Fallback to Account Key SAS
                if not self.account_key:
                    raise ValueError("No account key available for fallback SAS generation")
                    
                sas_token = generate_blob_sas(
                    account_name=self.account_name,
                    container_name=self.container_name,
                    blob_name=blob_name,
                    account_key=self.account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
                )
                logger.info(f"Generated Account Key SAS for GET: {blob_name}")
            
            url = f"{blob_client.url}?{sas_token}"
            return url
        except Exception as e:
            logger.error(f"Error generating presigned GET URL: {e}")
            raise

    def get_blob_metadata(self, blob_name: str) -> dict[str, any]:
        """Get blob metadata."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            properties = blob_client.get_blob_properties()
            
            return {
                "size": properties.size,
                "content_type": properties.content_settings.content_type,
                "etag": properties.etag,
                "last_modified": properties.last_modified,
            }
        except Exception as e:
            logger.error(f"Error getting metadata for {blob_name}: {e}")
            raise

    def get_blob_properties(self, blob_name: str) -> dict[str, any] | None:
        """Get blob properties for hash verification."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            properties = blob_client.get_blob_properties()
            
            return {
                "size": properties.size,
                "content_type": properties.content_settings.content_type,
                "etag": properties.etag,
                "last_modified": properties.last_modified,
            }
        except Exception as e:
            logger.error(f"Error getting properties for {blob_name}: {e}")
            return None

    def delete_blob(self, blob_name: str) -> None:
        """Delete blob from storage."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.delete_blob()
            logger.info(f"Deleted blob: {blob_name}")
        except Exception as e:
            logger.error(f"Error deleting blob {blob_name}: {e}")
            raise

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """Calculate SHA-256 hash."""
        return hashlib.sha256(data).hexdigest()

