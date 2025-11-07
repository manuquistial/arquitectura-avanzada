#!/usr/bin/env python3
"""
Script to create or update admin user
Creates admin@carpeta.com with password admin123 and admin role
"""

import asyncio
import sys
import os
import json
import hashlib

# Add services/auth to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'auth'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, text

# Database connection - get from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://psqladmin:2KFqv4LlAiRn7oFopoR@production-psql-hnzlr.postgres.database.azure.com:5432/carpeta_ciudadana?ssl=require"
)


def hash_password(password: str) -> str:
    """Hash password using SHA256 (same as AuthService)."""
    return hashlib.sha256(password.encode()).hexdigest()


async def create_or_update_admin_user():
    """Create or update admin user."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Hash password
        password_hash = hash_password("admin123")
        
        # Check if user exists
        result = await session.execute(
            text("SELECT id, email, roles, permissions FROM users WHERE email = 'admin@carpeta.com'")
        )
        user = result.fetchone()
        
        if user:
            print(f"✅ Usuario encontrado: {user[1]} (ID: {user[0]})")
            user_id = user[0]
            
            # Update user to admin
            await session.execute(
                text("""
                    UPDATE users 
                    SET roles = :roles,
                        permissions = :permissions,
                        password_hash = :password_hash,
                        is_verified = true
                    WHERE id = :user_id
                """),
                {
                    "roles": json.dumps(["admin"]),
                    "permissions": json.dumps(["*"]),
                    "password_hash": password_hash,
                    "user_id": user_id
                }
            )
            print("✅ Usuario actualizado a admin")
        else:
            print("❌ Usuario no encontrado, creando nuevo usuario admin...")
            # Create new admin user
            await session.execute(
                text("""
                    INSERT INTO users (email, password_hash, name, given_name, family_name, roles, permissions, is_active, is_verified)
                    VALUES (:email, :password_hash, :name, :given_name, :family_name, :roles, :permissions, true, true)
                """),
                {
                    "email": "admin@carpeta.com",
                    "password_hash": password_hash,
                    "name": "Administrator",
                    "given_name": "Admin",
                    "family_name": "User",
                    "roles": json.dumps(["admin"]),
                    "permissions": json.dumps(["*"])
                }
            )
            print("✅ Usuario admin creado")
        
        await session.commit()
        print("✅ Cambios guardados en la base de datos")
        
        # Verify the update
        result = await session.execute(
            text("SELECT id, email, roles, permissions FROM users WHERE email = 'admin@carpeta.com'")
        )
        user = result.fetchone()
        if user:
            print(f"\n📋 Usuario verificado:")
            print(f"   ID: {user[0]}")
            print(f"   Email: {user[1]}")
            print(f"   Roles: {user[2]}")
            print(f"   Permissions: {user[3]}")
        
        return True


if __name__ == "__main__":
    try:
        asyncio.run(create_or_update_admin_user())
        print("\n✅ Script completado exitosamente")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

