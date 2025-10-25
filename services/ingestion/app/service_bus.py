"""Azure Service Bus client for event publishing."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from app.config import get_config

logger = logging.getLogger(__name__)


class ServiceBusEventPublisher:
    """Azure Service Bus event publisher for document events."""
    
    def __init__(self):
        """Initialize Service Bus client."""
        self.config = get_config()
        self.connection_string = self.config.servicebus_connection_string
        self.queue_name = "document-events"  # Standardized queue name
        self.enabled = self.config.servicebus_enabled and bool(self.connection_string)
        
        if not self.enabled:
            logger.warning("Service Bus not configured - events will not be published")
    
    async def publish_document_uploaded(
        self,
        document_id: str,
        citizen_id: str,
        filename: str,
        content_type: str,
        blob_name: str,
        size_bytes: Optional[int] = None
    ) -> bool:
        """Publish document uploaded event to Service Bus."""
        if not self.enabled:
            logger.debug("Service Bus not enabled, skipping document.uploaded event")
            return False
        
        event = {
            "event_type": "document.uploaded",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "document_id": document_id,
                "citizen_id": citizen_id,
                "filename": filename,
                "content_type": content_type,
                "blob_name": blob_name,
                "size_bytes": size_bytes,
                "source": "ingestion-service"
            }
        }
        
        return await self._publish_event(event, document_id, citizen_id)
    
    async def publish_document_deleted(
        self,
        document_id: str,
        citizen_id: str
    ) -> bool:
        """Publish document deleted event to Service Bus."""
        if not self.enabled:
            logger.debug("Service Bus not enabled, skipping document.deleted event")
            return False
        
        event = {
            "event_type": "document.deleted",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "document_id": document_id,
                "citizen_id": citizen_id,
                "source": "ingestion-service"
            }
        }
        
        return await self._publish_event(event, document_id, citizen_id)
    
    async def publish_document_signed(
        self,
        document_id: str,
        citizen_id: str,
        signature_data: Dict[str, Any]
    ) -> bool:
        """Publish document signed event to Service Bus."""
        if not self.enabled:
            logger.debug("Service Bus not enabled, skipping document.signed event")
            return False
        
        event = {
            "event_type": "document.signed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "document_id": document_id,
                "citizen_id": citizen_id,
                "signature_data": signature_data,
                "source": "ingestion-service"
            }
        }
        
        return await self._publish_event(event, document_id, citizen_id)
    
    async def _publish_event(
        self,
        event: Dict[str, Any],
        document_id: str,
        citizen_id: str
    ) -> bool:
        """Publish event to Service Bus queue."""
        try:
            async with ServiceBusClient.from_connection_string(self.connection_string) as client:
                async with client.get_queue_sender(queue_name=self.queue_name) as sender:
                    message = ServiceBusMessage(
                        body=json.dumps(event).encode('utf-8'),
                        content_type="application/json",
                        subject=event["event_type"]
                    )
                    
                    message.application_properties = {
                        "event_type": event["event_type"],
                        "document_id": document_id,
                        "citizen_id": citizen_id,
                        "source": "ingestion-service"
                    }
                    
                    await sender.send_messages(message)
                    logger.info(f"Published {event['event_type']} event for document {document_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to publish {event['event_type']} event: {e}")
            return False


# Global instance
service_bus_publisher = ServiceBusEventPublisher()
