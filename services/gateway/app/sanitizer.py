"""
Data sanitization utilities for gateway.

Sanitizes data before sending to external services (MinTIC Hub)
to prevent PII leakage and ensure data quality.
"""

import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# PII patterns to redact in logs
PII_PATTERNS = [
    (re.compile(r'\b\d{6,}\b'), '[REDACTED_ID]'),  # IDs largos
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[REDACTED_EMAIL]'),  # Emails
    (re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'), '[REDACTED_PHONE]'),  # Teléfonos
    (re.compile(r'\b\d{9,12}\b'), '[REDACTED_DOCUMENT]'),  # Números de documento
]


def sanitize_for_hub(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize data before sending to MinTIC Hub.
    
    - Trim whitespace
    - Validate email format
    - Remove unnecessary PII
    - Limit string lengths
    
    Args:
        data: Dictionary with hub payload
        
    Returns:
        Sanitized dictionary
    """
    sanitized = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            # Trim whitespace
            value = value.strip()
            
            # Validate email if field looks like email
            if key.lower().endswith('email') or '@' in value:
                value = validate_email(value)
            
            # Limit string length to prevent oversized payloads
            max_length = 500 if key.lower() in ('description', 'notes') else 200
            if len(value) > max_length:
                value = value[:max_length]
                logger.warning(f"Truncated field {key} to {max_length} chars")
            
        sanitized[key] = value
    
    return sanitized


def validate_email(email: str) -> str:
    """
    Validate email format.
    
    Args:
        email: Email string to validate
        
    Returns:
        Validated email or empty string if invalid
    """
    email = email.strip().lower()
    
    # Basic email regex
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    if email_pattern.match(email):
        return email
    else:
        logger.warning(f"Invalid email format detected, removing: {email[:20]}...")
        return ""


def remove_pii_fields(data: Dict[str, Any], fields_to_remove: list[str]) -> Dict[str, Any]:
    """
    Remove PII fields that are not required for hub.
    
    Args:
        data: Dictionary with data
        fields_to_remove: List of field names to remove
        
    Returns:
        Dictionary without PII fields
    """
    return {k: v for k, v in data.items() if k not in fields_to_remove}


def truncate_for_logging(message: str, max_length: int = 200) -> str:
    """
    Truncate message for logging and redact PII.
    
    Args:
        message: Message to truncate
        max_length: Maximum length (default: 200)
        
    Returns:
        Truncated and sanitized message
    """
    # Redact PII patterns
    sanitized = message
    for pattern, replacement in PII_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    
    # Truncate
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize data for logging (redact PII).
    
    Args:
        data: Dictionary to log
        
    Returns:
        Sanitized dictionary safe for logging
    """
    sanitized = {}
    
    for key, value in data.items():
        # Skip sensitive fields entirely
        if key.lower() in ('password', 'token', 'secret', 'key', 'authorization'):
            sanitized[key] = '[REDACTED]'
            continue
        
        if isinstance(value, str):
            # Redact PII in string values
            sanitized_value = value
            for pattern, replacement in PII_PATTERNS:
                sanitized_value = pattern.sub(replacement, sanitized_value)
            
            # Truncate long strings
            if len(sanitized_value) > 200:
                sanitized_value = sanitized_value[:200] + "..."
            
            sanitized[key] = sanitized_value
        elif isinstance(value, dict):
            # Recursively sanitize nested dicts
            sanitized[key] = sanitize_log_data(value)
        elif isinstance(value, list):
            # Limit list size in logs
            if len(value) > 5:
                sanitized[key] = value[:5] + ["..."]
            else:
                sanitized[key] = value
        else:
            sanitized[key] = value
    
    return sanitized


def sanitize_hub_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize complete hub payload.
    
    - Removes unnecessary PII
    - Validates required fields
    - Trims strings
    - Validates formats
    
    Args:
        payload: Hub API payload
        
    Returns:
        Sanitized payload ready for hub
    """
    # Fields that hub doesn't need (PII protection)
    unnecessary_fields = [
        'fullAddress',  # Hub no necesita dirección completa
        'phoneNumber',  # Hub no necesita teléfono
        'personalEmail',  # Solo email oficial si es necesario
    ]
    
    # Remove unnecessary fields
    sanitized = remove_pii_fields(payload, unnecessary_fields)
    
    # Sanitize remaining fields
    sanitized = sanitize_for_hub(sanitized)
    
    logger.info(f"Sanitized hub payload: {truncate_for_logging(str(sanitized))}")
    
    return sanitized

