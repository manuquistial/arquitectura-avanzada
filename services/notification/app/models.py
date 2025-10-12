"""Database models for notification service."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class DeliveryLog(Base):
    """Notification delivery log."""
    
    __tablename__ = "delivery_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Event info
    event_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    
    # Notification info
    notification_type = Column(String, nullable=False)  # email, webhook
    recipient = Column(String, nullable=False)  # email address or webhook URL
    subject = Column(String, nullable=True)
    
    # Delivery status
    status = Column(String, default="pending")  # pending, sent, failed, retrying
    delivery_attempts = Column(Integer, default=0)
    
    # Response data
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

