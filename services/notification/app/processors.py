"""Event processors for notification operations."""

import logging
import uuid
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB

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
            if config.mailjet_enabled and email:
                try:
                    await self._send_welcome_email(email, name, citizen_id)
                    logger.info(f"✅ Welcome email sent to {email}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to send welcome email: {e}")
                    # Don't fail the entire process if email fails
            elif config.smtp_enabled and email:
                logger.info("📧 SMTP enabled but Mailjet disabled; SMTP implementation pending")
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
            sha256_hash = data.get("sha256_hash")
            email = data.get("email")
            name = data.get("name") or ""
            
            logger.info(
                f"✍️  Processing document.signed notification: document_id={document_id}, "
                f"citizen_id={citizen_id}"
            )
            
            # Enrich with citizen profile if email/name missing
            if citizen_id and (not email or not name):
                citizen = await self._get_citizen_profile(citizen_id)
                email = email or citizen.get("email")
                name = name or citizen.get("name") or ""
            
            title = "Documento firmado correctamente"
            message = f"El documento {document_id} ha sido firmado exitosamente."
            await self._save_notification(
                citizen_id=citizen_id,
                event_type="document.signed",
                title=title,
                message=message,
                metadata=data
            )
            
            if config.mailjet_enabled and email:
                try:
                    await self._send_document_signed_email(
                        email=email,
                        name=name,
                        citizen_id=citizen_id,
                        document_id=str(document_id or ""),
                        sha256_hash=sha256_hash,
                    )
                    logger.info(f"✅ Document signed email sent to {email}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to send document signed email: {e}")
            elif config.smtp_enabled and email:
                logger.info("📧 SMTP enabled but Mailjet disabled; SMTP implementation pending")
            else:
                logger.info("📧 Email not configured for document.signed, skipping email")
            
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
        
        metadata_payload = metadata or None
        notification_id = str(uuid.uuid4())
        
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt = text("""
                        INSERT INTO notifications (
                            id, citizen_id, event_type, title, message, metadata
                        )
                        VALUES (
                        :id, :citizen_id, :event_type, :title, :message, :metadata
                        )
                """).bindparams(bindparam("metadata", type_=JSONB))
                await session.execute(
                    stmt,
                    {
                        "id": notification_id,
                        "citizen_id": citizen_id,
                        "event_type": event_type,
                        "title": title,
                        "message": message,
                        "metadata": metadata_payload,
                    },
                )
        logger.info(f"📝 Notification stored: id={notification_id}, citizen_id={citizen_id}")
    
    async def _send_welcome_email(self, email: str, name: str, citizen_id: str) -> None:
        """Send welcome email to newly registered citizen using Mailjet."""
        full_name = name or "ciudadano"
        await self._send_mailjet_message(
            email=email,
            name=full_name,
            subject="Bienvenido a Carpeta Ciudadana",
            text_body=f"Hola {full_name}, tu registro en Carpeta Ciudadana se completó correctamente.",
            html_body=(
                f"<h3>Hola {full_name},</h3>"
                "<p>Tu registro en <strong>Carpeta Ciudadana</strong> se completó correctamente.</p>"
                "<p>Ya puedes ingresar y aprovechar todos los servicios disponibles.</p>"
                "<p>Saludos,<br/>Equipo Carpeta Ciudadana</p>"
            ),
            custom_id=citizen_id or str(uuid.uuid4()),
            template_id=config.mailjet_template_id,
            template_variables={
                "fullName": full_name,
                "citizenId": citizen_id,
            } if config.mailjet_template_id else None,
        )

    async def _send_document_signed_email(
        self,
        *,
        email: str,
        name: str,
        citizen_id: str,
        document_id: str,
        sha256_hash: Optional[str],
    ) -> None:
        """Send confirmation email when a document is signed."""
        display_name = name or "ciudadano"
        html_body = (
            f"<h3>Hola {display_name},</h3>"
            f"<p>El documento <strong>{document_id}</strong> ha sido firmado correctamente.</p>"
            "<p>Puedes consultarlo en la Carpeta Ciudadana cuando lo necesites.</p>"
        )
        if sha256_hash:
            html_body += (
                "<p>"
                "Huella digital (SHA-256): "
                f"<code>{sha256_hash}</code>"
                "</p>"
            )
        html_body += "<p>Saludos,<br/>Equipo Carpeta Ciudadana</p>"

        text_body = (
            f"Hola {display_name}, el documento {document_id} ha sido firmado correctamente "
            "en Carpeta Ciudadana."
        )
        if sha256_hash:
            text_body += f" Huella digital: {sha256_hash}"

        await self._send_mailjet_message(
            email=email,
            name=display_name,
            subject="Documento firmado correctamente",
            text_body=text_body,
            html_body=html_body,
            custom_id=f"document-signed-{document_id or uuid.uuid4()}",
            template_id=None,
            template_variables=None,
        )

    async def _send_mailjet_message(
        self,
        *,
        email: str,
        name: str,
        subject: str,
        text_body: str,
        html_body: str,
        custom_id: str,
        template_id: Optional[int],
        template_variables: Optional[Dict[str, Any]],
    ) -> None:
        """Generic Mailjet sender helper."""
        if not config.mailjet_enabled:
            logger.debug("Mailjet disabled; skipping email send")
            return

        required = {
            "MAILJET_API_KEY": config.mailjet_api_key,
            "MAILJET_SECRET_KEY": config.mailjet_secret_key,
            "MAILJET_FROM_EMAIL": config.mailjet_from_email,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Missing Mailjet configuration values: {', '.join(missing)}")

        payload: Dict[str, Any] = {
            "Messages": [
                {
                    "From": {
                        "Email": config.mailjet_from_email,
                        "Name": config.mailjet_from_name or "Carpeta Ciudadana",
                    },
                    "To": [
                        {
                            "Email": email,
                            "Name": name or "ciudadano",
                        }
                    ],
                    "Subject": subject,
                    "TextPart": text_body,
                    "HTMLPart": html_body,
                    "CustomID": custom_id,
                }
            ]
        }

        if template_id:
            payload["Messages"][0]["TemplateID"] = template_id
            payload["Messages"][0]["TemplateLanguage"] = True
            if template_variables:
                payload["Messages"][0]["Variables"] = template_variables

        auth = (config.mailjet_api_key, config.mailjet_secret_key)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.mailjet.com/v3.1/send",
                json=payload,
                auth=auth,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            raise RuntimeError(f"Mailjet request failed: {exc.response.status_code} {body}") from exc

        data = response.json()
        status = (
            data.get("Messages", [{}])[0]
            .get("Status", "unknown")
            .lower()
        )
        if status != "success":
            raise RuntimeError(f"Mailjet returned non-success status: {status}")

    async def _get_citizen_profile(self, citizen_id: str) -> Dict[str, Optional[str]]:
        """Fetch citizen details (name, email) from database."""
        if not citizen_id:
            return {}

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT name, email
                    FROM citizens
                    WHERE CAST(id AS TEXT) = CAST(:citizen_id AS TEXT)
                    LIMIT 1
                """),
                {"citizen_id": citizen_id},
            )
            row = result.fetchone()

        if not row:
            return {}

        mapping = row._mapping if hasattr(row, "_mapping") else None
        if mapping:
            return {
                "name": mapping.get("name"),
                "email": mapping.get("email"),
            }

        # Fallback for tuple-like rows
        return {
            "name": row[0] if len(row) > 0 else None,
            "email": row[1] if len(row) > 1 else None,
        }

