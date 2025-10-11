"""AWS client utilities."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from carpeta_shared.config import AWSConfig

logger = logging.getLogger(__name__)


class S3Client:
    """S3 client for document storage."""

    def __init__(self, config: AWSConfig) -> None:
        """Initialize S3 client."""
        self.config = config
        self.client = boto3.client(
            "s3",
            region_name=config.region,
            config=Config(signature_version="s3v4"),
        )

    def generate_presigned_put(
        self, key: str, content_type: str, expires_in: int = 3600
    ) -> dict[str, Any]:
        """Generate presigned URL for uploading."""
        try:
            url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.config.s3_bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            return {"url": url, "key": key, "bucket": self.config.s3_bucket}
        except ClientError as e:
            logger.error(f"Error generating presigned PUT URL: {e}")
            raise

    def generate_presigned_get(self, key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for downloading."""
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.config.s3_bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned GET URL: {e}")
            raise

    def delete_object(self, key: str) -> None:
        """Delete object from S3."""
        try:
            self.client.delete_object(Bucket=self.config.s3_bucket, Key=key)
            logger.info(f"Deleted object: {key}")
        except ClientError as e:
            logger.error(f"Error deleting object {key}: {e}")
            raise

    def get_object_metadata(self, key: str) -> dict[str, Any]:
        """Get object metadata."""
        try:
            response = self.client.head_object(Bucket=self.config.s3_bucket, Key=key)
            return {
                "size": response["ContentLength"],
                "content_type": response["ContentType"],
                "etag": response["ETag"].strip('"'),
                "last_modified": response["LastModified"],
            }
        except ClientError as e:
            logger.error(f"Error getting metadata for {key}: {e}")
            raise

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """Calculate SHA-256 hash."""
        return hashlib.sha256(data).hexdigest()


class SQSClient:
    """SQS client for event messaging."""

    def __init__(self, config: AWSConfig) -> None:
        """Initialize SQS client."""
        self.config = config
        self.client = boto3.client("sqs", region_name=config.region)

    def send_message(
        self, message_body: str, message_attributes: dict[str, Any] | None = None
    ) -> str:
        """Send message to SQS queue."""
        try:
            params: dict[str, Any] = {
                "QueueUrl": self.config.sqs_queue_url,
                "MessageBody": message_body,
            }
            if message_attributes:
                params["MessageAttributes"] = message_attributes

            response = self.client.send_message(**params)
            return response["MessageId"]
        except ClientError as e:
            logger.error(f"Error sending SQS message: {e}")
            raise

    def receive_messages(
        self, max_messages: int = 10, wait_time_seconds: int = 20
    ) -> list[dict[str, Any]]:
        """Receive messages from SQS queue."""
        try:
            response = self.client.receive_message(
                QueueUrl=self.config.sqs_queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time_seconds,
                MessageAttributeNames=["All"],
            )
            return response.get("Messages", [])
        except ClientError as e:
            logger.error(f"Error receiving SQS messages: {e}")
            raise

    def delete_message(self, receipt_handle: str) -> None:
        """Delete message from queue."""
        try:
            self.client.delete_message(
                QueueUrl=self.config.sqs_queue_url, ReceiptHandle=receipt_handle
            )
        except ClientError as e:
            logger.error(f"Error deleting SQS message: {e}")
            raise


class SNSClient:
    """SNS client for event publishing."""

    def __init__(self, config: AWSConfig) -> None:
        """Initialize SNS client."""
        self.config = config
        self.client = boto3.client("sns", region_name=config.region)

    def publish(
        self, message: str, subject: str | None = None, attributes: dict[str, Any] | None = None
    ) -> str:
        """Publish message to SNS topic."""
        try:
            params: dict[str, Any] = {
                "TopicArn": self.config.sns_topic_arn,
                "Message": message,
            }
            if subject:
                params["Subject"] = subject
            if attributes:
                params["MessageAttributes"] = attributes

            response = self.client.publish(**params)
            return response["MessageId"]
        except ClientError as e:
            logger.error(f"Error publishing to SNS: {e}")
            raise


class CognitoClient:
    """Cognito client for user management."""

    def __init__(self, config: AWSConfig) -> None:
        """Initialize Cognito client."""
        self.config = config
        self.client = boto3.client("cognito-idp", region_name=config.region)

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify JWT token."""
        # In production, use AWS Cognito JWT verification
        # For now, this is a placeholder
        try:
            response = self.client.get_user(AccessToken=token)
            return {
                "username": response["Username"],
                "attributes": {
                    attr["Name"]: attr["Value"] for attr in response["UserAttributes"]
                },
            }
        except ClientError as e:
            logger.error(f"Error verifying token: {e}")
            raise

