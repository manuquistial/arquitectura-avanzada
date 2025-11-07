"""Event processors for notification operations."""

import logging
from typing import Dict, Any
import httpx

from app.config import get_config

logger = logging.getLogger(__name__)

config = get_config()


class NotificationEventProcessor:
    """Processes citizen and notification events."""
    
    async def process_citizen_registered(self, event_data: Dict[str, Any]) -> bool:
        """Process citizen.registered event.
        
        Args:
            event_data: Event data with 'event_type', 'data', 'timestamp', etc.
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            data = event_data.get("data", {})
            citizen_id = data.get("citizen_id")
            email = data.get("email")
            name = data.get("name")
            
            logger.info(
                f"👤 Processing citizen.registered: citizen_id={citizen_id}, "
                f"email={email}, name={name}"
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
                logger.info(f"📧 Email not configured, skipping welcome email for {email}")
            
            # 2. Create initial profile/preferences (if needed)
            # TODO: Future enhancement - crear perfil inicial con preferencias
            
            # 3. Log notification sent
            logger.info(
                f"✅ Successfully processed citizen.registered: "
                f"citizen_id={citizen_id}, email={email}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing citizen.registered: {e}", exc_info=True)
            return False
    
    async def process_document_signed(self, event_data: Dict[str, Any]) -> bool:
        """Process document.signed event (notification).
        
        Args:
            event_data: Event data with 'event_type', 'data', 'timestamp', etc.
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            data = event_data.get("data", {})
            document_id = data.get("document_id")
            citizen_id = data.get("citizen_id")
            
            logger.info(
                f"✍️  Processing document.signed notification: document_id={document_id}, "
                f"citizen_id={citizen_id}"
            )
            
            # TODO: Future enhancement - enviar notificación al ciudadano
            # 1. Obtener email del ciudadano
            # 2. Enviar email de notificación de firma
            
            logger.info(
                f"✅ Successfully processed document.signed notification: "
                f"document_id={document_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing document.signed: {e}", exc_info=True)
            return False
    
    async def _send_welcome_email(self, email: str, name: str, citizen_id: str) -> None:
        """Send welcome email to newly registered citizen.
        
        Args:
            email: Citizen email address
            name: Citizen name
            citizen_id: Citizen ID
        """
        # TODO: Implement actual email sending when SMTP is configured
        # For now, just log
        logger.info(
            f"📧 [MOCK] Welcome email would be sent to {email} "
            f"(Name: {name}, Citizen ID: {citizen_id})"
        )
        
        # Future implementation:
        # if config.smtp_enabled and config.smtp_host:
        #     import smtplib
        #     from email.mime.text import MIMEText
        #     # Send email using SMTP
        #     pass

