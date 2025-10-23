"""Operator service for managing MinTIC operators."""

import json
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database_models import Operator
from app.models import RegisterOperatorRequest

logger = logging.getLogger(__name__)


class OperatorService:
    """Service for managing operators."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_operator(self, request: RegisterOperatorRequest, mintic_operator_id: str) -> Operator:
        """Create a new operator in the database."""
        try:
            # Convert participants list to JSON string
            participants_json = json.dumps(request.participants) if request.participants else None
            
            operator = Operator(
                mintic_operator_id=mintic_operator_id,
                name=request.name,
                address=request.address,
                contact_mail=request.contactMail,
                participants=participants_json,
                is_active=True
            )
            
            self.db.add(operator)
            self.db.commit()
            self.db.refresh(operator)
            
            logger.info(f"✅ Operator created in database: {operator.name} (MinTIC ID: {mintic_operator_id})")
            return operator
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"❌ Failed to create operator: {e}")
            raise ValueError(f"Operator with MinTIC ID {mintic_operator_id} already exists")
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Failed to create operator: {e}")
            raise
    
    def get_operator_by_mintic_id(self, mintic_operator_id: str) -> Optional[Operator]:
        """Get operator by MinTIC operator ID."""
        return self.db.query(Operator).filter(
            Operator.mintic_operator_id == mintic_operator_id
        ).first()
    
    def get_operator_by_id(self, operator_id: int) -> Optional[Operator]:
        """Get operator by internal ID."""
        return self.db.query(Operator).filter(Operator.id == operator_id).first()
    
    def get_all_operators(self, active_only: bool = True) -> List[Operator]:
        """Get all operators."""
        query = self.db.query(Operator)
        if active_only:
            query = query.filter(Operator.is_active == True)
        return query.order_by(Operator.created_at.desc()).all()
    
    def update_operator(self, operator_id: int, **kwargs) -> Optional[Operator]:
        """Update operator."""
        operator = self.get_operator_by_id(operator_id)
        if not operator:
            return None
        
        try:
            for key, value in kwargs.items():
                if hasattr(operator, key):
                    setattr(operator, key, value)
            
            self.db.commit()
            self.db.refresh(operator)
            
            logger.info(f"✅ Operator updated: {operator.name}")
            return operator
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Failed to update operator: {e}")
            raise
    
    def deactivate_operator(self, operator_id: int) -> bool:
        """Deactivate operator."""
        operator = self.get_operator_by_id(operator_id)
        if not operator:
            return False
        
        try:
            operator.is_active = False
            self.db.commit()
            
            logger.info(f"✅ Operator deactivated: {operator.name}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Failed to deactivate operator: {e}")
            return False
    
    def delete_operator(self, operator_id: int) -> bool:
        """Delete operator."""
        operator = self.get_operator_by_id(operator_id)
        if not operator:
            return False
        
        try:
            self.db.delete(operator)
            self.db.commit()
            
            logger.info(f"✅ Operator deleted: {operator.name}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Failed to delete operator: {e}")
            return False
