"""
Audit Logger - Compliance and Security Event Logging
Tracks all critical operations for compliance and security auditing
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

Base = declarative_base()


class AuditAction(Enum):
    """Audit action types."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SIGN = "sign"
    TRANSFER = "transfer"
    SHARE = "share"
    DOWNLOAD = "download"
    LOGIN = "login"
    LOGOUT = "logout"
    PERMISSION_CHANGE = "permission_change"


class AuditStatus(Enum):
    """Audit event status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


class AuditEvent(Base):
    """
    Audit event model for compliance logging.
    
    Tracks who did what, when, where, and how.
    """
    __tablename__ = 'audit_events'
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Who
    user_id = Column(String(100), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # What
    event_type = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    
    # Where
    service_name = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    
    # How
    request_id = Column(String(100), nullable=True, index=True)
    trace_id = Column(String(100), nullable=True, index=True)
    
    # Details
    details = Column(JSONB, nullable=True)
    changes = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)


class AuditLogger:
    """
    Audit logger for tracking critical operations.
    
    Usage:
        audit = AuditLogger(db_session, service_name="citizen")
        
        audit.log_event(
            user_id="user-123",
            action=AuditAction.CREATE,
            resource_type="document",
            resource_id="doc-456",
            status=AuditStatus.SUCCESS,
            details={"filename": "cedula.pdf"}
        )
    """
    
    def __init__(self, db: Session, service_name: str):
        """
        Initialize audit logger.
        
        Args:
            db: Database session
            service_name: Name of service (e.g., "citizen", "gateway")
        """
        self.db = db
        self.service_name = service_name
    
    def log_event(
        self,
        event_type: str,
        action: AuditAction,
        status: AuditStatus,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (e.g., "DOCUMENT_UPLOAD", "TRANSFER_INITIATED")
            action: Action performed (CREATE, UPDATE, DELETE, etc.)
            status: Event status (SUCCESS, FAILURE, PENDING)
            user_id: User who performed action
            user_email: User email
            ip_address: Client IP address
            resource_type: Type of resource (e.g., "document", "transfer")
            resource_id: ID of resource
            details: Additional details (JSON)
            changes: Before/after changes (JSON)
            error_message: Error message if failure
            request_id: Request ID for correlation
            trace_id: Trace ID for distributed tracing
            user_agent: User agent string
        
        Returns:
            Created audit event
        """
        try:
            event = AuditEvent(
                timestamp=datetime.utcnow(),
                event_type=event_type,
                user_id=user_id,
                user_email=user_email,
                ip_address=ip_address,
                service_name=self.service_name,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action.value,
                status=status.value,
                details=details,
                changes=changes,
                error_message=error_message,
                request_id=request_id,
                trace_id=trace_id,
                user_agent=user_agent
            )
            
            self.db.add(event)
            self.db.commit()
            
            logger.info(
                f"Audit event logged: {event_type} | {action.value} | {status.value} | "
                f"user={user_id} resource={resource_type}:{resource_id}"
            )
            
            return event
        
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            self.db.rollback()
            # Don't fail the original operation if audit logging fails
            raise
    
    def log_document_upload(
        self,
        user_id: str,
        document_id: str,
        filename: str,
        file_size: int,
        status: AuditStatus,
        ip_address: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Log document upload event."""
        return self.log_event(
            event_type="DOCUMENT_UPLOAD",
            action=AuditAction.CREATE,
            status=status,
            user_id=user_id,
            resource_type="document",
            resource_id=document_id,
            ip_address=ip_address,
            details={
                "filename": filename,
                "file_size": file_size
            },
            error_message=error_message
        )
    
    def log_document_sign(
        self,
        user_id: str,
        document_id: str,
        hub_signature: str,
        status: AuditStatus,
        ip_address: Optional[str] = None
    ):
        """Log document signing event."""
        return self.log_event(
            event_type="DOCUMENT_SIGN",
            action=AuditAction.SIGN,
            status=status,
            user_id=user_id,
            resource_type="document",
            resource_id=document_id,
            ip_address=ip_address,
            details={
                "hub_signature": hub_signature,
                "worm_locked": True
            }
        )
    
    def log_transfer(
        self,
        from_user: str,
        to_user: str,
        document_id: str,
        transfer_id: str,
        action: AuditAction,  # TRANSFER, UPDATE
        status: AuditStatus,
        ip_address: Optional[str] = None
    ):
        """Log transfer event."""
        return self.log_event(
            event_type=f"TRANSFER_{action.value.upper()}",
            action=action,
            status=status,
            user_id=from_user,
            resource_type="transfer",
            resource_id=transfer_id,
            ip_address=ip_address,
            details={
                "from_user": from_user,
                "to_user": to_user,
                "document_id": document_id
            }
        )
    
    def log_share(
        self,
        user_id: str,
        document_id: str,
        shortlink_code: str,
        max_views: int,
        expires_hours: int,
        status: AuditStatus,
        ip_address: Optional[str] = None
    ):
        """Log document sharing event."""
        return self.log_event(
            event_type="DOCUMENT_SHARE",
            action=AuditAction.SHARE,
            status=status,
            user_id=user_id,
            resource_type="shortlink",
            resource_id=shortlink_code,
            ip_address=ip_address,
            details={
                "document_id": document_id,
                "max_views": max_views,
                "expires_hours": expires_hours
            }
        )
    
    def log_access(
        self,
        user_id: Optional[str],
        resource_type: str,
        resource_id: str,
        action: AuditAction,
        status: AuditStatus,
        ip_address: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log resource access event."""
        return self.log_event(
            event_type=f"{resource_type.upper()}_ACCESS",
            action=action,
            status=status,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details
        )
    
    def log_permission_change(
        self,
        admin_user: str,
        target_user: str,
        old_roles: list[str],
        new_roles: list[str],
        status: AuditStatus,
        ip_address: Optional[str] = None
    ):
        """Log permission change event."""
        return self.log_event(
            event_type="PERMISSION_CHANGE",
            action=AuditAction.PERMISSION_CHANGE,
            status=status,
            user_id=admin_user,
            resource_type="user",
            resource_id=target_user,
            ip_address=ip_address,
            changes={
                "old_roles": old_roles,
                "new_roles": new_roles
            }
        )
    
    def log_login(
        self,
        user_id: str,
        user_email: str,
        status: AuditStatus,
        ip_address: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Log login event."""
        return self.log_event(
            event_type="USER_LOGIN",
            action=AuditAction.LOGIN,
            status=status,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            error_message=error_message
        )
    
    def log_logout(
        self,
        user_id: str,
        user_email: str,
        ip_address: Optional[str] = None
    ):
        """Log logout event."""
        return self.log_event(
            event_type="USER_LOGOUT",
            action=AuditAction.LOGOUT,
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address
        )


# Middleware for automatic audit logging
class AuditMiddleware:
    """
    Middleware to automatically log audit events for critical endpoints.
    
    Usage:
        from carpeta_common.audit_logger import AuditMiddleware
        
        app.add_middleware(AuditMiddleware, db=get_db, service_name="gateway")
    """
    
    # Critical endpoints to audit
    AUDIT_PATHS = [
        "/api/documents",
        "/api/transfers",
        "/api/signature",
        "/api/auth",
        "/api/users"
    ]
    
    # Methods to audit
    AUDIT_METHODS = ["POST", "PUT", "DELETE", "PATCH"]
    
    def __init__(self, app, db: Session, service_name: str):
        self.app = app
        self.db = db
        self.service_name = service_name
        self.audit_logger = AuditLogger(db, service_name)
    
    async def __call__(self, request: Request, call_next):
        """Process request and log if critical."""
        # Check if should audit
        should_audit = any(
            request.url.path.startswith(path) for path in self.AUDIT_PATHS
        ) and request.method in self.AUDIT_METHODS
        
        if not should_audit:
            return await call_next(request)
        
        # Extract user info from request
        user_id = request.headers.get("X-User-ID")
        user_email = request.headers.get("X-User-Email")
        ip_address = request.client.host if request.client else None
        
        # Process request
        response = await call_next(request)
        
        # Log audit event
        try:
            status = AuditStatus.SUCCESS if response.status_code < 400 else AuditStatus.FAILURE
            
            self.audit_logger.log_event(
                event_type=f"{request.method}_{request.url.path}",
                action=self._map_method_to_action(request.method),
                status=status,
                user_id=user_id,
                user_email=user_email,
                ip_address=ip_address,
                details={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code
                }
            )
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            # Don't fail request if audit logging fails
        
        return response
    
    def _map_method_to_action(self, method: str) -> AuditAction:
        """Map HTTP method to audit action."""
        mapping = {
            "POST": AuditAction.CREATE,
            "GET": AuditAction.READ,
            "PUT": AuditAction.UPDATE,
            "PATCH": AuditAction.UPDATE,
            "DELETE": AuditAction.DELETE
        }
        return mapping.get(method, AuditAction.READ)


# Helper function for getting audit events
async def get_audit_events(
    db: Session,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0
) -> list[AuditEvent]:
    """
    Query audit events with filters.
    
    Args:
        db: Database session
        user_id: Filter by user
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        action: Filter by action
        status: Filter by status
        start_date: Filter by start date
        end_date: Filter by end date
        limit: Max results
        offset: Offset for pagination
    
    Returns:
        List of audit events
    """
    query = db.query(AuditEvent)
    
    if user_id:
        query = query.filter(AuditEvent.user_id == user_id)
    
    if resource_type:
        query = query.filter(AuditEvent.resource_type == resource_type)
    
    if resource_id:
        query = query.filter(AuditEvent.resource_id == resource_id)
    
    if action:
        query = query.filter(AuditEvent.action == action)
    
    if status:
        query = query.filter(AuditEvent.status == status)
    
    if start_date:
        query = query.filter(AuditEvent.timestamp >= start_date)
    
    if end_date:
        query = query.filter(AuditEvent.timestamp <= end_date)
    
    # Order by timestamp descending (most recent first)
    query = query.order_by(AuditEvent.timestamp.desc())
    
    # Pagination
    query = query.offset(offset).limit(limit)
    
    return query.all()

