"""Event processors for notification operations."""

import json
import logging
import uuid
from typing import Dict, Any

from sqlalchemy import text

from app.config import get_config
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

config = get_config()


class NotificationEventProcessor:
    """Processes citizen and notification events."""
    
    async def process_citizen_registered(self, event_data: Dict[str, Any]) -> bool:
        """Process citizen.registered event."""
        try:
            data = event_data.get("data", {})
            citizen_id = str(data.get("citizen_id") or "")
            email = data.get("email")
            name = data.get("name") or ""
            
            logger.info(
                f"👤 Processing citizen.registered: citizen_id={citizen_id}, "
                f"email={email}, name={name}"
            )
            
            # Create notification entry
            title = "Bienvenido a Carpeta Ciudadana"
            message = f"Hola {name or 'ciudadano'}, tu registro se completó correctamente."
            await self._save_notification(
                citizen_id=citizen_id,
                event_type="citizen.registered",
                title=title,
                message=message,
                metadata=data
            )
            
            # 1. Send welcome email (if SMTP enabled)
            if config.smtp_enabled and email:
                try:
                    await self._send_welcome_email(email, name, citizen_id)
                    logger.info(f"✅ Welcome email sent to {email}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to send welcome email: {e}")
                    # Don't fail the entire process if email fails
            else:
                logger.info("📧 Email not configured, skipping welcome email")
            
            logger.info(
                f"✅ Successfully processed citizen.registered: "
                f"citizen_id={citizen_id}, email={email}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing citizen.registered: {e}", exc_info=True)
            return False
    
    async def process_document_signed(self, event_data: Dict[str, Any]) -> bool:
        """Process document.signed event (notification)."""
        try:
            data = event_data.get("data", {})
            document_id = data.get("document_id")
            citizen_id = str(data.get("citizen_id") or "")
            
            logger.info(
                f"✍️  Processing document.signed notification: document_id={document_id}, "
                f"citizen_id={citizen_id}"
            )
            
            title = "Documento firmado correctamente"
            message = f"El documento {document_id} ha sido firmado exitosamente."
            await self._save_notification(
                citizen_id=citizen_id,
                event_type="document.signed",
                title=title,
                message=message,
                metadata=data
            )
            
            logger.info(
                f"✅ Successfully processed document.signed notification: "
                f"document_id={document_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing document.signed: {e}", exc_info=True)
            return False
    
    async def _save_notification(
        self,
        citizen_id: str,
        event_type: str,
        title: str,
        message: str,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        """Persist notification event in database."""
        if not citizen_id:
            logger.warning("⚠️  Missing citizen_id for notification, skipping storage")
            return
        
        metadata_json = json.dumps(metadata or {})
        notification_id = str(uuid.uuid4())
        
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text("""
                        INSERT INTO notifications (
                            id, citizen_id, event_type, title, message, metadata
                        )
                        VALUES (
                            :id, :citizen_id, :event_type, :title, :message,
                            CASE WHEN :metadata IS NULL OR :metadata = '' THEN NULL ELSE CAST(:metadata AS JSONB) END
                        )
                    """),
                    {
                        "id": notification_id,
                        "citizen_id": citizen_id,
                        "event_type": event_type,
                        "title": title,
                        "message": message,
                        "metadata": metadata_json if metadata else None,
                    },
                )
        logger.info(f"📝 Notification stored: id={notification_id}, citizen_id={citizen_id}")
    
    async def _send_welcome_email(self, email: str, name: str, citizen_id: str) -> None:
        """Send welcome email to newly registered citizen (mock)."""
        # TODO: Implement actual email sending when SMTP is configured
        logger.info(
            f"📧 [MOCK] Welcome email would be sent to {email} "
            f"(Name: {name or 'ciudadano'}, Citizen ID: {citizen_id})"
        )

