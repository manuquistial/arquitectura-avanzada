#!/usr/bin/env python3
"""
Script de prueba optimizado para probar conexión a PostgreSQL en Azure desde un pod de Kubernetes.
Simula el entorno de un pod con variables de entorno y configuración SSL adecuada.
"""

import asyncio
import os
import ssl
import logging
import sys
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Configuración de base de datos para Azure PostgreSQL"""
    host: str
    port: int
    database: str
    username: str
    password: str
    sslmode: str = "require"
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Crear configuración desde variables de entorno del pod"""
        return cls(
            host=os.getenv("DB_HOST", "mock-postgres-host.database.azure.com"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "carpeta_ciudadana"),
            username=os.getenv("DB_USER", "mock_user"),
            password=os.getenv("DB_PASSWORD", "mock_password_123"),
            sslmode=os.getenv("DB_SSLMODE", "require")
        )
    
    def get_psycopg_url(self) -> str:
        """URL para psycopg3"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?sslmode={self.sslmode}"
    
    def get_asyncpg_url(self) -> str:
        """URL para asyncpg con SQLAlchemy"""
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?ssl=require"
    
    def get_psycopg_async_url(self) -> str:
        """URL para psycopg3 asíncrono con SQLAlchemy"""
        return f"postgresql+psycopg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?sslmode={self.sslmode}"

class PodDatabaseTester:
    """Tester para conexión a PostgreSQL desde un pod de Kubernetes"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.results: Dict[str, bool] = {}
        
        logger.info("🔧 Configuración del pod:")
        logger.info(f"   Host: {self.config.host}")
        logger.info(f"   Port: {self.config.port}")
        logger.info(f"   Database: {self.config.database}")
        logger.info(f"   User: {self.config.username}")
        logger.info(f"   SSL Mode: {self.config.sslmode}")
    
    def create_ssl_context(self) -> ssl.SSLContext:
        """Crear contexto SSL para Azure PostgreSQL"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
    
    async def test_psycopg3_sync(self) -> bool:
        """Probar conexión síncrona con psycopg3 (recomendado para FastAPI)"""
        try:
            import psycopg
            
            logger.info("🔍 Probando psycopg3 síncrono...")
            
            ssl_context = self.create_ssl_context()
            
            with psycopg.connect(self.config.get_psycopg_url(), ssl=ssl_context) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1, version()")
                    result = cur.fetchone()
                    logger.info(f"✅ psycopg3 síncrono exitoso: {result[0]}")
                    logger.info(f"   PostgreSQL version: {result[1][:50]}...")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Error en psycopg3 síncrono: {e}")
            return False
    
    async def test_psycopg3_async(self) -> bool:
        """Probar conexión asíncrona con psycopg3"""
        try:
            import psycopg
            
            logger.info("🔍 Probando psycopg3 asíncrono...")
            
            ssl_context = self.create_ssl_context()
            
            async with await psycopg.AsyncConnection.connect(
                self.config.get_psycopg_url(), 
                ssl=ssl_context
            ) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1, version()")
                    result = await cur.fetchone()
                    logger.info(f"✅ psycopg3 asíncrono exitoso: {result[0]}")
                    logger.info(f"   PostgreSQL version: {result[1][:50]}...")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Error en psycopg3 asíncrono: {e}")
            return False
    
    async def test_asyncpg(self) -> bool:
        """Probar conexión con asyncpg (alternativa a psycopg3)"""
        try:
            import asyncpg
            
            logger.info("🔍 Probando asyncpg...")
            
            ssl_context = self.create_ssl_context()
            
            conn = await asyncpg.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                ssl=ssl_context
            )
            
            result = await conn.fetchval("SELECT 1")
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            
            logger.info(f"✅ asyncpg exitoso: {result}")
            logger.info(f"   PostgreSQL version: {version[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en asyncpg: {e}")
            return False
    
    async def test_sqlalchemy_psycopg(self) -> bool:
        """Probar SQLAlchemy con psycopg3 (configuración recomendada)"""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text
            
            logger.info("🔍 Probando SQLAlchemy + psycopg3...")
            
            engine = create_async_engine(
                self.config.get_psycopg_async_url(),
                echo=False,
                connect_args={
                    "sslmode": self.config.sslmode,
                    "connect_timeout": 10
                }
            )
            
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1, version()"))
                row = result.fetchone()
                logger.info(f"✅ SQLAlchemy + psycopg3 exitoso: {row[0]}")
                logger.info(f"   PostgreSQL version: {row[1][:50]}...")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error en SQLAlchemy + psycopg3: {e}")
            return False
    
    async def test_sqlalchemy_asyncpg(self) -> bool:
        """Probar SQLAlchemy con asyncpg"""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text
            
            logger.info("🔍 Probando SQLAlchemy + asyncpg...")
            
            engine = create_async_engine(
                self.config.get_asyncpg_url(),
                echo=False,
                connect_args={"ssl": "require"}
            )
            
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1, version()"))
                row = result.fetchone()
                logger.info(f"✅ SQLAlchemy + asyncpg exitoso: {row[0]}")
                logger.info(f"   PostgreSQL version: {row[1][:50]}...")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error en SQLAlchemy + asyncpg: {e}")
            return False
    
    async def test_connection_pool(self) -> bool:
        """Probar pool de conexiones (simulando uso en producción)"""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text
            
            logger.info("🔍 Probando pool de conexiones...")
            
            engine = create_async_engine(
                self.config.get_psycopg_async_url(),
                echo=False,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                connect_args={
                    "sslmode": self.config.sslmode,
                    "connect_timeout": 10
                }
            )
            
            # Probar múltiples conexiones
            tasks = []
            for i in range(3):
                task = asyncio.create_task(self._test_single_connection(engine, i))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            await engine.dispose()
            
            success_count = sum(1 for r in results if r is True)
            logger.info(f"✅ Pool de conexiones: {success_count}/3 conexiones exitosas")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error en pool de conexiones: {e}")
            return False
    
    async def _test_single_connection(self, engine, connection_id: int) -> bool:
        """Probar una conexión individual del pool"""
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                value = result.scalar()
                logger.info(f"   Conexión {connection_id}: {value}")
                return True
        except Exception as e:
            logger.error(f"   Error en conexión {connection_id}: {e}")
            return False
    
    async def test_network_connectivity(self) -> bool:
        """Probar conectividad de red básica"""
        try:
            import socket
            
            logger.info("🔍 Probando conectividad de red...")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            result = sock.connect_ex((self.config.host, self.config.port))
            sock.close()
            
            if result == 0:
                logger.info(f"✅ Conectividad de red exitosa a {self.config.host}:{self.config.port}")
                return True
            else:
                logger.error(f"❌ Sin conectividad a {self.config.host}:{self.config.port}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en prueba de conectividad: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Ejecutar todas las pruebas de conexión"""
        logger.info("🚀 Iniciando pruebas de conexión desde pod...")
        logger.info("=" * 60)
        
        # Probar conectividad de red primero
        network_ok = await self.test_network_connectivity()
        self.results["Network Connectivity"] = network_ok
        
        if not network_ok:
            logger.error("❌ Sin conectividad de red. Verificar configuración del pod.")
            return self.results
        
        # Probar diferentes métodos de conexión
        tests = [
            ("psycopg3 Sync", self.test_psycopg3_sync()),
            ("psycopg3 Async", self.test_psycopg3_async()),
            ("asyncpg", self.test_asyncpg()),
            ("SQLAlchemy + psycopg3", self.test_sqlalchemy_psycopg()),
            ("SQLAlchemy + asyncpg", self.test_sqlalchemy_asyncpg()),
            ("Connection Pool", self.test_connection_pool()),
        ]
        
        for test_name, test_coro in tests:
            try:
                result = await test_coro
                self.results[test_name] = result
            except Exception as e:
                logger.error(f"❌ Error inesperado en {test_name}: {e}")
                self.results[test_name] = False
        
        return self.results
    
    def print_results(self):
        """Imprimir resultados de las pruebas"""
        logger.info("=" * 60)
        logger.info("📊 RESUMEN DE PRUEBAS DE CONEXIÓN DESDE POD:")
        
        successful = sum(1 for result in self.results.values() if result)
        total = len(self.results)
        
        for test_name, result in self.results.items():
            status = "✅ ÉXITO" if result else "❌ FALLO"
            logger.info(f"   {test_name}: {status}")
        
        logger.info(f"   Total: {successful}/{total} pruebas exitosas")
        
        if successful > 0:
            logger.info("🎉 ¡Conexión a PostgreSQL exitosa desde el pod!")
            logger.info("💡 Recomendaciones:")
            
            if self.results.get("SQLAlchemy + psycopg3", False):
                logger.info("   ✅ Usar SQLAlchemy + psycopg3 para FastAPI")
            if self.results.get("psycopg3 Sync", False):
                logger.info("   ✅ psycopg3 síncrono funciona correctamente")
            if self.results.get("Connection Pool", False):
                logger.info("   ✅ Pool de conexiones configurado correctamente")
        else:
            logger.error("❌ Ninguna conexión funciona. Verificar:")
            logger.error("   - Variables de entorno del pod")
            logger.error("   - Configuración de red del cluster")
            logger.error("   - Firewall de Azure PostgreSQL")
            logger.error("   - Credenciales de base de datos")

async def main():
    """Función principal"""
    # Crear configuración desde variables de entorno
    config = DatabaseConfig.from_env()
    
    # Crear tester
    tester = PodDatabaseTester(config)
    
    # Ejecutar pruebas
    results = await tester.run_all_tests()
    
    # Mostrar resultados
    tester.print_results()
    
    # Retornar éxito si al menos una prueba funciona
    return any(result for result in results.values())

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
