"""Azure Service Bus integration for transfer service."""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
    from azure.core.exceptions import AzureError
    AZURE_SERVICEBUS_AVAILABLE = True
except ImportError:
    AZURE_SERVICEBUS_AVAILABLE = False
    logging.warning("Azure Service Bus libraries not available. Running in local mode.")

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AzureServiceBusService:
    """Azure Service Bus service with fallback to local logging."""
    
    def __init__(self):
        self.client = None
        self.is_available = False
        
        if AZURE_SERVICEBUS_AVAILABLE and settings.servicebus_enabled:
            try:
                self._initialize_client()
                self.is_available = True
                logger.info("Azure Service Bus client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Service Bus: {e}")
                self.is_available = False
        else:
            logger.info("Azure Service Bus not configured, using local fallback")
    
    def _initialize_client(self):
        """Initialize Azure Service Bus client."""
        if settings.servicebus_connection_string:
            self.client = ServiceBusClient.from_connection_string(
                settings.servicebus_connection_string
            )
        else:
            raise ValueError("Azure Service Bus not configured")
    
    async def send_transfer_notification(
        self,
        transfer_id: str,
        citizen_id: int,
        status: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send transfer notification to Service Bus."""
        try:
            if not self.is_available:
                return await self._local_notification(transfer_id, citizen_id, status, message, metadata)
            
            # Create message
            notification_data = {
                "transfer_id": transfer_id,
                "citizen_id": citizen_id,
                "status": status,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            # Send to Service Bus queue
            with self.client.get_queue_sender(queue_name="transfer-notifications") as sender:
                message_obj = ServiceBusMessage(
                    json.dumps(notification_data),
                    content_type="application/json"
                )
                sender.send_messages(message_obj)
            
            logger.info(f"Transfer notification sent for {transfer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Service Bus notification: {e}")
            # Fallback to local notification
            return await self._local_notification(transfer_id, citizen_id, status, message, metadata)
    
    async def _local_notification(
        self,
        transfer_id: str,
        citizen_id: int,
        status: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Local notification fallback."""
        notification_data = {
            "transfer_id": transfer_id,
            "citizen_id": citizen_id,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        logger.info(f"LOCAL NOTIFICATION: {json.dumps(notification_data, indent=2)}")
        return True
    
    async def send_document_processed_event(
        self,
        document_id: str,
        citizen_id: int,
        processing_status: str,
        file_size: int,
        sha256_hash: str
    ) -> bool:
        """Send document processed event."""
        try:
            if not self.is_available:
                return await self._local_document_event(
                    document_id, citizen_id, processing_status, file_size, sha256_hash
                )
            
            event_data = {
                "event_type": "document_processed",
                "document_id": document_id,
                "citizen_id": citizen_id,
                "processing_status": processing_status,
                "file_size": file_size,
                "sha256_hash": sha256_hash,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            with self.client.get_queue_sender(queue_name="document-events") as sender:
                message_obj = ServiceBusMessage(
                    json.dumps(event_data),
                    content_type="application/json"
                )
                sender.send_messages(message_obj)
            
            logger.info(f"Document processed event sent for {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send document event: {e}")
            return await self._local_document_event(
                document_id, citizen_id, processing_status, file_size, sha256_hash
            )
    
    async def _local_document_event(
        self,
        document_id: str,
        citizen_id: int,
        processing_status: str,
        file_size: int,
        sha256_hash: str
    ) -> bool:
        """Local document event fallback."""
        event_data = {
            "event_type": "document_processed",
            "document_id": document_id,
            "citizen_id": citizen_id,
            "processing_status": processing_status,
            "file_size": file_size,
            "sha256_hash": sha256_hash,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"LOCAL DOCUMENT EVENT: {json.dumps(event_data, indent=2)}")
        return True


# Global instance
azure_servicebus = AzureServiceBusService()
