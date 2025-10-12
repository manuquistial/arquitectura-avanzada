"""Event publishing service (mock Service Bus)."""

import logging
import json
from datetime import datetime
from typing import Dict, Any
from app.config import Settings

logger = logging.getLogger(__name__)

class EventService:
    """Handles event publishing to Service Bus."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = settings.service_bus_enabled
    
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
        """Publish event (mock or Service Bus)."""
        if not self.enabled:
            logger.info(f"📨 [MOCK EVENT] {event['event_type']}: {json.dumps(event['data'])}")
            return
        
        # TODO: Implement Azure Service Bus publishing
        logger.info(f"📨 Publishing to Service Bus: {event['event_type']}")
