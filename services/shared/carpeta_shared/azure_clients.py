"""Azure client utilities - Equivalentes a AWS boto3."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    generate_blob_sas,
    generate_container_sas,
    ContainerSasPermissions,
)
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient as AsyncServiceBusClient

from carpeta_shared.config import AzureConfig

logger = logging.getLogger(__name__)


class AzureBlobClient:
    """Azure Blob Storage client - Equivalente a S3Client."""

    def __init__(self, config: AzureConfig) -> None:
        """Initialize Blob Storage client."""
        self.config = config
        self.credential = DefaultAzureCredential()
        
        # Connection string o DefaultAzureCredential
        if config.storage_connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                config.storage_connection_string
            )
        else:
            account_url = f"https://{config.storage_account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=self.credential
            )
        
        self.container_name = config.storage_container_name

    def generate_presigned_put(
        self, key: str, content_type: str, expires_in: int = 3600
    ) -> dict[str, Any]:
        """Generate presigned URL for uploading - Equivalente a generate_presigned_url PUT."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=key
            )
            
            # Generar SAS token para upload (write)
            sas_token = generate_blob_sas(
                account_name=self.config.storage_account_name,
                container_name=self.container_name,
                blob_name=key,
                account_key=self.config.storage_account_key,
                permission=BlobSasPermissions(write=True, create=True),
                expiry=datetime.utcnow() + timedelta(seconds=expires_in)
            )
            
            url = f"{blob_client.url}?{sas_token}"
            
            return {
                "url": url,
                "key": key,
                "container": self.container_name,
            }
        except Exception as e:
            logger.error(f"Error generating presigned PUT URL: {e}")
            raise

    def generate_presigned_get(self, key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for downloading - Equivalente a generate_presigned_url GET."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=key
            )
            
            # Generar SAS token para download (read)
            sas_token = generate_blob_sas(
                account_name=self.config.storage_account_name,
                container_name=self.container_name,
                blob_name=key,
                account_key=self.config.storage_account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(seconds=expires_in)
            )
            
            url = f"{blob_client.url}?{sas_token}"
            return url
        except Exception as e:
            logger.error(f"Error generating presigned GET URL: {e}")
            raise

    def delete_object(self, key: str) -> None:
        """Delete blob from storage - Equivalente a delete_object."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=key
            )
            blob_client.delete_blob()
            logger.info(f"Deleted blob: {key}")
        except Exception as e:
            logger.error(f"Error deleting blob {key}: {e}")
            raise

    def get_object_metadata(self, key: str) -> dict[str, Any]:
        """Get blob metadata - Equivalente a head_object."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=key
            )
            properties = blob_client.get_blob_properties()
            
            return {
                "size": properties.size,
                "content_type": properties.content_settings.content_type,
                "etag": properties.etag,
                "last_modified": properties.last_modified,
            }
        except Exception as e:
            logger.error(f"Error getting metadata for {key}: {e}")
            raise

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """Calculate SHA-256 hash."""
        return hashlib.sha256(data).hexdigest()


class AzureServiceBusClient:
    """Azure Service Bus client - Equivalente a SQS/SNS."""

    def __init__(self, config: AzureConfig) -> None:
        """Initialize Service Bus client."""
        self.config = config
        
        if config.servicebus_connection_string:
            self.client = ServiceBusClient.from_connection_string(
                config.servicebus_connection_string
            )
        else:
            credential = DefaultAzureCredential()
            self.client = ServiceBusClient(
                fully_qualified_namespace=config.servicebus_namespace,
                credential=credential
            )

    def send_message(
        self, 
        queue_name: str,
        message_body: str,
        message_attributes: dict[str, Any] | None = None
    ) -> str:
        """Send message to queue - Equivalente a SQS send_message."""
        try:
            with self.client:
                sender = self.client.get_queue_sender(queue_name=queue_name)
                with sender:
                    message = ServiceBusMessage(
                        body=message_body,
                        application_properties=message_attributes or {}
                    )
                    sender.send_messages(message)
                    logger.info(f"Message sent to queue: {queue_name}")
                    return "success"  # Service Bus no retorna message ID directamente
        except Exception as e:
            logger.error(f"Error sending message to queue: {e}")
            raise

    def receive_messages(
        self, 
        queue_name: str,
        max_messages: int = 10,
        max_wait_time: int = 20
    ) -> list[dict[str, Any]]:
        """Receive messages from queue - Equivalente a SQS receive_messages."""
        try:
            messages = []
            with self.client:
                receiver = self.client.get_queue_receiver(queue_name=queue_name)
                with receiver:
                    received_msgs = receiver.receive_messages(
                        max_message_count=max_messages,
                        max_wait_time=max_wait_time
                    )
                    
                    for msg in received_msgs:
                        messages.append({
                            "Body": str(msg),
                            "MessageId": msg.message_id,
                            "ReceiptHandle": msg.lock_token,
                            "Attributes": msg.application_properties,
                        })
            
            return messages
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            raise

    def delete_message(self, queue_name: str, receipt_handle: str) -> None:
        """Delete message from queue - Equivalente a SQS delete_message."""
        try:
            with self.client:
                receiver = self.client.get_queue_receiver(queue_name=queue_name)
                with receiver:
                    receiver.complete_message(receipt_handle)
                    logger.info("Message deleted from queue")
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            raise

    def publish_to_topic(
        self,
        topic_name: str,
        message: str,
        subject: str | None = None,
        attributes: dict[str, Any] | None = None
    ) -> str:
        """Publish message to topic - Equivalente a SNS publish."""
        try:
            with self.client:
                sender = self.client.get_topic_sender(topic_name=topic_name)
                with sender:
                    msg = ServiceBusMessage(
                        body=message,
                        subject=subject,
                        application_properties=attributes or {}
                    )
                    sender.send_messages(msg)
                    logger.info(f"Message published to topic: {topic_name}")
                    return "success"
        except Exception as e:
            logger.error(f"Error publishing to topic: {e}")
            raise


class AzureKeyVaultClient:
    """Azure Key Vault client - Para certificados mTLS (equivalente a ACM PCA)."""

    def __init__(self, config: AzureConfig) -> None:
        """Initialize Key Vault client."""
        from azure.keyvault.certificates import CertificateClient
        from azure.keyvault.secrets import SecretClient
        
        self.config = config
        credential = DefaultAzureCredential()
        
        self.cert_client = CertificateClient(
            vault_url=config.keyvault_url,
            credential=credential
        )
        
        self.secret_client = SecretClient(
            vault_url=config.keyvault_url,
            credential=credential
        )

    def get_certificate(self, cert_name: str) -> tuple[bytes, bytes]:
        """Get certificate and private key."""
        try:
            # Get certificate
            certificate = self.cert_client.get_certificate(cert_name)
            
            # Get private key from secret
            secret = self.secret_client.get_secret(cert_name)
            
            cert_bytes = certificate.cer
            key_bytes = secret.value.encode()
            
            return cert_bytes, key_bytes
        except Exception as e:
            logger.error(f"Error getting certificate: {e}")
            raise

    def create_certificate(self, cert_name: str, subject: str) -> str:
        """Create a new certificate."""
        from azure.keyvault.certificates import CertificatePolicy
        
        try:
            policy = CertificatePolicy.get_default()
            policy.subject_name = subject
            
            operation = self.cert_client.begin_create_certificate(
                certificate_name=cert_name,
                policy=policy
            )
            
            certificate = operation.result()
            logger.info(f"Certificate created: {cert_name}")
            return certificate.id
        except Exception as e:
            logger.error(f"Error creating certificate: {e}")
            raise

