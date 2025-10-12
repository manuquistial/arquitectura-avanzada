"""ABAC client for authorization checks."""

import logging
import httpx
from typing import Optional

from app.config import Settings

logger = logging.getLogger(__name__)


class ABACClient:
    """Client for IAM ABAC authorization."""
    
    def __init__(self, settings: Settings):
        """Initialize ABAC client.
        
        Args:
            settings: Service settings
        """
        self.settings = settings
        self.iam_url = settings.iam_service_url
    
    async def authorize(
        self,
        subject: str,
        resource: str,
        action: str,
        context: Optional[dict] = None
    ) -> tuple[bool, str]:
        """Check authorization via IAM ABAC.
        
        Args:
            subject: User identifier (email or sub)
            resource: Resource identifier (e.g., "document:123")
            action: Action to perform (e.g., "share", "access")
            context: Additional context
            
        Returns:
            Tuple of (is_authorized, reason)
        """
        if not self.iam_url:
            logger.warning("⚠️  IAM service not configured, allowing by default")
            return (True, "IAM not configured")
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.iam_url}/authorize",
                    json={
                        "subject": subject,
                        "resource": resource,
                        "action": action,
                        "context": context or {}
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    allowed = data.get("allowed", False)
                    reason = data.get("reason", "")
                    
                    if allowed:
                        logger.info(f"✅ ABAC authorized: {subject} -> {action} on {resource}")
                    else:
                        logger.warning(f"❌ ABAC denied: {subject} -> {action} on {resource}: {reason}")
                    
                    return (allowed, reason)
                else:
                    logger.error(f"IAM service returned {response.status_code}")
                    return (False, f"IAM error: {response.status_code}")
                    
        except httpx.TimeoutException:
            logger.error("IAM service timeout")
            return (False, "IAM timeout")
        except Exception as e:
            logger.error(f"ABAC check failed: {e}")
            return (False, f"ABAC error: {str(e)}")

