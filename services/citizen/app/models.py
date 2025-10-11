"""Citizen database models."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


class Citizen(Base):
    """Citizen database model."""

    __tablename__ = "citizens"

    id = Column(Integer, primary_key=True, index=True)  # Cédula
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    operator_id = Column(String, nullable=False)
    operator_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

