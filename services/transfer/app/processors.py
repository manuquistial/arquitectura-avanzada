"""Event processors for transfer operations."""

import logging
from typing import Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Transfer, TransferStatus
from app.saga import TransferSaga

logger = logging.getLogger(__name__)


class TransferEventProcessor:
    """Processes transfer events for async processing."""
    
    async def process_transfer_requested(self, event_data: Dict[str, Any]) -> bool:
        """Process transfer.requested event.
        
        Executes transfer saga asynchronously.
        
        Args:
            event_data: Event data with 'event_type', 'data', 'timestamp', etc.
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            data = event_data.get("data", {})
            transfer_id = data.get("transfer_id")
            citizen_id = data.get("citizen_id")
            source_operator = data.get("source_operator")
            destination_operator = data.get("destination_operator")
            destination_url = data.get("destination_url")
            
            logger.info(
                f"🚚 Processing transfer.requested: transfer_id={transfer_id}, "
                f"citizen_id={citizen_id}, source={source_operator}, "
                f"destination={destination_operator}"
            )
            
            # Get transfer record from database
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Transfer).where(Transfer.id == transfer_id)
                )
                transfer = result.scalar_one_or_none()
                
                if not transfer:
                    logger.warning(f"Transfer {transfer_id} not found in database")
                    return False
                
                # Execute saga asynchronously
                try:
                    saga = TransferSaga(
                        transfer_id=transfer.id,
                        citizen_id=transfer.citizen_id,
                        source_operator=source_operator or transfer.source_operator_id or "unknown",
                        destination_operator=destination_operator or transfer.destination_operator_id or "unknown",
                        destination_url=destination_url or transfer.confirm_url or ""
                    )
                    
                    success = await saga.execute()
                    
                    if success:
                        # Update transfer status
                        transfer.status = TransferStatus.SUCCESS
                        await db.commit()
                        logger.info(f"✅ Transfer saga completed successfully: {transfer_id}")
                    else:
                        # Update transfer status to failed
                        transfer.status = TransferStatus.FAILED
                        transfer.error_message = saga.error
                        await db.commit()
                        logger.warning(f"⚠️  Transfer saga failed: {transfer_id}, error: {saga.error}")
                    
                    return success
                    
                except Exception as saga_error:
                    logger.error(f"❌ Error executing saga: {saga_error}", exc_info=True)
                    # Update transfer status to failed
                    transfer.status = TransferStatus.FAILED
                    transfer.error_message = str(saga_error)
                    await db.commit()
                    return False
            
        except Exception as e:
            logger.error(f"❌ Error processing transfer.requested: {e}", exc_info=True)
            return False
    
    async def process_transfer_confirmed(self, event_data: Dict[str, Any]) -> bool:
        """Process transfer.confirmed event.
        
        Updates transfer status and performs post-confirmation actions.
        
        Args:
            event_data: Event data with 'event_type', 'data', 'timestamp', etc.
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            data = event_data.get("data", {})
            transfer_id = data.get("transfer_id")
            citizen_id = data.get("citizen_id")
            success = data.get("success", True)
            
            logger.info(
                f"✅ Processing transfer.confirmed: transfer_id={transfer_id}, "
                f"citizen_id={citizen_id}, success={success}"
            )
            
            # Update transfer record in database
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Transfer).where(Transfer.id == transfer_id)
                )
                transfer = result.scalar_one_or_none()
                
                if transfer:
                    if success:
                        transfer.status = TransferStatus.CONFIRMED
                        # confirmed_at should already be set, but ensure it
                        from datetime import datetime
                        if not transfer.confirmed_at:
                            transfer.confirmed_at = datetime.utcnow()
                    else:
                        transfer.status = TransferStatus.FAILED
                        transfer.error_message = data.get("error_message", "Transfer confirmation failed")
                    
                    await db.commit()
                    logger.info(f"✅ Updated transfer status: {transfer_id}")
                
                # TODO: Future enhancements
                # 1. Notificar al ciudadano (via Notification Service)
                # 2. Actualizar metadata
                # 3. Limpiar cache relacionado
            
            logger.info(
                f"✅ Successfully processed transfer.confirmed: "
                f"transfer_id={transfer_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing transfer.confirmed: {e}", exc_info=True)
            return False
    
    async def process_transfer_notification(self, event_data: Dict[str, Any]) -> bool:
        """Process transfer.notification event.
        
        Handles transfer notifications (status updates, etc.).
        
        Args:
            event_data: Event data with 'event_type', 'data', 'timestamp', etc.
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            data = event_data.get("data", {})
            transfer_id = data.get("transfer_id")
            citizen_id = data.get("citizen_id")
            status = data.get("status")
            message = data.get("message")
            
            logger.info(
                f"📬 Processing transfer.notification: transfer_id={transfer_id}, "
                f"citizen_id={citizen_id}, status={status}, message={message}"
            )
            
            # TODO: Future enhancements
            # 1. Enviar notificación al ciudadano (via Notification Service)
            # 2. Actualizar frontend (WebSocket)
            # 3. Registrar en auditoría
            
            logger.info(
                f"✅ Successfully processed transfer.notification: "
                f"transfer_id={transfer_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing transfer.notification: {e}", exc_info=True)
            return False

