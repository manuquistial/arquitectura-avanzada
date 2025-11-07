"""Event publishing service (mock Service Bus)."""

import logging
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from carpeta_common.bus import ServiceBusClient as CommonServiceBusClient  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


class EventService:
    """Handles event publishing to Service Bus."""

    def __init__(self, config) -> None:
        self.config = config
        self.enabled = bool(config.servicebus_enabled)
        self._bus_client: Optional["CommonServiceBusClient"] = None

    async def publish_document_signed(
        self,
        document_id: str,
        citizen_id: int,
        sha256_hash: str,
    ):
        """Publish document.signed event."""
        event = {
            "event_type": "document.signed",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "document_id": document_id,
                "citizen_id": citizen_id,
                "sha256_hash": sha256_hash,
            },
        }
        await self._publish(event)

    async def publish_document_verified(
        self,
        document_id: str,
        is_valid: bool,
    ):
        """Publish document.verified event."""
        event = {
            "event_type": "document.verified",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "document_id": document_id,
                "is_valid": is_valid,
            },
        }
        await self._publish(event)

    async def publish_document_authenticated(
        self,
        document_id: str,
        citizen_id: int,
        success: bool,
    ):
        """Publish document.hubAuthenticated event."""
        event = {
            "event_type": "document.hubAuthenticated",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "document_id": document_id,
                "citizen_id": citizen_id,
                "success": success,
            },
        }
        await self._publish(event)

    async def _publish(self, event: Dict[str, Any]):
        """Publish event (Service Bus or fallback)."""
        if not self.enabled:
            logger.info(
                f"📨 [FALLBACK EVENT] {event['event_type']}: {json.dumps(event['data'])}"
            )
            return

        connection_string = self.config.servicebus_connection_string
        if not connection_string:
            logger.warning("Service Bus connection string not configured, using mock")
            logger.info(
                f"📨 [MOCK EVENT] {event['event_type']}: {json.dumps(event['data'])}"
            )
            return

        queue_name = self._get_queue_name(event["event_type"])

        try:
            bus = self._get_bus_client(connection_string)
            await bus.publish_event(
                queue_name=queue_name,
                event_type=event["event_type"],
                data=event["data"],
            )
            logger.info(
                f"📨 Published to Service Bus queue '{queue_name}': {event['event_type']}"
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(f"❌ Error publishing to Service Bus: {exc}")
            logger.info(
                f"📨 [FALLBACK MOCK] {event['event_type']}: {json.dumps(event['data'])}"
            )

    def _get_bus_client(self, connection_string: str) -> "CommonServiceBusClient":
        """Return a cached Service Bus client, creating it if needed."""
        from carpeta_common.bus import ServiceBusClient as CommonServiceBusClient  # type: ignore[import-not-found]  # local import

        if not self._bus_client:
            self._bus_client = CommonServiceBusClient(connection_string=connection_string)
        return self._bus_client

    def _get_queue_name(self, event_type: str) -> str:
        """Get queue name based on event type."""
        queue_mapping = {
            "document.signed": "document-events",
            "document.verified": "document-events",
            "document.authenticated": "document-events",
            "document.hubAuthenticated": "document-events",
            "signature.completed": "signature-events",
            "signature.failed": "signature-events",
        }

        return queue_mapping.get(event_type, "general-events")
