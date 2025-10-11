"""S3 client for document storage."""

import hashlib
import logging
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3DocumentClient:
    """S3 client for document storage with presigned URLs."""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
    ) -> None:
        """Initialize S3 client."""
        self.bucket = bucket
        self.region = region
        self.client = boto3.client(
            "s3",
            region_name=region,
            config=Config(signature_version="s3v4"),
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
            "s3_key": "citizens/{citizen_id}/documents/{uuid}/{filename}"
        }
        """
        doc_id = str(uuid4())
        s3_key = f"citizens/{citizen_id}/documents/{doc_id}/{filename}"

        try:
            url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": s3_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )

            return {
                "upload_url": url,
                "document_id": doc_id,
                "s3_key": s3_key,
            }
        except ClientError as e:
            logger.error(f"Error generating presigned PUT URL: {e}")
            raise

    def generate_presigned_get(
        self,
        s3_key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate presigned URL for downloading a document."""
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": s3_key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned GET URL: {e}")
            raise

    def get_object_metadata(self, s3_key: str) -> dict[str, any]:
        """Get object metadata from S3."""
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return {
                "size": response["ContentLength"],
                "content_type": response.get("ContentType"),
                "etag": response["ETag"].strip('"'),
                "last_modified": response["LastModified"],
            }
        except ClientError as e:
            logger.error(f"Error getting metadata for {s3_key}: {e}")
            raise

    def delete_object(self, s3_key: str) -> None:
        """Delete object from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"Deleted object: {s3_key}")
        except ClientError as e:
            logger.error(f"Error deleting object {s3_key}: {e}")
            raise

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """Calculate SHA-256 hash."""
        return hashlib.sha256(data).hexdigest()

