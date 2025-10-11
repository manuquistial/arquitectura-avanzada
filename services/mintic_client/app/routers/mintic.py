"""MinTIC API router."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.client import MinTICClient
from app.models import (
    AuthenticateDocumentRequest,
    MinTICResponse,
    OperatorInfo,
    RegisterCitizenRequest,
    RegisterOperatorRequest,
    RegisterTransferEndPointRequest,
    UnregisterCitizenRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def get_mintic_client(request: Request) -> MinTICClient:
    """Get MinTIC client from app state."""
    return request.app.state.mintic_client


@router.post("/register-citizen", response_model=MinTICResponse)
async def register_citizen(
    data: RegisterCitizenRequest,
    client: Annotated[MinTICClient, Depends(get_mintic_client)],
) -> MinTICResponse:
    """Register citizen in MinTIC Hub."""
    logger.info(f"Registering citizen: {data.id}")
    result = await client.register_citizen(data)
    if not result.success:
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return result


@router.delete("/unregister-citizen", response_model=MinTICResponse)
async def unregister_citizen(
    data: UnregisterCitizenRequest,
    client: Annotated[MinTICClient, Depends(get_mintic_client)],
) -> MinTICResponse:
    """Unregister citizen from MinTIC Hub."""
    logger.info(f"Unregistering citizen: {data.id}")
    result = await client.unregister_citizen(data)
    if not result.success:
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return result


@router.put("/authenticate-document", response_model=MinTICResponse)
async def authenticate_document(
    data: AuthenticateDocumentRequest,
    client: Annotated[MinTICClient, Depends(get_mintic_client)],
) -> MinTICResponse:
    """Authenticate document in MinTIC Hub."""
    logger.info(f"Authenticating document for citizen: {data.idCitizen}")
    result = await client.authenticate_document(data)
    if not result.success:
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return result


@router.get("/validate-citizen/{citizen_id}", response_model=MinTICResponse)
async def validate_citizen(
    citizen_id: int,
    client: Annotated[MinTICClient, Depends(get_mintic_client)],
) -> MinTICResponse:
    """Validate citizen in MinTIC Hub."""
    logger.info(f"Validating citizen: {citizen_id}")
    result = await client.validate_citizen(citizen_id)
    if not result.success and result.status_code not in (204,):
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return result


@router.post("/register-operator", response_model=MinTICResponse)
async def register_operator(
    data: RegisterOperatorRequest,
    client: Annotated[MinTICClient, Depends(get_mintic_client)],
) -> MinTICResponse:
    """Register operator in MinTIC Hub."""
    logger.info(f"Registering operator: {data.name}")
    result = await client.register_operator(data)
    if not result.success:
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return result


@router.put("/register-transfer-endpoint", response_model=MinTICResponse)
async def register_transfer_endpoint(
    data: RegisterTransferEndPointRequest,
    client: Annotated[MinTICClient, Depends(get_mintic_client)],
) -> MinTICResponse:
    """Register transfer endpoint in MinTIC Hub."""
    logger.info(f"Registering transfer endpoint for operator: {data.idOperator}")
    result = await client.register_transfer_endpoint(data)
    if not result.success:
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return result


@router.get("/operators", response_model=list[OperatorInfo])
async def get_operators(
    client: Annotated[MinTICClient, Depends(get_mintic_client)],
) -> list[OperatorInfo]:
    """Get all operators from MinTIC Hub."""
    logger.info("Fetching operators from MinTIC Hub")
    operators, response = await client.get_operators()
    if not response.success:
        raise HTTPException(status_code=response.status_code, detail=response.message)
    return operators

