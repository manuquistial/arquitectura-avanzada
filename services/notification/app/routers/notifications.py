"""Notification API router."""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.config import Settings
from app.services.notifier import Notifier

logger = logging.getLogger(__name__)
router = APIRouter()

# Singleton
_settings = Settings()
_notifier = Notifier(_settings)


class TestNotificationRequest(BaseModel):
    """Test notification request."""
    email: EmailStr
    notification_type: str = "test"  # test, document_auth, transfer


@router.post("/test")
async def send_test_notification(request: TestNotificationRequest) -> Dict[str, Any]:
    """Send test notification.
    
    Useful for testing email/webhook configuration.
    """
    logger.info(f"Sending test notification to {request.email}")
    
    try:
        # Send test email
        email_result = await _notifier.send_email(
            to_email=request.email,
            subject="Test Notification - Carpeta Ciudadana",
            template_name="document_authenticated.html",  # Reuse template
            context={
                "citizen_name": "Usuario de Prueba",
                "document_id": "test-doc-123",
                "document_title": "Documento de Prueba",
                "sha256_hash": "abc123def456" * 4,  # Mock hash
                "authenticated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "dashboard_url": "https://carpeta.example.com/dashboard"
            }
        )
        
        # Send test webhook
        webhook_result = await _notifier.send_webhook(
            event_type="notification.test",
            payload={
                "test": True,
                "email": request.email,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return {
            "message": "Test notification sent",
            "email": email_result,
            "webhook": webhook_result
        }
        
    except Exception as e:
        logger.error(f"Test notification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get notification metrics."""
    # TODO: Return OpenTelemetry metrics
    return {
        "service": "notification",
        "status": "healthy",
        "smtp_enabled": _settings.smtp_enabled,
        "webhook_enabled": _settings.webhook_enabled,
        "webhook_url": _settings.webhook_url if _settings.webhook_url else "not configured"
    }

