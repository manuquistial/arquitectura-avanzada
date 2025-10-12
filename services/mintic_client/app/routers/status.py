"""Status and monitoring endpoints for MinTIC client service."""

import logging
from fastapi import APIRouter, Depends
from typing import Dict

from app.client import MinTICClient
from app.config import Settings

logger = logging.getLogger(__name__)

router = APIRouter()


def get_settings() -> Settings:
    """Get settings dependency."""
    return Settings()


def get_client(settings: Settings = Depends(get_settings)) -> MinTICClient:
    """Get MinTIC client dependency."""
    return MinTICClient(settings)


@router.get("/ops/hub-rate-limit/status")
async def hub_rate_limit_status(
    client: MinTICClient = Depends(get_client)
) -> Dict:
    """Get hub rate limiter status for all endpoints.
    
    Returns current usage, limits, and remaining calls for each hub endpoint.
    """
    endpoints = [
        "registerCitizen",
        "unregisterCitizen",
        "authenticateDocument",
        "validateCitizen",
        "getOperators"
    ]
    
    status = {
        "enabled": client.hub_rate_limiter.enabled,
        "limit_per_minute": client.hub_rate_limiter.requests_per_minute,
        "endpoints": {}
    }
    
    for endpoint in endpoints:
        usage = await client.hub_rate_limiter.get_current_usage(endpoint)
        status["endpoints"][endpoint] = usage
    
    return status


@router.get("/ops/circuit-breakers/status")
async def circuit_breakers_status(
    client: MinTICClient = Depends(get_client)
) -> Dict:
    """Get circuit breaker status for all hub endpoints."""
    status = {
        "enabled": len(client.circuit_breakers) > 0,
        "endpoints": {}
    }
    
    for name, cb in client.circuit_breakers.items():
        status["endpoints"][name] = {
            "state": cb.state.value if hasattr(cb.state, 'value') else str(cb.state),
            "failure_count": cb.failure_count if hasattr(cb, 'failure_count') else 0,
            "last_failure_time": cb.last_failure_time if hasattr(cb, 'last_failure_time') else None
        }
    
    return status

