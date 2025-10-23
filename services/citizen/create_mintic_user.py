#!/usr/bin/env python3
"""Create MinTIC user in the database."""

import os
import sys
import hashlib
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_db
from app.models import User
from sqlalchemy.orm import Session

def hash_password(password: str) -> str:
    """Hash password using SHA256 (for development)."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_mintic_user():
    """Create MinTIC user in the database."""
    print("Creating MinTIC user...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == "mintic@govcarpeta.com").first()
        if existing_user:
            print("✅ MinTIC user already exists")
            return
        
        # Create MinTIC user
        mintic_user = User(
            email="mintic@govcarpeta.com",
            password_hash=hash_password("mintic123"),
            name="Usuario MinTIC",
            roles=json.dumps(["mintic"]),  # Store as JSON string
            permissions=json.dumps(["operator_management", "citizen_registration"]),  # Store as JSON string
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_login=None
        )
        
        db.add(mintic_user)
        db.commit()
        
        print("✅ MinTIC user created successfully")
        print(f"   Email: mintic@govcarpeta.com")
        print(f"   Password: mintic123")
        print(f"   Roles: {mintic_user.roles}")
        
    except Exception as e:
        print(f"❌ Error creating MinTIC user: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_mintic_user()
