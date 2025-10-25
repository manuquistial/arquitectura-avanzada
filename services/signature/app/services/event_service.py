"""Event publishing service (mock Service Bus)."""

import logging
import json
from datetime import datetime
from typing import Dict, Any
from app.config import get_config

logger = logging.getLogger(__name__)

class EventService:
    """Handles event publishing to Service Bus."""
    
    def __init__(self, config):
        self.config = config
        self.enabled = config.servicebus_enabled
    
    async def publish_document_signed(
        self,
        document_id: str,
        citizen_id: int,
        sha256_hash: str
    ):
        """Publish document.signed event."""
        event = {
            "event_type": "document.signed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "document_id": document_id,
                "citizen_id": citizen_id,
                "sha256_hash": sha256_hash
            }
        }
        await self._publish(event)
    
    async def publish_document_verified(
        self,
        document_id: str,
        is_valid: bool
    ):
        """Publish document.verified event."""
        event = {
            "event_type": "document.verified",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "document_id": document_id,
                "is_valid": is_valid
            }
        }
        await self._publish(event)
    
    async def publish_document_authenticated(
        self,
        document_id: str,
        citizen_id: int,
        success: bool
    ):
        """Publish document.hubAuthenticated event."""
        event = {
            "event_type": "document.hubAuthenticated",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "document_id": document_id,
                "citizen_id": citizen_id,
                "success": success
            }
        }
        await self._publish(event)
    
    async def _publish(self, event: Dict[str, Any]):
        """Publish event (Service Bus or fallback)."""
        if not self.enabled:
            logger.info(f"📨 [FALLBACK EVENT] {event['event_type']}: {json.dumps(event['data'])}")
            return
        
        try:
            # Use Azure Service Bus client
            from azure.servicebus import ServiceBusClient, ServiceBusMessage
            from azure.servicebus.exceptions import ServiceBusError
            
            # Get connection string from environment
            connection_string = self.config.servicebus_connection_string
            if not connection_string:
                logger.warning("Service Bus connection string not configured, using mock")
                logger.info(f"📨 [MOCK EVENT] {event['event_type']}: {json.dumps(event['data'])}")
                return
            
            # Create Service Bus client with timeout
            async with ServiceBusClient.from_connection_string(
                connection_string, 
                retry_total=3,
                retry_backoff_factor=0.8,
                retry_backoff_max=120
            ) as client:
                # Get queue name from event type
                queue_name = self._get_queue_name(event['event_type'])
                
                # Create sender with timeout
                async with client.get_queue_sender(queue_name=queue_name) as sender:
                    # Create message
                    message = ServiceBusMessage(
                        body=json.dumps(event).encode('utf-8'),
                        content_type="application/json",
                        subject=event['event_type']
                    )
                    
                    # Add custom properties
                    message.application_properties = {
                        "event_type": event['event_type'],
                        "timestamp": event.get('timestamp', datetime.utcnow().isoformat()),
                        "source": "signature-service"
                    }
                    
                    # Send message with timeout
                    await sender.send_messages(message)
                    
                    logger.info(f"📨 Published to Service Bus queue '{queue_name}': {event['event_type']}")
                    
        except ServiceBusError as e:
            logger.error(f"❌ Azure Service Bus error publishing event: {e}")
            # Fallback to mock
            logger.info(f"📨 [FALLBACK MOCK] {event['event_type']}: {json.dumps(event['data'])}")
        except ConnectionError as e:
            logger.error(f"❌ Connection error to Service Bus: {e}")
            # Fallback to mock
            logger.info(f"📨 [FALLBACK MOCK] {event['event_type']}: {json.dumps(event['data'])}")
        except TimeoutError as e:
            logger.error(f"❌ Timeout error to Service Bus: {e}")
            # Fallback to mock
            logger.info(f"📨 [FALLBACK MOCK] {event['event_type']}: {json.dumps(event['data'])}")
        except Exception as e:
            logger.error(f"❌ Unexpected error publishing to Service Bus: {e}")
            # Fallback to mock
            logger.info(f"📨 [FALLBACK MOCK] {event['event_type']}: {json.dumps(event['data'])}")

    def _get_queue_name(self, event_type: str) -> str:
        """Get queue name based on event type."""
        # Map event types to standardized queue names
        queue_mapping = {
            "document.signed": "document-events",
            "document.authenticated": "document-events", 
            "signature.completed": "signature-events",
            "signature.failed": "signature-events"
        }
        
        return queue_mapping.get(event_type, "general-events")
