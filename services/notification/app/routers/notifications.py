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


# In-memory notification store (use Redis in production)
notification_store: Dict[str, Dict[str, Any]] = {}


@router.get("/")
async def list_notifications(
    citizen_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[Dict[str, Any]]:
    """List notifications for a citizen."""
    logger.info(f"Listing notifications for citizen {citizen_id}")
    
    # Filter notifications by citizen_id
    citizen_notifications = []
    for notification_id, notification in notification_store.items():
        if notification.get('citizen_id') == citizen_id:
            citizen_notifications.append({
                "id": notification_id,
                "type": notification.get('type', 'system'),
                "title": notification.get('title', 'Notification'),
                "message": notification.get('message', ''),
                "is_read": notification.get('is_read', False),
                "created_at": notification.get('created_at', datetime.utcnow().isoformat()),
                "action_url": notification.get('action_url'),
                "metadata": notification.get('metadata', {}),
            })
    
    # Sort by created_at descending
    citizen_notifications.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Apply pagination
    return citizen_notifications[offset:offset + limit]


@router.patch("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    citizen_id: str = None,
) -> Dict[str, Any]:
    """Mark a notification as read."""
    logger.info(f"Marking notification {notification_id} as read")
    
    if notification_id not in notification_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification = notification_store[notification_id]
    
    # Update notification status
    notification['is_read'] = True
    notification['read_at'] = datetime.utcnow().isoformat()
    
    logger.info(f"Notification {notification_id} marked as read")
    
    return {
        "message": "Notification marked as read",
        "notification_id": notification_id
    }


@router.post("/create")
async def create_notification(
    notification_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a new notification."""
    logger.info("Creating new notification")
    
    try:
        # Extract notification data
        citizen_id = notification_data.get('citizen_id')
        notification_type = notification_data.get('type', 'system')
        title = notification_data.get('title', 'Notification')
        message = notification_data.get('message', '')
        action_url = notification_data.get('action_url')
        metadata = notification_data.get('metadata', {})
        
        if not citizen_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="citizen_id is required"
            )
        
        # Generate notification ID
        import uuid
        notification_id = str(uuid.uuid4())
        
        # Create notification record
        notification_record = {
            "id": notification_id,
            "citizen_id": citizen_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "is_read": False,
            "created_at": datetime.utcnow().isoformat(),
            "action_url": action_url,
            "metadata": metadata,
        }
        
        # Store notification
        notification_store[notification_id] = notification_record
        
        logger.info(f"Notification {notification_id} created successfully")
        
        return {
            "message": "Notification created successfully",
            "notification_id": notification_id,
            "notification": notification_record
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create notification"
        )


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    citizen_id: str = None,
) -> Dict[str, Any]:
    """Delete a notification."""
    logger.info(f"Deleting notification {notification_id}")
    
    if notification_id not in notification_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Check if notification belongs to citizen
    notification = notification_store[notification_id]
    if citizen_id and notification.get('citizen_id') != citizen_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Notification does not belong to citizen"
        )
    
    # Delete notification
    del notification_store[notification_id]
    
    logger.info(f"Notification {notification_id} deleted")
    
    return {
        "message": "Notification deleted successfully",
        "notification_id": notification_id
    }

