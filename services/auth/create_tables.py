#!/usr/bin/env python3
"""
Script to create auth tables directly using SQLAlchemy
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import engine
from app.models import Base

async def create_tables():
    """Create all tables"""
    print("🔧 Creating auth tables...")
    
    try:
        async with engine.begin() as conn:
            # Drop existing tables if they exist
            print("🗑️ Dropping existing tables...")
            await conn.run_sync(Base.metadata.drop_all)
            
            # Create all tables
            print("🏗️ Creating new tables...")
            await conn.run_sync(Base.metadata.create_all)
            
            print("✅ Tables created successfully!")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_tables())
