"""OAuth 2.0 Authentication endpoints for operators."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import get_settings
from app.models import (
    OperatorTokenRequest,
    OperatorTokenResponse,
    RegisterOperatorRequest,
    RegisterOperatorResponse,
    OperatorConfig,
)

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# In-memory operator store (use database in production)
operators_store: Dict[str, OperatorConfig] = {}


class OperatorTokenRequestForm(BaseModel):
    """Form data for OAuth 2.0 token request."""
    client_id: str
    client_secret: str
    grant_type: str = "client_credentials"


def create_jwt_token(operator_id: str, operator_name: str) -> str:
    """Create JWT token for operator."""
    payload = {
        "sub": operator_id,
        "operator_name": operator_name,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours),
        "iss": "carpeta-ciudadana-transfer",
        "aud": "transfer-api"
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_jwt_token(token: str) -> dict:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.post("/auth/token", response_model=OperatorTokenResponse)
async def operator_token(request: OperatorTokenRequest):
    """
    OAuth 2.0 token endpoint for operators.
    
    POST /auth/token
    Content-Type: application/x-www-form-urlencoded
    
    Body:
    - client_id: Operator client ID
    - client_secret: Operator client secret
    - grant_type: client_credentials
    """
    logger.info(f"Token request from operator: {request.client_id}")
    
    # Validate grant type
    if request.grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only client_credentials grant type is supported"
        )
    
    # Find operator by client_id
    operator = None
    for op in operators_store.values():
        if op.client_id == request.client_id:
            operator = op
            break
    
    if not operator:
        logger.warning(f"Operator not found: {request.client_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials"
        )
    
    # Verify client secret
    if operator.client_secret != request.client_secret:
        logger.warning(f"Invalid client secret for operator: {request.client_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials"
        )
    
    # Check if operator is active
    if not operator.is_active:
        logger.warning(f"Inactive operator attempted token request: {request.client_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operator is not active"
        )
    
    # Generate JWT token
    access_token = create_jwt_token(operator.operator_id, operator.operator_name)
    
    logger.info(f"Token generated for operator: {operator.operator_id}")
    
    return OperatorTokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.jwt_expiration_hours * 3600  # Convert hours to seconds
    )


@router.post("/register-operator", response_model=RegisterOperatorResponse)
async def register_operator(request: RegisterOperatorRequest):
    """
    Register a new operator for B2B transfers.
    
    POST /register-operator
    """
    logger.info(f"Registering operator: {request.operator_id}")
    
    # Check if operator already exists
    if request.operator_id in operators_store:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Operator {request.operator_id} already exists"
        )
    
    # Check if client_id is already in use
    for op in operators_store.values():
        if op.client_id == request.client_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Client ID {request.client_id} is already in use"
            )
    
    # Create operator configuration
    operator_config = OperatorConfig(
        operator_id=request.operator_id,
        operator_name=request.operator_name,
        client_id=request.client_id,
        client_secret=request.client_secret,
        transfer_api_url=request.transfer_api_url,
        confirm_api_url=request.confirm_api_url,
        is_active=True
    )
    
    # Store operator
    operators_store[request.operator_id] = operator_config
    
    logger.info(f"Operator registered successfully: {request.operator_id}")
    
    return RegisterOperatorResponse(
        message=f"Operator {request.operator_id} registered successfully",
        operator_id=request.operator_id,
        status="registered"
    )


@router.get("/operators")
async def list_operators():
    """
    List all registered operators (for debugging/admin purposes).
    """
    return {
        "operators": [
            {
                "operator_id": op.operator_id,
                "operator_name": op.operator_name,
                "client_id": op.client_id,
                "transfer_api_url": op.transfer_api_url,
                "confirm_api_url": op.confirm_api_url,
                "is_active": op.is_active,
                "created_at": op.created_at
            }
            for op in operators_store.values()
        ]
    }


@router.get("/operators/{operator_id}")
async def get_operator(operator_id: str):
    """
    Get operator configuration by ID.
    """
    if operator_id not in operators_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operator {operator_id} not found"
        )
    
    op = operators_store[operator_id]
    return {
        "operator_id": op.operator_id,
        "operator_name": op.operator_name,
        "client_id": op.client_id,
        "transfer_api_url": op.transfer_api_url,
        "confirm_api_url": op.confirm_api_url,
        "is_active": op.is_active,
        "created_at": op.created_at,
        "updated_at": op.updated_at
    }
