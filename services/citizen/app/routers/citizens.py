"""Citizens API router."""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Citizen
from app.schemas import CitizenCreate, CitizenResponse, CitizenUnregister

settings = get_settings()

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=CitizenResponse, status_code=status.HTTP_201_CREATED)
async def register_citizen(
    citizen_data: CitizenCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Citizen:
    """Register a new citizen."""
    logger.info(f"=== REGISTER CITIZEN START ===")
    logger.info(f"Received citizen data: {citizen_data}")
    logger.info(f"Citizen ID: {citizen_data.id}")
    logger.info(f"Citizen name: {citizen_data.name}")
    logger.info(f"Citizen email: {citizen_data.email}")
    logger.info(f"Operator ID: {citizen_data.operator_id}")
    logger.info(f"Operator name: {citizen_data.operator_name}")

    try:
        # Check if citizen already exists in local database
        logger.info("Checking if citizen already exists in local database...")
        result = await db.execute(select(Citizen).where(Citizen.id == citizen_data.id))
        existing = result.scalar_one_or_none()

        if existing:
            logger.warning(f"Citizen {citizen_data.id} already exists in local database")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El ciudadano con ID {citizen_data.id} ya se encuentra registrado en la Carpeta Ciudadana",
            )

        logger.info("Creating citizen in local database...")
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
        await db.flush()  # Flush but don't commit yet
        logger.info(f"Citizen {citizen.id} created in local database (flushed)")

        # Register citizen in MinTIC Hub via mintic_client service (simple facade)
        logger.info(f"Calling MinTIC service at: {settings.mintic_client_url}/api/mintic/register-citizen")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Call mintic_client service (facade to hub)
                mintic_payload = {
                    "id": int(citizen.id),  # Convert to int as expected by MinTIC service
                    "name": citizen.name,
                    "address": citizen.address,
                    "email": citizen.email,
                    "operatorId": citizen.operator_id,
                    "operatorName": citizen.operator_name,
                }
                logger.info(f"MinTIC payload: {mintic_payload}")
                
                response = await client.post(
                    f"{settings.mintic_client_url}/api/mintic/register-citizen",
                    json=mintic_payload
                )
                
                logger.info(f"MinTIC response status: {response.status_code}")
                logger.info(f"MinTIC response headers: {dict(response.headers)}")
                logger.info(f"MinTIC response text: {response.text}")
                
                if response.status_code == 200:
                    logger.info(f"✅ Citizen {citizen.id} registered in MinTIC Hub")
                elif response.status_code in [400, 409]:
                    # Rollback local registration
                    logger.warning(f"MinTIC returned {response.status_code}, rolling back local registration")
                    await db.rollback()
                    error_data = response.json() if response.headers.get("content-type") == "application/json" else {}
                    error_detail = error_data.get("detail", response.text)
                    
                    # Check if it's a duplicate ID error
                    if "ya se encuentra registrado" in error_detail.lower():
                        logger.warning(f"Citizen {citizen.id} already exists in MinTIC Hub")
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"El ciudadano con ID {citizen.id} ya se encuentra registrado en la Carpeta Ciudadana del Hub MinTIC",
                        )
                    else:
                        logger.error(f"MinTIC validation error: {error_detail}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Error de validación del Hub MinTIC: {error_detail}",
                        )
                else:
                    # Rollback local registration on any other error
                    logger.error(f"MinTIC returned unexpected status {response.status_code}")
                    await db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Error al registrar en el Hub MinTIC. Status: {response.status_code}",
                    )
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            # Rollback on any unexpected error
            logger.error(f"Error calling MinTIC client service: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error al comunicarse con el servicio MinTIC client: {str(e)}",
            )
        
        # Only commit if MinTIC registration succeeded
        logger.info("Committing citizen to local database...")
        await db.commit()
        await db.refresh(citizen)
        logger.info(f"Citizen {citizen.id} successfully committed to local database")
        
        # Publish event to Service Bus
        try:
            from carpeta_common.message_broker import publish_citizen_registered
            
            await publish_citizen_registered(
                citizen_id=citizen.id,
                name=citizen.name,
                email=citizen.email
            )
            logger.info("Event published to Service Bus")
        except ImportError:
            logger.warning("carpeta_common not installed, skipping event publishing")
        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")

        logger.info(f"=== REGISTER CITIZEN SUCCESS: {citizen.id} ===")
        return citizen
        
    except HTTPException:
        logger.error(f"HTTP Exception in register_citizen")
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Unexpected error in register_citizen: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {str(e)}")
        # Rollback on any unexpected error
        try:
            await db.rollback()
            logger.info("Database rolled back due to error")
        except Exception as rollback_error:
            logger.error(f"Error during rollback: {rollback_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.delete("/unregister", status_code=status.HTTP_200_OK)
async def unregister_citizen(
    data: CitizenUnregister,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Unregister a citizen."""
    logger.info(f"Unregistering citizen: {data.id}")

    try:
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
                        "id": int(citizen.id),
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
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error unregistering citizen {data.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{citizen_id}", response_model=CitizenResponse)
async def get_citizen(
    citizen_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Citizen:
    """Get citizen by ID."""
    try:
        result = await db.execute(select(Citizen).where(Citizen.id == citizen_id))
        citizen = result.scalar_one_or_none()

        if not citizen:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Citizen {citizen_id} not found",
            )

        return citizen
    except Exception as e:
        logger.error(f"Error getting citizen {citizen_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


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



