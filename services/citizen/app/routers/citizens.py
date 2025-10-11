"""Citizens API router."""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import get_db
from app.models import Citizen
from app.schemas import CitizenCreate, CitizenResponse, CitizenUnregister

settings = Settings()

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=CitizenResponse, status_code=status.HTTP_201_CREATED)
async def register_citizen(
    citizen_data: CitizenCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Citizen:
    """Register a new citizen."""
    logger.info(f"Registering citizen: {citizen_data.id}")

    # Check if citizen already exists
    result = await db.execute(select(Citizen).where(Citizen.id == citizen_data.id))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Citizen {citizen_data.id} already registered",
        )

    # Create citizen
    citizen = Citizen(
        id=citizen_data.id,
        name=citizen_data.name,
        address=citizen_data.address,
        email=citizen_data.email,
        operator_id=citizen_data.operator_id,
        operator_name=citizen_data.operator_name,
    )

    db.add(citizen)
    await db.commit()
    await db.refresh(citizen)

    # Register citizen in MinTIC Hub (async, non-blocking)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.mintic_client_url}/apis/registerCitizen",
                json={
                    "id": citizen.id,
                    "name": citizen.name,
                    "address": citizen.address,
                    "email": citizen.email,
                    "operatorId": citizen.operator_id,
                    "operatorName": citizen.operator_name,
                }
            )
            if response.status_code == 201:
                logger.info(f"Citizen {citizen.id} registered in MinTIC Hub")
            else:
                logger.warning(f"Failed to register in MinTIC Hub: {response.text}")
    except Exception as e:
        # Don't fail citizen registration if MinTIC sync fails
        logger.error(f"Error calling MinTIC client: {e}")
    
    # TODO: Publish event to Service Bus/SQS for async processing

    return citizen


@router.delete("/unregister", status_code=status.HTTP_200_OK)
async def unregister_citizen(
    data: CitizenUnregister,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Unregister a citizen."""
    logger.info(f"Unregistering citizen: {data.id}")

    # Get citizen
    result = await db.execute(select(Citizen).where(Citizen.id == data.id))
    citizen = result.scalar_one_or_none()

    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Citizen {data.id} not found",
        )

    # Mark as inactive
    citizen.is_active = False
    await db.commit()

    # Unregister from MinTIC Hub (async, non-blocking)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.delete(
                f"{settings.mintic_client_url}/apis/unregisterCitizen",
                json={
                    "id": citizen.id,
                    "operatorId": citizen.operator_id,
                    "operatorName": citizen.operator_name,
                }
            )
            if response.status_code == 200:
                logger.info(f"Citizen {citizen.id} unregistered from MinTIC Hub")
            else:
                logger.warning(f"Failed to unregister from MinTIC Hub: {response.text}")
    except Exception as e:
        logger.error(f"Error calling MinTIC client: {e}")
    
    # TODO: Publish event to Service Bus/SQS for async processing

    return {"message": f"Citizen {data.id} unregistered successfully"}


@router.get("/{citizen_id}", response_model=CitizenResponse)
async def get_citizen(
    citizen_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Citizen:
    """Get citizen by ID."""
    result = await db.execute(select(Citizen).where(Citizen.id == citizen_id))
    citizen = result.scalar_one_or_none()

    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Citizen {citizen_id} not found",
        )

    return citizen


@router.get("/", response_model=list[CitizenResponse])
async def list_citizens(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
) -> list[Citizen]:
    """List all citizens."""
    result = await db.execute(
        select(Citizen).where(Citizen.is_active == True).offset(skip).limit(limit)
    )
    citizens = result.scalars().all()
    return list(citizens)

