"""Service Bus event consumer for notifications."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.services.notifier import Notifier
from app.models import DeliveryLog

logger = logging.getLogger(__name__)


class NotificationConsumer:
    """Consumes events and sends notifications."""
    
    def __init__(self, settings: Settings, db_session_factory):
        """Initialize consumer.
        
        Args:
            settings: Service settings
            db_session_factory: SQLAlchemy session factory
        """
        self.settings = settings
        self.db_session_factory = db_session_factory
        self.notifier = Notifier(settings)
        self.bus_client = None
        
        # Initialize Service Bus
        try:
            from carpeta_common.bus import ServiceBusClient
            self.bus_client = ServiceBusClient(settings.servicebus_connection_string)
        except ImportError:
            logger.warning("Service Bus client not available")
    
    async def start_consumers(self):
        """Start all notification consumers."""
        if not self.bus_client:
            logger.warning("Service Bus not initialized, consumers not started")
            return
        
        logger.info("🚀 Starting notification consumers...")
        
        await asyncio.gather(
            self._consume_document_authenticated(),
            self._consume_transfer_confirmed(),
            return_exceptions=True
        )
    
    async def _consume_document_authenticated(self):
        """Consume document.authenticated events."""
        logger.info("📭 Starting consumer: document-authenticated")
        
        await self.bus_client.consume_queue(
            queue_name="document-authenticated",
            handler=self._handle_document_authenticated,
            max_messages=10
        )
    
    async def _consume_transfer_confirmed(self):
        """Consume transfer.confirmed events."""
        logger.info("📭 Starting consumer: transfer-confirmed")
        
        await self.bus_client.consume_queue(
            queue_name="transfer-confirmed",
            handler=self._handle_transfer_confirmed,
            max_messages=10
        )
    
    async def _handle_document_authenticated(self, event: Dict[str, Any]):
        """Handle document.authenticated event."""
        try:
            data = event.get("data", {})
            event_id = event.get("event_id")
            
            logger.info(f"📧 Sending document authenticated notification for event {event_id}")
            
            # TODO: Get citizen email from database
            citizen_email = "citizen@example.com"  # Mock
            citizen_name = "Juan Pérez"  # Mock
            
            # Send email
            email_result = await self.notifier.send_email(
                to_email=citizen_email,
                subject="Documento Autenticado - Carpeta Ciudadana",
                template_name="document_authenticated.html",
                context={
                    "citizen_name": citizen_name,
                    "document_id": data.get("document_id"),
                    "document_title": data.get("document_title", "Documento"),
                    "sha256_hash": data.get("sha256_hash", ""),
                    "authenticated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                    "dashboard_url": "https://carpeta.example.com/dashboard"
                }
            )
            
            # Send webhook
            webhook_result = await self.notifier.send_webhook(
                event_type="document.authenticated",
                payload=data
            )
            
            # Log delivery
            await self._log_delivery(event_id, "document.authenticated", "email", citizen_email, email_result)
            await self._log_delivery(event_id, "document.authenticated", "webhook", self.settings.webhook_url, webhook_result)
            
            logger.info(f"✅ Notifications sent for event {event_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle document.authenticated: {e}")
            raise  # Re-raise for DLQ
    
    async def _handle_transfer_confirmed(self, event: Dict[str, Any]):
        """Handle transfer.confirmed event."""
        try:
            data = event.get("data", {})
            event_id = event.get("event_id")
            
            logger.info(f"📧 Sending transfer confirmed notification for event {event_id}")
            
            # TODO: Get citizen info from database
            citizen_email = "citizen@example.com"
            citizen_name = "Juan Pérez"
            
            # Send email
            email_result = await self.notifier.send_email(
                to_email=citizen_email,
                subject="Transferencia Completada - Carpeta Ciudadana",
                template_name="transfer_confirmed.html",
                context={
                    "citizen_name": citizen_name,
                    "transfer_id": data.get("transfer_id"),
                    "source_operator": "Operador A",  # TODO: Get from DB
                    "destination_operator": "Operador B",  # TODO: Get from DB
                    "success": data.get("success", False),
                    "error_message": data.get("error", ""),
                    "confirmed_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M")
                }
            )
            
            # Send webhook
            webhook_result = await self.notifier.send_webhook(
                event_type="transfer.confirmed",
                payload=data
            )
            
            # Log delivery
            await self._log_delivery(event_id, "transfer.confirmed", "email", citizen_email, email_result)
            await self._log_delivery(event_id, "transfer.confirmed", "webhook", self.settings.webhook_url, webhook_result)
            
            logger.info(f"✅ Notifications sent for event {event_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle transfer.confirmed: {e}")
            raise
    
    async def _log_delivery(
        self,
        event_id: str,
        event_type: str,
        notification_type: str,
        recipient: str,
        result: Dict[str, Any]
    ):
        """Log notification delivery to database."""
        try:
            async with self.db_session_factory() as session:
                log = DeliveryLog(
                    event_id=event_id,
                    event_type=event_type,
                    notification_type=notification_type,
                    recipient=recipient,
                    status="sent" if result.get("success") else "failed",
                    response_status_code=result.get("status_code"),
                    response_body=result.get("response", "")[:1000],  # Limit size
                    error_message=result.get("error"),
                    sent_at=datetime.utcnow() if result.get("success") else None,
                    failed_at=None if result.get("success") else datetime.utcnow(),
                    metadata=result
                )
                
                session.add(log)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to log delivery: {e}")

