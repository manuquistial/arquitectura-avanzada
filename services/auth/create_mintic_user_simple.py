#!/usr/bin/env python3
"""Create MinTIC user using direct SQL."""

import hashlib
import json
from datetime import datetime

def hash_password(password: str) -> str:
    """Hash password using SHA256 (for development)."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_mintic_user_sql():
    """Create MinTIC user using SQL."""
    print("Creating MinTIC user with SQL...")
    
    # Hash the password
    password_hash = hash_password("mintic123")
    roles_json = json.dumps(["mintic"])
    permissions_json = json.dumps(["operator_management", "citizen_registration"])
    now = datetime.utcnow()
    
    # SQL to create the user
    sql = f"""
    INSERT INTO users (
        email, password_hash, name, roles, permissions, 
        is_active, is_verified, created_at, updated_at
    ) VALUES (
        'mintic@govcarpeta.com',
        '{password_hash}',
        'Usuario MinTIC',
        '{roles_json}',
        '{permissions_json}',
        true,
        true,
        '{now.isoformat()}',
        '{now.isoformat()}'
    ) ON CONFLICT (email) DO NOTHING;
    """
    
    print("SQL to execute:")
    print(sql)
    print("\n✅ MinTIC user SQL generated")
    print(f"   Email: mintic@govcarpeta.com")
    print(f"   Password: mintic123")
    print(f"   Roles: {roles_json}")
    print(f"   Permissions: {permissions_json}")
    print("\nExecute this SQL in your database to create the user.")

if __name__ == "__main__":
    create_mintic_user_sql()
