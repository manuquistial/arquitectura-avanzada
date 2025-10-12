"""Notification service - handles email and webhook notifications."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import Settings

logger = logging.getLogger(__name__)


class Notifier:
    """Handles email and webhook notifications with retries."""
    
    def __init__(self, settings: Settings):
        """Initialize notifier.
        
        Args:
            settings: Service settings
        """
        self.settings = settings
        
        # Initialize Jinja2 for templates
        self.jinja_env = Environment(
            loader=FileSystemLoader("app/templates"),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Metrics (OpenTelemetry)
        self._init_metrics()
    
    def _init_metrics(self):
        """Initialize OpenTelemetry metrics."""
        if not self.settings.otel_enabled:
            return
        
        try:
            from opentelemetry import metrics
            meter = metrics.get_meter(__name__)
            
            self.notification_counter = meter.create_counter(
                name="notification_sent_total",
                description="Total notifications sent",
                unit="1"
            )
            
            self.notification_failed_counter = meter.create_counter(
                name="notification_failed_total",
                description="Total notifications failed",
                unit="1"
            )
            
            self.notification_latency = meter.create_histogram(
                name="notification_latency_seconds",
                description="Notification delivery latency",
                unit="s"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize metrics: {e}")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email notification.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            template_name: Template file name (e.g., 'document_authenticated.html')
            context: Template context variables
            
        Returns:
            Result dict with status and details
        """
        start_time = datetime.utcnow()
        
        try:
            # Render template
            template = self.jinja_env.get_template(template_name)
            html_body = template.render(**context)
            
            if self.settings.smtp_enabled:
                # Send real email
                result = await self._send_smtp_email(to_email, subject, html_body)
            else:
                # Console output (mock)
                result = self._log_email_console(to_email, subject, html_body)
            
            # Record metrics
            if self.settings.otel_enabled:
                try:
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    self.notification_counter.add(1, {"type": "email", "status": "success"})
                    self.notification_latency.record(duration, {"type": "email"})
                except:
                    pass
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            
            if self.settings.otel_enabled:
                try:
                    self.notification_failed_counter.add(1, {"type": "email"})
                except:
                    pass
            
            return {
                "success": False,
                "error": str(e),
                "sent_at": None
            }
    
    async def _send_smtp_email(self, to_email: str, subject: str, html_body: str) -> Dict[str, Any]:
        """Send email via SMTP."""
        import aiosmtplib
        from email.message import EmailMessage
        
        message = EmailMessage()
        message["From"] = f"{self.settings.smtp_from_name} <{self.settings.smtp_from_email}>"
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(html_body, subtype="html")
        
        await aiosmtplib.send(
            message,
            hostname=self.settings.smtp_host,
            port=self.settings.smtp_port,
            username=self.settings.smtp_username or None,
            password=self.settings.smtp_password or None,
            use_tls=self.settings.smtp_use_tls
        )
        
        logger.info(f"✅ Email sent to {to_email}")
        return {
            "success": True,
            "sent_at": datetime.utcnow().isoformat(),
            "method": "smtp"
        }
    
    def _log_email_console(self, to_email: str, subject: str, html_body: str) -> Dict[str, Any]:
        """Log email to console (mock mode)."""
        logger.info(
            f"\n"
            f"📧 [MOCK EMAIL]\n"
            f"To: {to_email}\n"
            f"Subject: {subject}\n"
            f"Body (first 200 chars): {html_body[:200]}...\n"
        )
        
        return {
            "success": True,
            "sent_at": datetime.utcnow().isoformat(),
            "method": "console"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def send_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send webhook notification with retries.
        
        Args:
            event_type: Event type for webhook
            payload: Webhook payload
            
        Returns:
            Result dict with status and response
        """
        if not self.settings.webhook_enabled or not self.settings.webhook_url:
            logger.info(f"📨 [MOCK WEBHOOK] Type: {event_type} | Payload: {payload}")
            return {
                "success": True,
                "sent_at": datetime.utcnow().isoformat(),
                "method": "console"
            }
        
        start_time = datetime.utcnow()
        
        try:
            async with httpx.AsyncClient(timeout=self.settings.webhook_timeout) as client:
                response = await client.post(
                    self.settings.webhook_url,
                    json={
                        "event_type": event_type,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": payload
                    },
                    headers={
                        "Content-Type": "application/json",
                        "X-Event-Type": event_type
                    }
                )
                
                response.raise_for_status()
                
                logger.info(f"✅ Webhook sent: {event_type} → {self.settings.webhook_url}")
                
                # Record metrics
                if self.settings.otel_enabled:
                    try:
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        self.notification_counter.add(1, {"type": "webhook", "status": "success"})
                        self.notification_latency.record(duration, {"type": "webhook"})
                    except:
                        pass
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": response.text,
                    "sent_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            
            if self.settings.otel_enabled:
                try:
                    self.notification_failed_counter.add(1, {"type": "webhook"})
                except:
                    pass
            
            raise  # Re-raise for tenacity retry

