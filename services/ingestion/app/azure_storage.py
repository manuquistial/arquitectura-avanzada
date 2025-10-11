"""Azure Blob Storage client for document storage."""

import hashlib
import logging
from datetime import datetime, timedelta
from uuid import uuid4

from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    generate_blob_sas,
)

logger = logging.getLogger(__name__)


class AzureBlobDocumentClient:
    """Azure Blob Storage client for document storage with presigned URLs."""

    def __init__(
        self,
        account_name: str,
        account_key: str,
        container_name: str,
        connection_string: str | None = None,
    ) -> None:
        """Initialize Azure Blob client."""
        self.account_name = account_name
        self.account_key = account_key
        self.container_name = container_name
        
        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )
        else:
            account_url = f"https://{account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=DefaultAzureCredential()
            )

    def generate_presigned_put(
        self,
        citizen_id: int,
        filename: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> dict[str, str]:
        """Generate presigned URL for uploading a document.

        Returns:
        {
            "upload_url": "https://...",
            "document_id": "uuid",
            "blob_name": "citizens/{citizen_id}/documents/{uuid}/{filename}"
        }
        """
        doc_id = str(uuid4())
        blob_name = f"citizens/{citizen_id}/documents/{doc_id}/{filename}"

        try:
            # Generate SAS token for write
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=self.account_key,
                permission=BlobSasPermissions(write=True, create=True),
                expiry=datetime.utcnow() + timedelta(seconds=expires_in),
                content_type=content_type,
            )
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
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
        expires_in: int = 3600,
    ) -> str:
        """Generate presigned URL for downloading a document."""
        try:
            # Generate SAS token for read
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=expires_in),
            )
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
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

