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
    
    # Get operator_id and operator_name from system config if not provided
    operator_id = citizen_data.operator_id
    operator_name = citizen_data.operator_name
    
    if not operator_id or not operator_name:
        logger.info("Operator ID/Name not provided, fetching from system config...")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                config_response = await client.get(
                    f"{settings.mintic_client_url}/api/mintic/system-config/operator"
                )
                if config_response.status_code == 200:
                    config_data = config_response.json()
                    operator_id = operator_id or config_data.get("operator_id")
                    operator_name = operator_name or config_data.get("operator_name")
                    logger.info(f"✅ Fetched operator config: {operator_name} (ID: {operator_id})")
                else:
                    logger.warning(f"⚠️  Failed to fetch system config: {config_response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️  Error fetching system config: {e}")
            # Use defaults if config fetch fails
            if not operator_id:
                operator_id = "operator-demo"
            if not operator_name:
                operator_name = "Carpeta Ciudadana Demo"
    
    logger.info(f"Using Operator ID: {operator_id}")
    logger.info(f"Using Operator Name: {operator_name}")

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
            operator_id=operator_id,
            operator_name=operator_name,
        )

        db.add(citizen)
        await db.flush()  # Flush but don't commit yet
        logger.info(f"Citizen {citizen.id} created in local database (flushed)")

        # Register citizen in MinTIC Hub via mintic_client service (simple facade)
        logger.info(f"Calling MinTIC service at: {settings.mintic_client_url}/api/mintic/register-citizen")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
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
        except httpx.TimeoutException as e:
            # Timeout error - service might be slow or unavailable
            logger.error(f"Timeout calling MinTIC client service: {e}")
            logger.error(f"Service URL: {settings.mintic_client_url}/api/mintic/register-citizen")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"El servicio MinTIC client no respondió a tiempo. Por favor intenta nuevamente.",
            )
        except httpx.ConnectError as e:
            # Connection error - service might be down
            logger.error(f"Cannot connect to MinTIC client service: {e}")
            logger.error(f"Service URL: {settings.mintic_client_url}/api/mintic/register-citizen")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No se pudo conectar con el servicio MinTIC client. El servicio puede estar temporalmente no disponible.",
            )
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
        
        # Create auth user with password
        logger.info(f"Creating auth user for citizen {citizen.id}...")
        logger.info(f"Auth service URL: {settings.auth_service_url}")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Split name into given_name and family_name
                name_parts = citizen.name.split(maxsplit=1)
                given_name = name_parts[0] if name_parts else ""
                family_name = name_parts[1] if len(name_parts) > 1 else ""
                
                auth_payload = {
                    "email": citizen.email,
                    "password": citizen_data.password,
                    "name": citizen.name,
                    "given_name": given_name,
                    "family_name": family_name
                }
                logger.info(f"Auth service payload: {auth_payload['email']} (password hidden)")
                
                auth_url = f"{settings.auth_service_url}/api/auth/register"
                logger.info(f"Calling auth service: {auth_url}")
                
                auth_response = await client.post(
                    auth_url,
                    json=auth_payload
                )
                
                logger.info(f"Auth service response status: {auth_response.status_code}")
                
                if auth_response.status_code == 200:
                    logger.info(f"✅ Auth user created for citizen {citizen.id}")
                    auth_user_data = auth_response.json()
                    auth_user_id = auth_user_data.get("id")
                    
                    # Now update the user in citizen service's users table with citizen_id
                    if auth_user_id:
                        logger.info(f"Linking user {auth_user_id} to citizen {citizen.id}...")
                        from sqlalchemy import text
                        update_user_query = text("""
                            UPDATE users 
                            SET citizen_id = :citizen_id
                            WHERE CAST(id AS TEXT) = CAST(:user_id AS TEXT) OR email = :email
                        """)
                        result = await db.execute(update_user_query, {
                            "citizen_id": citizen.id,
                            "user_id": auth_user_id,
                            "email": citizen.email
                        })
                        if result.rowcount > 0:
                            logger.info(f"✅ User {auth_user_id} linked to citizen {citizen.id}")
                        else:
                            logger.warning(f"⚠️  User {auth_user_id} not found in users table to link to citizen")
                elif auth_response.status_code == 400:
                    # User might already exist, log warning but don't fail
                    error_data = auth_response.json() if auth_response.headers.get("content-type") == "application/json" else {}
                    error_detail = error_data.get("detail", auth_response.text)
                    logger.warning(f"⚠️  Auth user might already exist: {error_detail}")
                    
                    # Try to link existing user to citizen
                    try:
                        from sqlalchemy import text
                        update_user_query = text("""
                            UPDATE users 
                            SET citizen_id = :citizen_id
                            WHERE email = :email
                        """)
                        result = await db.execute(update_user_query, {
                            "citizen_id": citizen.id,
                            "email": citizen.email
                        })
                        if result.rowcount > 0:
                            logger.info(f"✅ Linked existing user to citizen {citizen.id}")
                        await db.commit()
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to link user to citizen: {e}")
                else:
                    # Log error but don't fail citizen registration
                    logger.warning(f"⚠️  Failed to create auth user: {auth_response.status_code} - {auth_response.text}")
        except httpx.ConnectError as e:
            # Connection error - service might not be available
            logger.warning(f"⚠️  Cannot connect to auth service at {settings.auth_service_url}: {e}")
        except Exception as e:
            # Log error but don't fail citizen registration
            logger.warning(f"⚠️  Error creating auth user: {e}")
        
        # Publish event to Service Bus
        try:
            from carpeta_common.bus import publish_citizen_registered
            
            await publish_citizen_registered(
                citizen_id=citizen.id,
                name=citizen.name,
                email=citizen.email,
                operator_id=str(citizen.operator_id) if citizen.operator_id else "carpeta-ciudadana"
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


@router.delete("/unregister", status_code=status.HTTP_200_OK)
async def unregister_citizen(
    data: CitizenUnregister,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Unregister a citizen.
    
    This endpoint:
    1. Finds the user by user.id (sent from frontend)
    2. Gets the citizen_id from the user
    3. Finds the citizen by citizen_id
    4. Deletes the user completely (hard delete)
    5. Deletes the citizen completely (hard delete)
    6. Unregisters from MinTIC Hub using citizen.id
    7. Publishes event to Service Bus
    
    This is a complete deletion (hard delete), not a soft delete.
    """
    logger.info(f"=== UNREGISTER CITIZEN START ===")
    logger.info(f"Received unregister request with ID: {data.id} (type: {type(data.id)})")
    logger.info(f"This should be a user.id from the users table")

    try:
        from sqlalchemy import text
        
        # Step 1: Find the user by user.id (this is what the frontend sends)
        logger.info(f"Step 1: Searching for user with ID: {data.id} in users table...")
        user_query = text("""
        SELECT id, email, citizen_id FROM users 
        WHERE CAST(id AS TEXT) = CAST(:user_id AS TEXT)
        LIMIT 1
        """)
        user_result = await db.execute(user_query, {"user_id": data.id})
        user_row = user_result.fetchone()
            
        if not user_row:
            logger.error(f"❌ User not found with ID: {data.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found with ID: {data.id}",
            )
        
        logger.info(f"✅ User found: ID={user_row.id}, Email={user_row.email}, Citizen ID={user_row.citizen_id}")
        
        # Step 2: Get citizen_id from user
        if not user_row.citizen_id:
            logger.error(f"❌ User {user_row.id} does not have a citizen_id linked")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {data.id} does not have a citizen linked. Cannot unregister.",
            )
        
        citizen_id = user_row.citizen_id
        logger.info(f"Step 2: Found citizen_id: {citizen_id} from user")
        
        # Step 3: Find the citizen by citizen_id
        logger.info(f"Step 3: Searching for citizen with ID: {citizen_id}...")
        result = await db.execute(select(Citizen).where(Citizen.id == citizen_id))
        citizen = result.scalar_one_or_none()
        
        if not citizen:
            logger.error(f"❌ Citizen not found with ID: {citizen_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Citizen not found with ID: {citizen_id}",
            )
        
        logger.info(f"✅ Citizen found: ID={citizen.id}, Email={citizen.email}, Name={citizen.name}")
        
        # Step 4: Save citizen info before deletion (needed for MinTIC unregister and Service Bus)
        citizen_id_for_mintic = citizen.id
        citizen_email_for_event = citizen.email
        citizen_operator_id_for_event = citizen.operator_id
        
        # Step 5: Get operator info for MinTIC unregister (before deleting)
        operator_id = citizen.operator_id
        operator_name = citizen.operator_name
        
        if not operator_id or not operator_name:
            logger.info("Citizen doesn't have operator info, fetching from system config...")
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                    config_response = await client.get(
                        f"{settings.mintic_client_url}/api/mintic/system-config/operator"
                    )
                    if config_response.status_code == 200:
                        config_data = config_response.json()
                        operator_id = operator_id or config_data.get("operator_id")
                        operator_name = operator_name or config_data.get("operator_name")
                        logger.info(f"✅ Fetched operator config: {operator_name} (ID: {operator_id})")
                    else:
                        logger.warning(f"⚠️  Failed to fetch system config: {config_response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️  Error fetching system config: {e}")
                if not operator_id:
                    operator_id = "operator-demo"
                if not operator_name:
                    operator_name = "Carpeta Ciudadana Demo"
        
        # Step 6: Delete related records first (to avoid foreign key violations)
        logger.info(f"Step 6: Deleting related records for user {user_row.id}...")
        
        # Use savepoints to handle errors without aborting the entire transaction
        # Delete audit_logs entries (if table exists)
        try:
            # Create a savepoint before attempting to delete audit_logs
            await db.execute(text("SAVEPOINT before_delete_audit_logs"))
            delete_audit_logs_query = text("""
                DELETE FROM audit_logs 
                WHERE CAST(user_id AS TEXT) = CAST(:user_id AS TEXT)
            """)
            audit_logs_result = await db.execute(delete_audit_logs_query, {"user_id": data.id})
            if audit_logs_result.rowcount > 0:
                logger.info(f"✅ Deleted {audit_logs_result.rowcount} audit_logs entries for user {user_row.id}")
            # Release savepoint if successful
            await db.execute(text("RELEASE SAVEPOINT before_delete_audit_logs"))
        except Exception as e:
            # Table might not exist or error occurred, rollback to savepoint and continue
            logger.debug(f"Could not delete audit_logs (table may not exist): {e}")
            try:
                await db.execute(text("ROLLBACK TO SAVEPOINT before_delete_audit_logs"))
            except Exception as rollback_error:
                # If savepoint doesn't exist, try full rollback
                logger.debug(f"Could not rollback to savepoint: {rollback_error}")
                try:
                    await db.rollback()
                except Exception as full_rollback_error:
                    logger.debug(f"Full rollback also failed: {full_rollback_error}")
        
        # Delete audit_events entries (if table exists)
        try:
            # Create a savepoint before attempting to delete audit_events
            await db.execute(text("SAVEPOINT before_delete_audit_events"))
            delete_audit_events_query = text("""
                DELETE FROM audit_events 
                WHERE user_id = :user_id
            """)
            audit_events_result = await db.execute(delete_audit_events_query, {"user_id": str(data.id)})
            if audit_events_result.rowcount > 0:
                logger.info(f"✅ Deleted {audit_events_result.rowcount} audit_events entries for user {user_row.id}")
            # Release savepoint if successful
            await db.execute(text("RELEASE SAVEPOINT before_delete_audit_events"))
        except Exception as e:
            # Table might not exist or error occurred, rollback to savepoint and continue
            logger.debug(f"Could not delete audit_events (table may not exist): {e}")
            try:
                await db.execute(text("ROLLBACK TO SAVEPOINT before_delete_audit_events"))
            except Exception as rollback_error:
                # If savepoint doesn't exist, try full rollback
                logger.debug(f"Could not rollback to savepoint: {rollback_error}")
                try:
                    await db.rollback()
                except Exception as full_rollback_error:
                    logger.debug(f"Full rollback also failed: {full_rollback_error}")
        
        # Step 7: Delete user completely (hard delete)
        logger.info(f"Step 7: Deleting user {user_row.id} completely (hard delete)...")
        delete_user_query = text("""
            DELETE FROM users 
            WHERE CAST(id AS TEXT) = CAST(:user_id AS TEXT)
        """)
        user_delete_result = await db.execute(delete_user_query, {"user_id": data.id})
        if user_delete_result.rowcount > 0:
            logger.info(f"✅ User {user_row.id} deleted completely")
        else:
            logger.warning(f"⚠️  No user was deleted (may have already been deleted)")
        
        # Step 8: Delete citizen completely (hard delete)
        logger.info(f"Step 8: Deleting citizen {citizen.id} completely (hard delete)...")
        delete_citizen_query = text("""
            DELETE FROM citizens 
            WHERE id = :citizen_id
        """)
        citizen_delete_result = await db.execute(delete_citizen_query, {"citizen_id": citizen.id})
        if citizen_delete_result.rowcount > 0:
            logger.info(f"✅ Citizen {citizen.id} deleted completely")
        else:
            logger.warning(f"⚠️  No citizen was deleted (may have already been deleted)")
        
        # Commit the deletions
        try:
            await db.commit()
            logger.info(f"✅ User and citizen deleted successfully")
        except Exception as commit_error:
            logger.error(f"Failed to commit deletions: {commit_error}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user and citizen: {str(commit_error)}"
            )

        # Step 9: Unregister from MinTIC Hub (async, non-blocking)
        # Use saved operator_id and operator_name (already fetched before deletion)
        logger.info(f"Step 9: Unregistering citizen {citizen_id_for_mintic} from MinTIC Hub...")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                import json as json_lib

                payload = {
                    "id": int(citizen_id_for_mintic),  # Use saved citizen.id (documento de 10 dígitos)
                    "operatorId": operator_id,
                    "operatorName": operator_name,
                }

                mintic_endpoint = f"{settings.mintic_client_url}/api/mintic/unregister-citizen"
                logger.info("Calling MinTIC client endpoint: %s", mintic_endpoint)

                response = await client.request(
                    "DELETE",
                    mintic_endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    logger.info(f"Citizen {citizen_id_for_mintic} unregistered from MinTIC Hub")
                else:
                    logger.warning(
                        "Failed to unregister from MinTIC Hub: %s (status: %s, payload: %s)",
                        response.text,
                        response.status_code,
                        json_lib.dumps(payload),
                    )
        except Exception as e:
            logger.error(f"Error calling MinTIC client: {e}", exc_info=True)
        
        # Publish event to Service Bus
        try:
            from carpeta_common.bus import publish_citizen_unregistered
            
            await publish_citizen_unregistered(
                citizen_id=citizen_id_for_mintic,  # Use saved citizen.id
                email=citizen_email_for_event,  # Use saved citizen.email
                operator_id=str(citizen_operator_id_for_event) if citizen_operator_id_for_event else "carpeta-ciudadana"
            )
            logger.info("Event published to Service Bus")
        except ImportError:
            logger.warning("carpeta_common not installed, skipping event publishing")
        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")

        return {"message": f"Citizen {data.id} and associated user unregistered successfully"}
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error unregistering citizen {data.id}: {e}")
        await db.rollback()
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



