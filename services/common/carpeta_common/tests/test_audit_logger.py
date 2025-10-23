"""
Unit tests for Audit Logger
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from carpeta_common.audit_logger import (
    AuditLogger,
    AuditAction,
    AuditStatus,
    AuditEvent
)


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock(spec=Session)
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


def test_audit_logger_initialization(mock_db):
    """Test audit logger initialization."""
    audit = AuditLogger(mock_db, service_name="test_service")
    
    assert audit.db == mock_db
    assert audit.service_name == "test_service"


def test_log_event_success(mock_db):
    """Test logging successful event."""
    audit = AuditLogger(mock_db, service_name="citizen")
    
    event = audit.log_event(
        event_type="DOCUMENT_UPLOAD",
        action=AuditAction.CREATE,
        status=AuditStatus.SUCCESS,
        user_id="user-123",
        resource_type="document",
        resource_id="doc-456",
        details={"filename": "test.pdf"}
    )
    
    # Should have called db.add and db.commit
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_log_event_failure(mock_db):
    """Test logging failed event."""
    audit = AuditLogger(mock_db, service_name="signature")
    
    event = audit.log_event(
        event_type="DOCUMENT_SIGN",
        action=AuditAction.SIGN,
        status=AuditStatus.FAILURE,
        user_id="user-123",
        resource_id="doc-456",
        error_message="Hub authentication failed"
    )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_log_document_upload(mock_db):
    """Test logging document upload."""
    audit = AuditLogger(mock_db, service_name="ingestion")
    
    event = audit.log_document_upload(
        user_id="user-123",
        document_id="doc-456",
        filename="cedula.pdf",
        file_size=1024,
        status=AuditStatus.SUCCESS,
        ip_address="192.168.1.100"
    )
    
    mock_db.add.assert_called_once()


def test_log_document_sign(mock_db):
    """Test logging document signature."""
    audit = AuditLogger(mock_db, service_name="signature")
    
    event = audit.log_document_sign(
        user_id="user-123",
        document_id="doc-456",
        hub_signature="hub_sig_123",
        status=AuditStatus.SUCCESS,
        ip_address="192.168.1.100"
    )
    
    mock_db.add.assert_called_once()


def test_log_transfer(mock_db):
    """Test logging transfer event."""
    audit = AuditLogger(mock_db, service_name="transfer")
    
    event = audit.log_transfer(
        from_user="user-123",
        to_user="user-456",
        document_id="doc-789",
        transfer_id="transfer-111",
        action=AuditAction.TRANSFER,
        status=AuditStatus.SUCCESS,
        ip_address="192.168.1.100"
    )
    
    mock_db.add.assert_called_once()




def test_log_login(mock_db):
    """Test logging login event."""
    audit = AuditLogger(mock_db, service_name="auth")
    
    event = audit.log_login(
        user_id="user-123",
        user_email="user@example.com",
        status=AuditStatus.SUCCESS,
        ip_address="192.168.1.100"
    )
    
    mock_db.add.assert_called_once()


def test_log_login_failure(mock_db):
    """Test logging failed login."""
    audit = AuditLogger(mock_db, service_name="auth")
    
    event = audit.log_login(
        user_id="user-123",
        user_email="user@example.com",
        status=AuditStatus.FAILURE,
        ip_address="192.168.1.100",
        error_message="Invalid credentials"
    )
    
    mock_db.add.assert_called_once()


def test_log_permission_change(mock_db):
    """Test logging permission change."""
    audit = AuditLogger(mock_db, service_name="citizen")
    
    event = audit.log_permission_change(
        admin_user="admin-123",
        target_user="user-456",
        old_roles=["user"],
        new_roles=["user", "operator"],
        status=AuditStatus.SUCCESS,
        ip_address="192.168.1.100"
    )
    
    mock_db.add.assert_called_once()


def test_audit_logger_handles_db_error(mock_db):
    """Test audit logger handles database errors."""
    # Mock commit to raise exception
    mock_db.commit.side_effect = Exception("Database error")
    
    audit = AuditLogger(mock_db, service_name="test")
    
    with pytest.raises(Exception):
        audit.log_event(
            event_type="TEST_EVENT",
            action=AuditAction.CREATE,
            status=AuditStatus.SUCCESS
        )
    
    # Should have called rollback
    mock_db.rollback.assert_called_once()


def test_log_event_with_all_fields(mock_db):
    """Test logging event with all fields populated."""
    audit = AuditLogger(mock_db, service_name="gateway")
    
    event = audit.log_event(
        event_type="DOCUMENT_DELETE",
        action=AuditAction.DELETE,
        status=AuditStatus.SUCCESS,
        user_id="user-123",
        user_email="user@example.com",
        ip_address="192.168.1.100",
        resource_type="document",
        resource_id="doc-456",
        details={"reason": "user request"},
        changes={"status": {"from": "active", "to": "deleted"}},
        request_id="req-789",
        trace_id="trace-111",
        user_agent="Mozilla/5.0"
    )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

