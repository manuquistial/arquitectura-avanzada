"""MinTIC API router."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.client import MinTICClient
from app.database import get_db
from app.models import (
    AuthenticateDocumentRequest,
    MinTICResponse,
    OperatorInfo,
    RegisterCitizenRequest,
    RegisterOperatorRequest,
    RegisterTransferEndPointRequest,
    SystemOperatorConfigRequest,
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
    try:
        logger.info(f"Registering citizen: {data.id}")
        result = await client.register_citizen(data)
        if not result.success:
            raise HTTPException(status_code=result.status_code, detail=result.message)
        return result
    except Exception as e:
        logger.error(f"Error in register_citizen endpoint: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MinTICResponse:
    """Register operator in MinTIC Hub and persist in database."""
    logger.info(f"Registering operator: {data.name}")
    
    # Register with MinTIC Hub
    result = await client.register_operator(data)
    if not result.success:
        raise HTTPException(status_code=result.status_code, detail=result.message)
    
    # Extract MinTIC operator ID from response
    mintic_operator_id = None
    if result.data and isinstance(result.data, dict):
        mintic_operator_id = result.data.get("idOperator")
    
    if not mintic_operator_id:
        logger.error("❌ No operator ID returned from MinTIC Hub")
        raise HTTPException(status_code=500, detail="No operator ID returned from MinTIC Hub")
    
    # Persist in database
    try:
        from app.database_models import Operator
        import json
        
        # Convert participants list to JSON string
        participants_json = json.dumps(data.participants) if data.participants else None
        
        operator = Operator(
            mintic_operator_id=mintic_operator_id,
            name=data.name,
            address=data.address,
            contact_mail=data.contactMail,
            participants=participants_json,
            is_active=True
        )
        
        db.add(operator)
        await db.commit()
        await db.refresh(operator)
        
        logger.info(f"✅ Operator registered and persisted: {data.name} (MinTIC ID: {mintic_operator_id})")
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to persist operator in database: {e}")
        # Note: We don't raise here because MinTIC registration was successful
        # The operator exists in MinTIC Hub even if our DB save failed
    
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


@router.post("/sync/documents")
async def sync_documents(
    sync_request: dict,
    client: Annotated[MinTICClient, Depends(get_mintic_client)],
) -> dict:
    """Sync documents with MinTIC Hub."""
    logger.info("Starting document sync with MinTIC Hub")
    
    try:
        # Extract sync parameters
        citizen_id = sync_request.get('citizen_id')
        document_ids = sync_request.get('document_ids', [])
        sync_type = sync_request.get('sync_type', 'full')  # full, incremental
        
        if not citizen_id:
            raise HTTPException(
                status_code=400,
                detail="citizen_id is required for document sync"
            )
        
        # Perform document synchronization
        sync_result = await client.sync_citizen_documents(
            citizen_id=citizen_id,
            document_ids=document_ids,
            sync_type=sync_type
        )
        
        return {
            "message": "Document sync completed",
            "citizen_id": citizen_id,
            "synced_documents": sync_result.get('synced_count', 0),
            "failed_documents": sync_result.get('failed_count', 0),
            "sync_timestamp": sync_result.get('timestamp'),
            "details": sync_result.get('details', [])
        }
        
    except Exception as e:
        logger.error(f"Document sync failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document sync failed: {str(e)}"
        )


@router.post("/webhooks/hub-notification")
async def handle_hub_notification(
    notification: dict,
    client: Annotated[MinTICClient, Depends(get_mintic_client)],
) -> dict:
    """Handle notifications from MinTIC Hub."""
    logger.info(f"Received hub notification: {notification.get('type', 'unknown')}")
    
    try:
        notification_type = notification.get('type')
        payload = notification.get('payload', {})
        
        # Process different types of hub notifications
        if notification_type == 'document_authenticated':
            await client.handle_document_authentication(payload)
        elif notification_type == 'citizen_updated':
            await client.handle_citizen_update(payload)
        elif notification_type == 'operator_status_changed':
            await client.handle_operator_status_change(payload)
        elif notification_type == 'transfer_completed':
            await client.handle_transfer_completion(payload)
        else:
            logger.warning(f"Unknown notification type: {notification_type}")
        
        return {
            "message": "Notification processed successfully",
            "notification_type": notification_type,
            "processed_at": client.get_current_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Failed to process hub notification: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process notification: {str(e)}"
        )


@router.get("/sync/status/{citizen_id}")
async def get_sync_status(
    citizen_id: str,
    client: Annotated[MinTICClient, Depends(get_mintic_client)],
) -> dict:
    """Get synchronization status for a citizen."""
    logger.info(f"Getting sync status for citizen: {citizen_id}")
    
    try:
        sync_status = await client.get_citizen_sync_status(citizen_id)
        
        return {
            "citizen_id": citizen_id,
            "last_sync": sync_status.get('last_sync'),
            "sync_status": sync_status.get('status', 'unknown'),
            "documents_synced": sync_status.get('documents_synced', 0),
            "pending_sync": sync_status.get('pending_sync', 0),
            "last_error": sync_status.get('last_error'),
            "next_sync": sync_status.get('next_sync')
        }
        
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sync status: {str(e)}"
        )


@router.post("/validate/document")
async def validate_document_with_hub(
    validation_request: dict,
    client: Annotated[MinTICClient, Depends(get_mintic_client)],
) -> dict:
    """Validate document with MinTIC Hub."""
    logger.info("Validating document with MinTIC Hub")
    
    try:
        document_id = validation_request.get('document_id')
        document_hash = validation_request.get('document_hash')
        citizen_id = validation_request.get('citizen_id')
        
        if not all([document_id, document_hash, citizen_id]):
            raise HTTPException(
                status_code=400,
                detail="document_id, document_hash, and citizen_id are required"
            )
        
        # Perform document validation with hub
        validation_result = await client.validate_document_with_hub(
            document_id=document_id,
            document_hash=document_hash,
            citizen_id=citizen_id
        )
        
        return {
            "document_id": document_id,
            "is_valid": validation_result.get('is_valid', False),
            "validation_timestamp": validation_result.get('timestamp'),
            "hub_response": validation_result.get('hub_response'),
            "validation_details": validation_result.get('details', {})
        }
        
    except Exception as e:
        logger.error(f"Document validation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document validation failed: {str(e)}"
        )


# Operator Management Endpoints
@router.get("/operators/local")
async def get_local_operators(
    db: Annotated[AsyncSession, Depends(get_db)],
    active_only: bool = True
) -> dict:
    """Get all operators from local database."""
    try:
        from app.database_models import Operator
        
        query = select(Operator)
        if active_only:
            query = query.where(Operator.is_active == True)
        query = query.order_by(Operator.created_at.desc())
        
        result = await db.execute(query)
        operators = result.scalars().all()
        
        return {
            "operators": [
                {
                    "id": op.id,
                    "mintic_operator_id": op.mintic_operator_id,
                    "name": op.name,
                    "address": op.address,
                    "contact_mail": op.contact_mail,
                    "participants": json.loads(op.participants) if op.participants else [],
                    "is_active": op.is_active,
                    "created_at": op.created_at.isoformat(),
                    "updated_at": op.updated_at.isoformat()
                }
                for op in operators
            ],
            "total": len(operators)
        }
        
    except Exception as e:
        logger.error(f"Failed to get local operators: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get operators: {str(e)}"
        )


@router.get("/operators/local/{operator_id}")
async def get_local_operator(
    operator_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    """Get operator by ID from local database."""
    try:
        from app.database_models import Operator
        
        result = await db.execute(
            select(Operator).where(Operator.id == operator_id)
        )
        operator = result.scalar_one_or_none()
        
        if not operator:
            raise HTTPException(
                status_code=404,
                detail=f"Operator with ID {operator_id} not found"
            )
        
        return {
            "id": operator.id,
            "mintic_operator_id": operator.mintic_operator_id,
            "name": operator.name,
            "address": operator.address,
            "contact_mail": operator.contact_mail,
            "participants": json.loads(operator.participants) if operator.participants else [],
            "is_active": operator.is_active,
            "created_at": operator.created_at.isoformat(),
            "updated_at": operator.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get operator {operator_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get operator: {str(e)}"
        )


@router.put("/operators/local/{operator_id}/deactivate")
async def deactivate_operator(
    operator_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    """Deactivate operator."""
    try:
        from app.database_models import Operator
        
        result = await db.execute(
            select(Operator).where(Operator.id == operator_id)
        )
        operator = result.scalar_one_or_none()
        
        if not operator:
            raise HTTPException(
                status_code=404,
                detail=f"Operator with ID {operator_id} not found"
            )
        
        operator.is_active = False
        await db.commit()
        
        logger.info(f"✅ Operator deactivated: {operator.name}")
        return {"message": f"Operator {operator_id} deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to deactivate operator {operator_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deactivate operator: {str(e)}"
        )


@router.delete("/operators/local/{operator_id}")
async def delete_operator(
    operator_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    """Delete operator."""
    try:
        from app.database_models import Operator
        
        result = await db.execute(
            select(Operator).where(Operator.id == operator_id)
        )
        operator = result.scalar_one_or_none()
        
        if not operator:
            raise HTTPException(
                status_code=404,
                detail=f"Operator with ID {operator_id} not found"
            )
        
        await db.delete(operator)
        await db.commit()
        
        logger.info(f"✅ Operator deleted: {operator.name}")
        return {"message": f"Operator {operator_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete operator {operator_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete operator: {str(e)}"
        )


# ========================================
# System Configuration Endpoints
# ========================================

@router.get("/system-config/operator")
async def get_system_operator_config(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    """Get the system operator configuration (operatorId and operatorName).
    
    This is the operator configuration that should be used throughout
    the entire system for all MinTIC Hub interactions.
    """
    try:
        from app.database_models import SystemConfig
        
        # Get operator_id
        result = await db.execute(
            select(SystemConfig).filter(
                SystemConfig.config_key == "system_operator_id"
            )
        )
        operator_id_config = result.scalar_one_or_none()
        
        # Get operator_name
        result = await db.execute(
            select(SystemConfig).filter(
                SystemConfig.config_key == "system_operator_name"
            )
        )
        operator_name_config = result.scalar_one_or_none()
        
        # Return configured values or defaults
        operator_id = operator_id_config.config_value if operator_id_config else None
        operator_name = operator_name_config.config_value if operator_name_config else None
        
        # Fallback to configured defaults if not set
        if not operator_id or not operator_name:
            from app.config import get_config
            config = get_config()
            operator_id = operator_id or config.mintic_operator_id
            operator_name = operator_name or config.mintic_operator_name
        
        return {
            "operator_id": operator_id,
            "operator_name": operator_name,
            "is_configured": operator_id_config is not None and operator_name_config is not None
        }
        
    except Exception as e:
        logger.error(f"Failed to get system operator config: {e}")
        # Fallback to configured defaults on error
        from app.config import get_config
        config = get_config()
        return {
            "operator_id": config.mintic_operator_id,
            "operator_name": config.mintic_operator_name,
            "is_configured": False
        }


@router.put("/system-config/operator")
async def update_system_operator_config(
    config_data: SystemOperatorConfigRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    """Update the system operator configuration.
    
    This sets the operatorId and operatorName that will be used
    throughout the entire system.
    
    Request body:
    {
        "operator_id": "OP-12345",
        "operator_name": "Carpeta Ciudadana",
        "updated_by": "admin@carpeta.com" (optional)
    }
    """
    try:
        from app.database_models import SystemConfig
        from datetime import datetime
        
        operator_id = config_data.operator_id
        operator_name = config_data.operator_name
        updated_by = config_data.updated_by
        
        if not operator_id or not operator_name:
            raise HTTPException(
                status_code=400,
                detail="operator_id and operator_name are required"
            )
        
        # Update or create operator_id config
        result = await db.execute(
            select(SystemConfig).filter(
                SystemConfig.config_key == "system_operator_id"
            )
        )
        operator_id_config = result.scalar_one_or_none()
        
        if operator_id_config:
            operator_id_config.config_value = operator_id
            operator_id_config.updated_at = datetime.utcnow()
            operator_id_config.updated_by = updated_by
        else:
            operator_id_config = SystemConfig(
                config_key="system_operator_id",
                config_value=operator_id,
                description="System operator ID for MinTIC Hub interactions",
                updated_by=updated_by
            )
            db.add(operator_id_config)
        
        # Update or create operator_name config
        result = await db.execute(
            select(SystemConfig).filter(
                SystemConfig.config_key == "system_operator_name"
            )
        )
        operator_name_config = result.scalar_one_or_none()
        
        if operator_name_config:
            operator_name_config.config_value = operator_name
            operator_name_config.updated_at = datetime.utcnow()
            operator_name_config.updated_by = updated_by
        else:
            operator_name_config = SystemConfig(
                config_key="system_operator_name",
                config_value=operator_name,
                description="System operator name for MinTIC Hub interactions",
                updated_by=updated_by
            )
            db.add(operator_name_config)
        
        await db.commit()
        
        logger.info(f"✅ System operator config updated: {operator_name} (ID: {operator_id})")
        
        return {
            "message": "System operator configuration updated successfully",
            "operator_id": operator_id,
            "operator_name": operator_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update system operator config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update system operator config: {str(e)}"
        )

