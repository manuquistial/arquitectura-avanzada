"""Sanitization and PII protection layer for MinTIC hub calls.

Since hub is public, we must:
- Minimize PII exposure
- Validate and sanitize all inputs
- Audit what is sent
- Mask sensitive data in logs
"""

import logging
import re
from typing import Any, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class DataSanitizer:
    """Sanitizes data before sending to MinTIC hub."""
    
    @staticmethod
    def sanitize_citizen_id(citizen_id: Any) -> int:
        """Validate and sanitize citizen ID.
        
        Args:
            citizen_id: Citizen ID (int or string)
            
        Returns:
            Validated integer ID
            
        Raises:
            ValueError: If ID is invalid
        """
        # Convert to string and remove whitespace
        id_str = str(citizen_id).strip()
        
        # Remove any non-digits
        id_str = re.sub(r'\D', '', id_str)
        
        # Validate length (must be exactly 10 digits)
        if len(id_str) != 10:
            raise ValueError(f"Citizen ID must be 10 digits, got {len(id_str)}")
        
        # Convert to int
        try:
            return int(id_str)
        except ValueError:
            raise ValueError(f"Invalid citizen ID: {citizen_id}")
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Validate and sanitize email.
        
        Args:
            email: Email address
            
        Returns:
            Sanitized email
            
        Raises:
            ValueError: If email is invalid
        """
        email = email.strip().lower()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError(f"Invalid email format: {email}")
        
        return email
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """Sanitize string field.
        
        Args:
            value: String value
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string (trimmed, limited)
        """
        if not value:
            return ""
        
        # Trim whitespace
        sanitized = value.strip()
        
        # Remove extra spaces
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Truncate if too long
        if len(sanitized) > max_length:
            logger.warning(f"⚠️  String truncated from {len(sanitized)} to {max_length} chars")
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def minimize_address(address: str, required: bool = True) -> str:
        """Minimize address PII.
        
        Only send full address if strictly required by hub.
        Otherwise, send city/region only.
        
        Args:
            address: Full address
            required: If False, return only city
            
        Returns:
            Full address or minimized version
        """
        if not required:
            # Extract only city (last part after comma)
            parts = address.split(',')
            city = parts[-1].strip() if parts else address.strip()
            logger.info(f"ℹ️  Address minimized: {DataSanitizer.mask_pii(address)} → {city}")
            return city
        
        # If required, sanitize but keep full
        return DataSanitizer.sanitize_string(address, max_length=200)
    
    @staticmethod
    def mask_pii(value: str, show_chars: int = 4) -> str:
        """Mask PII for logging.
        
        Args:
            value: Sensitive value
            show_chars: Number of chars to show at end
            
        Returns:
            Masked value (e.g., "***4567")
        """
        if not value or len(value) <= show_chars:
            return "***"
        
        return "***" + value[-show_chars:]
    
    @staticmethod
    def sanitize_register_citizen(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize citizen registration data.
        
        Args:
            data: Raw citizen data
            
        Returns:
            Sanitized data safe to send to hub
        """
        sanitized = {
            "id": DataSanitizer.sanitize_citizen_id(data.get("id")),
            "name": DataSanitizer.sanitize_string(data.get("name", ""), max_length=100),
            "email": DataSanitizer.sanitize_email(data.get("email", "")),
            "operatorId": DataSanitizer.sanitize_string(data.get("operatorId", ""), max_length=50),
            "operatorName": DataSanitizer.sanitize_string(data.get("operatorName", ""), max_length=100),
        }
        
        # Address - minimize if not strictly required
        # Hub seems to require address, so we keep it but sanitize
        if "address" in data:
            sanitized["address"] = DataSanitizer.sanitize_string(data["address"], max_length=200)
        
        # Remove any extra fields (minimize data sent to public hub)
        # Only send what hub requires
        
        return sanitized
    
    @staticmethod
    def sanitize_authenticate_document(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize document authentication data.
        
        Args:
            data: Raw document data
            
        Returns:
            Sanitized data (minimal: citizen_id, URL, title)
        """
        sanitized = {
            "idCitizen": DataSanitizer.sanitize_citizen_id(data.get("idCitizen")),
            "UrlDocument": data.get("UrlDocument", "").strip(),
            "documentTitle": DataSanitizer.sanitize_string(data.get("documentTitle", ""), max_length=100),
        }
        
        # Only send these 3 fields - NO additional PII
        # NO send: citizen name, email, address, document content
        
        return sanitized


class AuditLogger:
    """Audit logger for hub calls (what we sent to public hub)."""
    
    @staticmethod
    async def log_hub_call(
        operation: str,
        sanitized_payload: Dict[str, Any],
        response_status: int,
        response_message: str
    ):
        """Log hub call for audit trail.
        
        Args:
            operation: Operation name (e.g., "registerCitizen")
            sanitized_payload: Sanitized data sent to hub
            response_status: HTTP status code
            response_message: Response message
        """
        # Mask sensitive fields for logging
        masked_payload = {}
        for key, value in sanitized_payload.items():
            if key in ['email', 'address', 'UrlDocument']:
                masked_payload[key] = DataSanitizer.mask_pii(str(value))
            elif key in ['id', 'idCitizen']:
                # Mask except last 4 digits
                masked_payload[key] = DataSanitizer.mask_pii(str(value), show_chars=4)
            else:
                masked_payload[key] = value
        
        # Log to audit trail
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "hub": "MinTIC",
            "payload_sent": masked_payload,
            "response_status": response_status,
            "response_message": response_message[:100]  # Truncate long messages
        }
        
        logger.info(f"📋 AUDIT: {operation} → status={response_status}, payload={masked_payload}")
        
        # TODO: Save to audit_logs table in DB for compliance
        # await db.save(AuditLog(**audit_entry))
    
    @staticmethod
    def log_pii_exposure(operation: str, fields_sent: list[str]):
        """Log what PII fields were sent to public hub.
        
        Args:
            operation: Operation name
            fields_sent: List of field names sent
        """
        pii_fields = [f for f in fields_sent if f in ['email', 'address', 'phone', 'id']]
        
        if pii_fields:
            logger.warning(
                f"⚠️  PII EXPOSURE: Operation {operation} sent PII to public hub: {pii_fields}"
            )

