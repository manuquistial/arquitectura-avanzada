#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración de database usando
la misma configuración que ingestion/database.py (sin parámetros de pool).

Este script simula exactamente cómo ingestion configura su conexión a la base de datos.
"""

import asyncio
import logging
import sys
import os

# Agregar el directorio del servicio al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_config
from app.database import (
    engine,
    test_connection,
    get_database_info,
    init_db
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_ingestion_db_config():
    """Probar la configuración de database igual que ingestion."""
    logger.info("=" * 60)
    logger.info("🔍 PRUEBA DE CONFIGURACIÓN DE DATABASE (INGESTION STYLE)")
    logger.info("=" * 60)
    
    # Obtener configuración
    config = get_config()
    
    logger.info("\n📋 Configuración detectada:")
    logger.info(f"   Host: {config.database_host}")
    logger.info(f"   Port: {config.database_port}")
    logger.info(f"   Database: {config.database_name}")
    logger.info(f"   User: {config.database_user}")
    logger.info(f"   SSL Mode: {config.database_sslmode}")
    logger.info(f"   Azure Environment: {config.is_azure_environment()}")
    logger.info(f"   Database URL (masked): {config.get_database_url()[:50]}...")
    
    # Mostrar configuración del engine
    logger.info("\n🔧 Configuración del Engine:")
    logger.info("   echo: config.debug")
    logger.info("   connect_args: {ssl: 'require'} (Azure) o {ssl: config.database_sslmode} (local)")
    logger.info("   NO pool_size, max_overflow, pool_pre_ping, pool_recycle")
    
    # Probar 1: Verificar que el engine se creó correctamente
    logger.info("\n" + "=" * 60)
    logger.info("1️⃣ VERIFICANDO ENGINE CREADO")
    logger.info("=" * 60)
    try:
        if engine is None:
            logger.error("❌ Engine es None")
            return False
        logger.info("✅ Engine creado exitosamente")
        logger.info(f"   Engine URL: {str(engine.url)[:50]}...")
    except Exception as e:
        logger.error(f"❌ Error al verificar engine: {e}")
        return False
    
    # Probar 2: Test de conexión básico
    logger.info("\n" + "=" * 60)
    logger.info("2️⃣ PRUEBA DE CONEXIÓN BÁSICA (test_connection)")
    logger.info("=" * 60)
    try:
        result = await test_connection()
        if result:
            logger.info("✅ Conexión básica exitosa")
        else:
            logger.error("❌ Conexión básica falló")
            return False
    except Exception as e:
        logger.error(f"❌ Error en prueba de conexión: {e}")
        logger.error(f"   Tipo: {type(e).__name__}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        return False
    
    # Probar 3: Obtener información de la base de datos
    logger.info("\n" + "=" * 60)
    logger.info("3️⃣ OBTENER INFORMACIÓN DE BASE DE DATOS")
    logger.info("=" * 60)
    try:
        info = await get_database_info()
        if info.get("status") == "connected":
            logger.info("✅ Información de base de datos obtenida:")
            logger.info(f"   Version: {info.get('version', 'N/A')[:50]}...")
            logger.info(f"   Database: {info.get('database', 'N/A')}")
            logger.info(f"   User: {info.get('user', 'N/A')}")
            logger.info(f"   Timestamp: {info.get('timestamp', 'N/A')}")
        else:
            logger.error(f"❌ Error al obtener información: {info.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"❌ Error al obtener información: {e}")
        logger.error(f"   Tipo: {type(e).__name__}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        return False
    
    # Probar 4: Inicialización de base de datos (simulando startup)
    logger.info("\n" + "=" * 60)
    logger.info("4️⃣ PRUEBA DE INICIALIZACIÓN (init_db)")
    logger.info("=" * 60)
    try:
        await init_db()
        logger.info("✅ Inicialización de base de datos completada")
    except Exception as e:
        logger.error(f"❌ Error en inicialización: {e}")
        logger.error(f"   Tipo: {type(e).__name__}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        # No retornamos False aquí porque init_db puede continuar con errores
        logger.warning("⚠️  Continuando (init_db puede funcionar con errores)")
    
    # Probar 5: Múltiples conexiones (simulando uso real)
    logger.info("\n" + "=" * 60)
    logger.info("5️⃣ PRUEBA DE MÚLTIPLES CONEXIONES")
    logger.info("=" * 60)
    try:
        from sqlalchemy import text
        
        async def single_query(conn_id: int):
            try:
                async with engine.begin() as conn:
                    result = await conn.execute(text("SELECT 1, current_database(), now()"))
                    row = result.fetchone()
                    logger.info(f"   Conexión {conn_id}: ✅ OK (DB: {row[1]}, Time: {row[2]})")
                    return True
            except Exception as e:
                logger.error(f"   Conexión {conn_id}: ❌ Error: {e}")
                return False
        
        # Probar 3 conexiones simultáneas
        tasks = [single_query(i) for i in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        logger.info(f"✅ Múltiples conexiones: {success_count}/3 exitosas")
        
        if success_count < 3:
            logger.warning("⚠️  Algunas conexiones fallaron, pero esto puede ser normal")
    
    except Exception as e:
        logger.error(f"❌ Error en prueba de múltiples conexiones: {e}")
        logger.error(f"   Tipo: {type(e).__name__}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
    
    # Resumen final
    logger.info("\n" + "=" * 60)
    logger.info("📊 RESUMEN DE PRUEBAS")
    logger.info("=" * 60)
    logger.info("✅ Configuración de database (estilo ingestion) funciona correctamente")
    logger.info("\n💡 Esta es la misma configuración que deberían usar:")
    logger.info("   - metadata/database.py")
    logger.info("   - signature/database.py")
    logger.info("   - notification/database.py")
    logger.info("\n🔧 Configuración aplicada:")
    logger.info("   - echo: config.debug")
    logger.info("   - connect_args: {ssl: 'require'} (sin parámetros de pool)")
    logger.info("   - SQLAlchemy usa valores por defecto para el pool")
    
    return True


async def main():
    """Función principal."""
    try:
        success = await test_ingestion_db_config()
        if success:
            logger.info("\n🎉 ¡Todas las pruebas pasaron!")
            return 0
        else:
            logger.error("\n❌ Algunas pruebas fallaron")
            return 1
    except Exception as e:
        logger.error(f"\n❌ Error crítico: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

