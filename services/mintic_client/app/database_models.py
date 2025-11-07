"""Database models for MinTIC Client service."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Operator(Base):
    """Operator model for persisting MinTIC operators."""
    
    __tablename__ = "operators"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mintic_operator_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    contact_mail = Column(String(255), nullable=False)
    participants = Column(Text, nullable=True)  # JSON string of participants list
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Operator(id={self.id}, mintic_id='{self.mintic_operator_id}', name='{self.name}')>"


class SystemConfig(Base):
    """System configuration for Carpeta Ciudadana."""
    
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String(255), nullable=True)  # User email or system
    
    def __repr__(self):
        return f"<SystemConfig(key='{self.config_key}', value='{self.config_value}')>"
