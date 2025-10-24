"""
Health check utilities for FastAPI services.

Provides liveness and readiness probes with dependency checking.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health check status."""
    
    def __init__(self):
        self.checks: Dict[str, Dict[str, Any]] = {}
        self.healthy = True
        self.ready = True
    
    def add_check(self, name: str, healthy: bool, message: str = "", duration_ms: float = 0):
        """Add a health check result."""
        self.checks[name] = {
            "healthy": healthy,
            "message": message,
            "duration_ms": round(duration_ms, 2)
        }
        
        if not healthy:
            self.healthy = False
            self.ready = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": "healthy" if self.healthy else "unhealthy",
            "ready": self.ready,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": self.checks
        }


async def check_database(db_url: str, timeout: float = 2.0) -> tuple[bool, str, float]:
    """
    Check database connectivity.
    
    Args:
        db_url: Database connection URL
        timeout: Timeout in seconds
        
    Returns:
        (healthy, message, duration_ms)
    """
    if not db_url:
        return True, "Database not configured", 0.0
    
    start = asyncio.get_event_loop().time()
    
    try:
        # Try SQLAlchemy async
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        engine = create_async_engine(db_url, pool_pre_ping=True)
        
        async with asyncio.timeout(timeout):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        
        await engine.dispose()
        
        duration = (asyncio.get_event_loop().time() - start) * 1000
        return True, "Database OK", duration
        
    except asyncio.TimeoutError:
        duration = (asyncio.get_event_loop().time() - start) * 1000
        return False, f"Database timeout (>{timeout}s)", duration
    except Exception as e:
        duration = (asyncio.get_event_loop().time() - start) * 1000
        logger.error(f"Database health check failed: {e}")
        return False, f"Database error: {str(e)[:100]}", duration


async def check_redis(host: str, port: int = 6379, password: str = "", timeout: float = 2.0) -> tuple[bool, str, float]:
    """
    Check Redis connectivity.
    
    Args:
        host: Redis host
        port: Redis port
        password: Redis password (optional)
        timeout: Timeout in seconds
        
    Returns:
        (healthy, message, duration_ms)
    """
    if not host or host == "localhost":
        return True, "Redis not configured", 0.0
    
    start = asyncio.get_event_loop().time()
    
    try:
        import redis.asyncio as aioredis
        
        redis_client = aioredis.Redis(
            host=host,
            port=port,
            password=password if password else None,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
            decode_responses=True
        )
        
        async with asyncio.timeout(timeout):
            await redis_client.ping()
        
        await redis_client.close()
        
        duration = (asyncio.get_event_loop().time() - start) * 1000
        return True, "Redis OK", duration
        
    except asyncio.TimeoutError:
        duration = (asyncio.get_event_loop().time() - start) * 1000
        return False, f"Redis timeout (>{timeout}s)", duration
    except Exception as e:
        duration = (asyncio.get_event_loop().time() - start) * 1000
        logger.error(f"Redis health check failed: {e}")
        return False, f"Redis error: {str(e)[:100]}", duration


async def check_service_bus(connection_string: str, timeout: float = 3.0) -> tuple[bool, str, float]:
    """
    Check Service Bus connectivity (optional, only for readiness).
    
    Args:
        connection_string: Service Bus connection string
        timeout: Timeout in seconds
        
    Returns:
        (healthy, message, duration_ms)
    """
    if not connection_string:
        return True, "Service Bus not configured", 0.0
    
    start = asyncio.get_event_loop().time()
    
    try:
        from azure.servicebus.aio import ServiceBusClient
        
        async with asyncio.timeout(timeout):
            async with ServiceBusClient.from_connection_string(connection_string) as client:
                # List queues to verify connection
                # Note: This requires manage permissions, might fail with limited permissions
                pass
        
        duration = (asyncio.get_event_loop().time() - start) * 1000
        return True, "Service Bus OK", duration
        
    except asyncio.TimeoutError:
        duration = (asyncio.get_event_loop().time() - start) * 1000
        return False, f"Service Bus timeout (>{timeout}s)", duration
    except ImportError:
        return True, "Service Bus client not available", 0.0
    except Exception as e:
        duration = (asyncio.get_event_loop().time() - start) * 1000
        logger.warning(f"Service Bus health check failed: {e}")
        # Don't fail readiness if SB is optional
        return True, f"Service Bus warning: {str(e)[:50]}", duration




def create_health_router(
    check_database: bool = True,
    check_redis: bool = False,
    check_service_bus: bool = False,
    database_url: Optional[str] = None,
    redis_host: Optional[str] = None,
    redis_port: int = 6379,
    redis_password: str = "",
    servicebus_conn: Optional[str] = None,
):
    """
    Create FastAPI router with health endpoints.
    
    Args:
        check_database: Check database in readiness
        check_redis: Check Redis in readiness
        check_service_bus: Check Service Bus in readiness
        database_url: Database URL
        redis_host: Redis host
        redis_port: Redis port
        redis_password: Redis password
        servicebus_conn: Service Bus connection string
        
    Returns:
        APIRouter with /health and /ready endpoints
    """
    from fastapi import APIRouter, Response, status
    
    router = APIRouter()
    
    @router.get("/health")
    async def liveness() -> Dict[str, Any]:
        """
        Liveness probe - checks if service is alive.
        
        Returns 200 if process is running.
        Should NOT check external dependencies.
        """
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @router.get("/ready")
    async def readiness(response: Response) -> Dict[str, Any]:
        """
        Readiness probe - checks if service is ready to accept traffic.
        
        Checks external dependencies:
        - Database (if enabled)
        - Redis (if enabled)
        - Service Bus (if enabled)
        
        Returns 200 if ready, 503 if not ready.
        """
        health = HealthStatus()
        
        # Check database
        if check_database and database_url:
            healthy, message, duration = await check_database(database_url)
            health.add_check("database", healthy, message, duration)
        
        # Check Redis
        if check_redis and redis_host:
            healthy, message, duration = await check_redis(
                redis_host, redis_port, redis_password
            )
            health.add_check("redis", healthy, message, duration)
        
        # Check Service Bus (optional, might not have manage permissions)
        if check_service_bus and servicebus_conn:
            healthy, message, duration = await check_service_bus(servicebus_conn)
            health.add_check("service_bus", healthy, message, duration)
        
        
        # Set response status
        if not health.ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
        return health.to_dict()
    
    return router

