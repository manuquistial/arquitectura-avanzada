#!/usr/bin/env python3
"""Execute SQL to create MinTIC user in the database."""

import os
import sys
import asyncio
from sqlalchemy import text
from app.database import get_db

async def create_mintic_user():
    """Create MinTIC user in the database."""
    print("Creating MinTIC user in database...")
    
    sql = """
    INSERT INTO users (
        email, password_hash, name, roles, permissions, 
        is_active, is_verified, created_at, updated_at
    ) VALUES (
        'mintic@govcarpeta.com',
        '60684d48440f9405af7bc268b7a18a54f6d71d2df38d622ea8b76b09ad4b005c',
        'Usuario MinTIC',
        '["mintic"]',
        '["operator_management", "citizen_registration"]',
        true,
        true,
        '2025-10-22T06:15:53.690827',
        '2025-10-22T06:15:53.690827'
    ) ON CONFLICT (email) DO NOTHING;
    """
    
    try:
        async for db in get_db():
            result = await db.execute(text(sql))
            await db.commit()
            print("✅ MinTIC user created successfully")
            break
    except Exception as e:
        print(f"❌ Error creating MinTIC user: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(create_mintic_user())
