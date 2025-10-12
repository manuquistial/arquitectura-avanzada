"""OpenTelemetry instrumentation helpers for MinTIC hub calls.

SECURITY:
- Truncate request/response bodies (max 200 chars)
- Never log tokens, passwords, or full PII
- Mask sensitive fields in attributes
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode, Span
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("⚠️  OpenTelemetry tracing not available")


class HubTelemetry:
    """OpenTelemetry instrumentation for MinTIC hub calls."""
    
    @staticmethod
    def truncate_body(body: Any, max_length: int = 200) -> str:
        """Truncate request/response body for logging.
        
        Args:
            body: Request or response body (dict, str, bytes)
            max_length: Maximum length to keep
            
        Returns:
            Truncated string representation
        """
        if body is None:
            return ""
        
        # Convert to string
        if isinstance(body, dict):
            body_str = json.dumps(body, ensure_ascii=False)
        elif isinstance(body, bytes):
            body_str = body.decode('utf-8', errors='replace')
        else:
            body_str = str(body)
        
        # Truncate
        if len(body_str) > max_length:
            return body_str[:max_length] + f"... ({len(body_str)} chars total)"
        
        return body_str
    
    @staticmethod
    def mask_sensitive_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive fields in data for telemetry.
        
        Args:
            data: Data dict to mask
            
        Returns:
            Dict with masked sensitive fields
        """
        masked = data.copy()
        
        sensitive_fields = [
            'email', 'address', 'phone', 'password', 'token',
            'UrlDocument', 'url', 'sas_token', 'access_key'
        ]
        
        for field in sensitive_fields:
            if field in masked:
                value = str(masked[field])
                if len(value) > 4:
                    masked[field] = f"***{value[-4:]}"
                else:
                    masked[field] = "***"
        
        # Mask citizen ID (show last 4 digits)
        for field in ['id', 'idCitizen', 'citizen_id']:
            if field in masked:
                value = str(masked[field])
                if len(value) > 4:
                    masked[field] = f"***{value[-4:]}"
        
        return masked
    
    @staticmethod
    def create_hub_span(
        tracer: Optional[Any],
        endpoint: str,
        method: str = "POST"
    ) -> Optional[Any]:
        """Create OpenTelemetry span for hub call.
        
        Args:
            tracer: OpenTelemetry tracer
            endpoint: Hub endpoint name (e.g., "registerCitizen")
            method: HTTP method
            
        Returns:
            Span context manager or None
        """
        if not OTEL_AVAILABLE or tracer is None:
            return None
        
        # Create span with semantic conventions
        span = tracer.start_span(
            name=f"hub.call",
            kind=trace.SpanKind.CLIENT
        )
        
        # Set standard attributes
        span.set_attribute("http.method", method)
        span.set_attribute("http.url", f"/apis/{endpoint}")
        span.set_attribute("hub.endpoint", endpoint)
        span.set_attribute("hub.provider", "MinTIC")
        span.set_attribute("service.name", "mintic_client")
        
        return span
    
    @staticmethod
    def record_hub_call(
        span: Optional[Any],
        endpoint: str,
        status_code: int,
        retry_count: int,
        cb_state: str,
        request_body: Optional[Dict] = None,
        response_body: Optional[str] = None,
        error: Optional[Exception] = None
    ):
        """Record hub call details in span.
        
        Args:
            span: OpenTelemetry span
            endpoint: Hub endpoint name
            status_code: HTTP status code (0 if network error)
            retry_count: Number of retries attempted
            cb_state: Circuit breaker state (CLOSED/OPEN/HALF_OPEN)
            request_body: Request payload (will be masked and truncated)
            response_body: Response text (will be truncated)
            error: Exception if call failed
        """
        if not OTEL_AVAILABLE or span is None:
            return
        
        # Set attributes
        span.set_attribute("hub.endpoint", endpoint)
        span.set_attribute("http.status_code", status_code)
        span.set_attribute("hub.retry_count", retry_count)
        span.set_attribute("hub.circuit_breaker_state", cb_state)
        
        # Determine success
        success = 200 <= status_code < 300
        span.set_attribute("hub.success", success)
        
        # Set span status
        if error:
            span.set_status(Status(StatusCode.ERROR, str(error)))
            span.record_exception(error)
        elif status_code >= 500:
            span.set_status(Status(StatusCode.ERROR, f"Server error: {status_code}"))
        elif status_code == 501:
            span.set_status(Status(StatusCode.ERROR, "Invalid parameters"))
        elif success:
            span.set_status(Status(StatusCode.OK))
        else:
            span.set_status(Status(StatusCode.ERROR, f"Client error: {status_code}"))
        
        # Add events with truncated bodies (NEVER full PII)
        if request_body:
            masked = HubTelemetry.mask_sensitive_fields(request_body)
            truncated = HubTelemetry.truncate_body(masked, max_length=200)
            span.add_event(
                "hub.request",
                attributes={
                    "request.body": truncated,
                    "request.size": len(json.dumps(request_body))
                }
            )
        
        if response_body:
            truncated = HubTelemetry.truncate_body(response_body, max_length=200)
            span.add_event(
                "hub.response",
                attributes={
                    "response.body": truncated,
                    "response.size": len(response_body)
                }
            )
        
        # Special markers for specific status codes
        if status_code == 204:
            span.set_attribute("hub.response_type", "no_content")
        elif status_code == 501:
            span.set_attribute("hub.response_type", "invalid_parameters")
        elif status_code == 202:
            span.set_attribute("hub.response_type", "queued_for_retry")
    
    @staticmethod
    def log_hub_call(
        endpoint: str,
        status_code: int,
        retry_count: int,
        cb_state: str,
        request_body: Optional[Dict] = None,
        response_body: Optional[str] = None,
        duration: Optional[float] = None
    ):
        """Log hub call with truncated bodies.
        
        Args:
            endpoint: Hub endpoint name
            status_code: HTTP status code
            retry_count: Number of retries
            cb_state: Circuit breaker state
            request_body: Request payload (will be masked)
            response_body: Response text
            duration: Call duration in seconds
        """
        # Mask and truncate request
        req_log = ""
        if request_body:
            masked = HubTelemetry.mask_sensitive_fields(request_body)
            req_log = HubTelemetry.truncate_body(masked, max_length=200)
        
        # Truncate response
        resp_log = HubTelemetry.truncate_body(response_body, max_length=200) if response_body else ""
        
        # Build log message
        duration_str = f"{duration:.3f}s" if duration else "N/A"
        
        logger.info(
            f"🌐 Hub call: {endpoint} | "
            f"status={status_code} | "
            f"retries={retry_count} | "
            f"cb={cb_state} | "
            f"duration={duration_str} | "
            f"req={req_log} | "
            f"resp={resp_log}"
        )

