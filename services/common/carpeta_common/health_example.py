"""
Example of how to integrate health checks in a FastAPI service.

Copy this pattern to your service's main.py
"""

from fastapi import FastAPI
from app.config import Settings

def create_app() -> FastAPI:
    """Create FastAPI application with health checks."""
    settings = Settings()
    
    app = FastAPI(title="My Service")
    
    # Option 1: Use the health router from common (RECOMMENDED)
    try:
        from carpeta_common.health import create_health_router
        
        health_router = create_health_router(
            check_database=True,
            check_redis=False,
            check_service_bus=False,  # Optional, only in readiness
            check_opensearch=False,
            database_url=settings.database_url,
            redis_host=getattr(settings, 'redis_host', None),
            redis_port=getattr(settings, 'redis_port', 6379),
            redis_password=getattr(settings, 'redis_password', ''),
            servicebus_conn=getattr(settings, 'servicebus_connection_string', None),
            opensearch_host=getattr(settings, 'opensearch_host', None),
            opensearch_port=getattr(settings, 'opensearch_port', 9200),
        )
        
        app.include_router(health_router, tags=["health"])
        
    except ImportError:
        # Option 2: Simple fallback if common package not available
        @app.get("/health")
        async def health():
            """Liveness probe - process is alive."""
            return {"status": "alive"}
        
        @app.get("/ready")
        async def ready():
            """Readiness probe - ready to serve traffic."""
            # TODO: Check critical dependencies here
            return {"status": "ready"}
    
    # Your other routes...
    
    return app


# Example for each service type:

# 1. Citizen Service (has DB)
health_router = create_health_router(
    check_database=True,
    database_url=settings.database_url,
)

# 2. Metadata Service (has DB + OpenSearch)
health_router = create_health_router(
    check_database=True,
    check_opensearch=True,
    database_url=settings.database_url,
    opensearch_host=settings.opensearch_host,
)

# 3. Gateway (has Redis)
health_router = create_health_router(
    check_redis=True,
    redis_host=settings.redis_host,
)

# 4. Signature (has DB + Redis + Service Bus)
health_router = create_health_router(
    check_database=True,
    check_redis=True,
    check_service_bus=True,  # Optional in readiness
    database_url=settings.database_url,
    redis_host=settings.redis_host,
    servicebus_conn=settings.servicebus_connection_string,
)

