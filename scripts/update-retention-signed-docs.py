#!/usr/bin/env python3
"""
Script para actualizar retención de documentos firmados.
Documentos firmados (SIGNED) deben tener retention_until = NULL (ETERNAL)
Documentos no firmados (UNSIGNED) deben tener retention_until = created_at + 30 días
"""

import asyncio
import os
import sys
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Database connection from environment
DB_HOST = os.getenv("DB_HOST", "production-psql-hnzlr.postgres.database.azure.com")
DB_USER = os.getenv("DB_USER", "psqladmin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "carpeta_ciudadana")
DB_PORT = os.getenv("DB_PORT", "5432")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?ssl=require"


async def update_retention():
    """Update retention for signed and unsigned documents."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # 1. Update signed documents to ETERNAL (retention_until = NULL)
            print("🔄 Actualizando documentos firmados a retención ETERNA...")
            result_signed = await session.execute(
                text("""
                    UPDATE document_metadata 
                    SET retention_until = NULL 
                    WHERE state = 'SIGNED' 
                      AND retention_until IS NOT NULL
                """)
            )
            await session.commit()
            updated_signed = result_signed.rowcount
            print(f"✅ {updated_signed} documentos firmados actualizados a retención ETERNA")
            
            # 2. Update unsigned documents to 30 days retention
            print("🔄 Actualizando documentos no firmados a retención de 30 días...")
            result_unsigned = await session.execute(
                text("""
                    UPDATE document_metadata 
                    SET retention_until = created_at::date + INTERVAL '30 days'
                    WHERE state = 'UNSIGNED' 
                      AND retention_until IS NULL
                """)
            )
            await session.commit()
            updated_unsigned = result_unsigned.rowcount
            print(f"✅ {updated_unsigned} documentos no firmados actualizados a retención de 30 días")
            
            # 3. Verify results
            print("\n📊 Verificando resultados...")
            result = await session.execute(
                text("""
                    SELECT 
                        state,
                        COUNT(*) as total,
                        COUNT(CASE WHEN retention_until IS NULL THEN 1 END) as eternal,
                        COUNT(CASE WHEN retention_until IS NOT NULL THEN 1 END) as with_date
                    FROM document_metadata
                    GROUP BY state
                    ORDER BY state
                """)
            )
            
            rows = result.fetchall()
            print("\n📈 Resumen por estado:")
            for row in rows:
                state, total, eternal, with_date = row
                print(f"  {state}:")
                print(f"    Total: {total}")
                print(f"    ETERNAL (NULL): {eternal}")
                print(f"    Con fecha: {with_date}")
            
            print("\n✅ Actualización completada exitosamente")
            
        except Exception as e:
            print(f"❌ Error: {e}", file=sys.stderr)
            await session.rollback()
            sys.exit(1)
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_retention())

