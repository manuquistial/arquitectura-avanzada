"""Event projector - Projects Service Bus events to read models."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict

from app.config import Settings
from app.models import ReadDocument, ReadTransfer

logger = logging.getLogger(__name__)


class EventProjector:
    """Projects Service Bus events to optimized read models (CQRS)."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.running = False
        
        # Initialize Service Bus client (if available)
        try:
            from azure.servicebus.aio import ServiceBusClient
            self.servicebus_client = ServiceBusClient.from_connection_string(
                settings.servicebus_connection_string
            )
            logger.info("✅ Service Bus client initialized")
        except ImportError:
            logger.error("❌ azure-servicebus not installed")
            self.servicebus_client = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize Service Bus: {e}")
            self.servicebus_client = None
    
    async def start(self):
        """Start consuming events from multiple queues."""
        if not self.servicebus_client:
            logger.error("❌ Service Bus client not available")
            return
        
        self.running = True
        logger.info("Starting event projectors for CQRS read models...")
        
        try:
            # Start consumers in parallel with enhanced error handling
            results = await asyncio.gather(
                self.consume_citizen_registered(),
                self.consume_document_uploaded(),
                self.consume_document_authenticated(),
                self.consume_transfer_requested(),
                self.consume_transfer_confirmed(),
                return_exceptions=True
            )
            
            # Log any exceptions that occurred
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    consumer_names = [
                        "citizen_registered", "document_uploaded", "document_authenticated",
                        "transfer_requested", "transfer_confirmed"
                    ]
                    logger.error(f"❌ Consumer {consumer_names[i]} failed: {result}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to start event projectors: {e}")
            self.running = False
            raise
    
    async def consume_citizen_registered(self):
        """
        Consume citizen.registered events.
        
        Updates citizen_name in read_documents (denormalization).
        """
        queue_name = "citizen-registered"
        logger.info(f"📥 Starting consumer: {queue_name}")
        
        try:
            async with self.servicebus_client:
                receiver = self.servicebus_client.get_queue_receiver(queue_name)
                
                async with receiver:
                    while self.running:
                        try:
                            messages = await receiver.receive_messages(
                                max_message_count=10,
                                max_wait_time=60
                            )
                            
                            for msg in messages:
                                try:
                                    # Parse event
                                    event = json.loads(str(msg))
                                    await self._project_citizen_registered(event)
                                    
                                    # Complete message
                                    await receiver.complete_message(msg)
                                    
                                except json.JSONDecodeError as e:
                                    logger.error(f"❌ Invalid JSON in citizen.registered message: {e}")
                                    await receiver.dead_letter_message(msg, reason=f"Invalid JSON: {str(e)}")
                                except Exception as e:
                                    logger.error(f"❌ Error projecting citizen.registered: {e}")
                                    await receiver.dead_letter_message(msg, reason=str(e))
                        
                        except asyncio.CancelledError:
                            logger.info(f"🛑 Consumer {queue_name} cancelled")
                            break
                        except Exception as e:
                            logger.error(f"❌ Consumer {queue_name} error: {e}")
                            await asyncio.sleep(5)
                            
        except Exception as e:
            logger.error(f"❌ Failed to start consumer {queue_name}: {e}")
            raise
    
    async def consume_document_uploaded(self):
        """
        Consume document.uploaded events.
        
        Creates entry in read_documents.
        """
        queue_name = "document-uploaded"
        logger.info(f"📥 Starting consumer: {queue_name}")
        
        try:
            async with self.servicebus_client:
                receiver = self.servicebus_client.get_queue_receiver(queue_name)
                
                async with receiver:
                    while self.running:
                        try:
                            messages = await receiver.receive_messages(
                                max_message_count=10,
                                max_wait_time=60
                            )
                            
                            for msg in messages:
                                try:
                                    event = json.loads(str(msg))
                                    await self._project_document_uploaded(event)
                                    await receiver.complete_message(msg)
                                except json.JSONDecodeError as e:
                                    logger.error(f"❌ Invalid JSON in document.uploaded message: {e}")
                                    await receiver.dead_letter_message(msg, reason=f"Invalid JSON: {str(e)}")
                                except Exception as e:
                                    logger.error(f"❌ Error projecting document.uploaded: {e}")
                                    await receiver.dead_letter_message(msg, reason=str(e))
                        
                        except asyncio.CancelledError:
                            logger.info(f"🛑 Consumer {queue_name} cancelled")
                            break
                        except Exception as e:
                            logger.error(f"❌ Consumer {queue_name} error: {e}")
                            await asyncio.sleep(5)
                            
        except Exception as e:
            logger.error(f"❌ Failed to start consumer {queue_name}: {e}")
            raise
    
    async def consume_document_authenticated(self):
        """
        Consume document.authenticated events.
        
        Updates is_authenticated in read_documents.
        """
        queue_name = "document-authenticated"
        logger.info(f"📥 Starting consumer: {queue_name}")
        
        try:
            async with self.servicebus_client:
                receiver = self.servicebus_client.get_queue_receiver(queue_name)
                
                async with receiver:
                    while self.running:
                        try:
                            messages = await receiver.receive_messages(
                                max_message_count=10,
                                max_wait_time=60
                            )
                            
                            for msg in messages:
                                try:
                                    event = json.loads(str(msg))
                                    await self._project_document_authenticated(event)
                                    await receiver.complete_message(msg)
                                except json.JSONDecodeError as e:
                                    logger.error(f"❌ Invalid JSON in document.authenticated message: {e}")
                                    await receiver.dead_letter_message(msg, reason=f"Invalid JSON: {str(e)}")
                                except Exception as e:
                                    logger.error(f"❌ Error projecting document.authenticated: {e}")
                                    await receiver.dead_letter_message(msg, reason=str(e))
                        
                        except asyncio.CancelledError:
                            logger.info(f"🛑 Consumer {queue_name} cancelled")
                            break
                        except Exception as e:
                            logger.error(f"❌ Consumer {queue_name} error: {e}")
                            await asyncio.sleep(5)
                            
        except Exception as e:
            logger.error(f"❌ Failed to start consumer {queue_name}: {e}")
            raise
    
    async def consume_transfer_requested(self):
        """
        Consume transfer.requested events.
        
        Creates entry in read_transfers.
        """
        queue_name = "transfer-requested"
        logger.info(f"📥 Starting consumer: {queue_name}")
        
        try:
            async with self.servicebus_client:
                receiver = self.servicebus_client.get_queue_receiver(queue_name)
                
                async with receiver:
                    while self.running:
                        try:
                            messages = await receiver.receive_messages(
                                max_message_count=10,
                                max_wait_time=60
                            )
                            
                            for msg in messages:
                                try:
                                    event = json.loads(str(msg))
                                    await self._project_transfer_requested(event)
                                    await receiver.complete_message(msg)
                                except json.JSONDecodeError as e:
                                    logger.error(f"❌ Invalid JSON in transfer.requested message: {e}")
                                    await receiver.dead_letter_message(msg, reason=f"Invalid JSON: {str(e)}")
                                except Exception as e:
                                    logger.error(f"❌ Error projecting transfer.requested: {e}")
                                    await receiver.dead_letter_message(msg, reason=str(e))
                        
                        except asyncio.CancelledError:
                            logger.info(f"🛑 Consumer {queue_name} cancelled")
                            break
                        except Exception as e:
                            logger.error(f"❌ Consumer {queue_name} error: {e}")
                            await asyncio.sleep(5)
                            
        except Exception as e:
            logger.error(f"❌ Failed to start consumer {queue_name}: {e}")
            raise
    
    async def consume_transfer_confirmed(self):
        """
        Consume transfer.confirmed events.
        
        Updates transfer status in read_transfers.
        """
        queue_name = "transfer-confirmed"
        logger.info(f"📥 Starting consumer: {queue_name}")
        
        try:
            async with self.servicebus_client:
                receiver = self.servicebus_client.get_queue_receiver(queue_name)
                
                async with receiver:
                    while self.running:
                        try:
                            messages = await receiver.receive_messages(
                                max_message_count=10,
                                max_wait_time=60
                            )
                            
                            for msg in messages:
                                try:
                                    event = json.loads(str(msg))
                                    await self._project_transfer_confirmed(event)
                                    await receiver.complete_message(msg)
                                except json.JSONDecodeError as e:
                                    logger.error(f"❌ Invalid JSON in transfer.confirmed message: {e}")
                                    await receiver.dead_letter_message(msg, reason=f"Invalid JSON: {str(e)}")
                                except Exception as e:
                                    logger.error(f"❌ Error projecting transfer.confirmed: {e}")
                                    await receiver.dead_letter_message(msg, reason=str(e))
                        
                        except asyncio.CancelledError:
                            logger.info(f"🛑 Consumer {queue_name} cancelled")
                            break
                        except Exception as e:
                            logger.error(f"❌ Consumer {queue_name} error: {e}")
                            await asyncio.sleep(5)
                            
        except Exception as e:
            logger.error(f"❌ Failed to start consumer {queue_name}: {e}")
            raise
    
    # Projection methods
    
    async def _project_citizen_registered(self, event: Dict[str, Any]):
        """Update citizen_name in all read_documents for this citizen."""
        try:
            from app.database import get_db
            from sqlalchemy import update
            
            data = event.get('data', {})
            citizen_id = data.get('citizen_id')
            citizen_name = data.get('name')
            
            if not citizen_id or not citizen_name:
                logger.warning(f"Invalid citizen.registered event: {event}")
                return
            
            # Update all read_documents for this citizen
            async for db in get_db():
                try:
                    await db.execute(
                        update(ReadDocument)
                        .where(ReadDocument.citizen_id == citizen_id)
                        .values(citizen_name=citizen_name)
                    )
                    await db.commit()
                    
                    logger.info(f"Updated citizen_name for citizen {citizen_id} in read_documents")
                    
                    # Invalidate cache for this citizen
                    try:
                        from app.services.redis_client import get_redis_client
                        redis_client = await get_redis_client(self.settings)
                        if redis_client:
                            await redis_client.invalidate_citizen_cache(citizen_id)
                    except Exception as cache_error:
                        logger.warning(f"Failed to invalidate cache: {cache_error}")
                    
                    break
                    
                except Exception as e:
                    logger.error(f"Failed to update citizen_name: {e}")
                    await db.rollback()
                finally:
                    await db.close()
                    
        except Exception as e:
            logger.error(f"Error projecting citizen.registered: {e}")
    
    async def _project_document_uploaded(self, event: Dict[str, Any]):
        """Create entry in read_documents."""
        try:
            from app.database import get_db
            
            data = event.get('data', {})
            document_id = data.get('document_id')
            citizen_id = data.get('citizen_id')
            filename = data.get('filename')
            content_type = data.get('content_type')
            blob_name = data.get('blob_name')
            
            if not all([document_id, citizen_id, filename]):
                logger.warning(f"Invalid document.uploaded event: {event}")
                return
            
            # Create read_document entry
            async for db in get_db():
                try:
                    read_doc = ReadDocument(
                        id=document_id,
                        citizen_id=citizen_id,
                        filename=filename,
                        content_type=content_type,
                        blob_name=blob_name,
                        status="uploaded",
                        uploaded_at=datetime.utcnow()
                    )
                    
                    db.add(read_doc)
                    await db.commit()
                    
                    logger.info(f"Created read_document entry for {document_id}")
                    
                    # Invalidate cache for this citizen and document
                    try:
                        from app.services.redis_client import get_redis_client
                        redis_client = await get_redis_client(self.settings)
                        if redis_client:
                            await redis_client.invalidate_citizen_cache(citizen_id)
                            await redis_client.invalidate_document_cache(document_id)
                    except Exception as cache_error:
                        logger.warning(f"Failed to invalidate cache: {cache_error}")
                    
                    break
                    
                except Exception as e:
                    logger.error(f"Failed to create read_document: {e}")
                    await db.rollback()
                finally:
                    await db.close()
                    
        except Exception as e:
            logger.error(f"Error projecting document.uploaded: {e}")
    
    async def _project_document_authenticated(self, event: Dict[str, Any]):
        """Update is_authenticated in read_documents."""
        try:
            from app.database import get_db
            from sqlalchemy import update
            
            data = event.get('data', {})
            document_id = data.get('document_id')
            success = data.get('success', False)
            
            if not document_id:
                logger.warning(f"Invalid document.authenticated event: {event}")
                return
            
            # Update read_document
            async for db in get_db():
                try:
                    await db.execute(
                        update(ReadDocument)
                        .where(ReadDocument.id == document_id)
                        .values(
                            is_authenticated=success,
                            authenticated_at=datetime.utcnow() if success else None,
                            status="authenticated" if success else "uploaded"
                        )
                    )
                    await db.commit()
                    
                    logger.info(f"Updated authentication status for document {document_id}")
                    
                    # Invalidate cache for this document
                    try:
                        from app.services.redis_client import get_redis_client
                        redis_client = await get_redis_client(self.settings)
                        if redis_client:
                            await redis_client.invalidate_document_cache(document_id)
                    except Exception as cache_error:
                        logger.warning(f"Failed to invalidate cache: {cache_error}")
                    
                    break
                    
                except Exception as e:
                    logger.error(f"Failed to update authentication status: {e}")
                    await db.rollback()
                finally:
                    await db.close()
                    
        except Exception as e:
            logger.error(f"Error projecting document.authenticated: {e}")
    
    async def _project_transfer_requested(self, event: Dict[str, Any]):
        """Create entry in read_transfers."""
        try:
            from app.database import get_db
            
            data = event.get('data', {})
            transfer_id = data.get('transfer_id')
            citizen_id = data.get('citizen_id')
            citizen_name = data.get('citizen_name')
            source_operator_id = data.get('source_operator_id')
            source_operator_name = data.get('source_operator_name')
            destination_operator_id = data.get('destination_operator_id')
            destination_operator_name = data.get('destination_operator_name')
            document_count = data.get('document_count', 0)
            
            if not all([transfer_id, citizen_id, source_operator_id, destination_operator_id]):
                logger.warning(f"Invalid transfer.requested event: {event}")
                return
            
            # Create read_transfer entry
            async for db in get_db():
                try:
                    read_transfer = ReadTransfer(
                        id=transfer_id,
                        citizen_id=citizen_id,
                        citizen_name=citizen_name,
                        source_operator_id=source_operator_id,
                        source_operator_name=source_operator_name,
                        destination_operator_id=destination_operator_id,
                        destination_operator_name=destination_operator_name,
                        status="requested",
                        document_count=document_count,
                        requested_at=datetime.utcnow()
                    )
                    
                    db.add(read_transfer)
                    await db.commit()
                    
                    logger.info(f"Created read_transfer entry for {transfer_id}")
                    
                    # Invalidate cache for this citizen and transfer
                    try:
                        from app.services.redis_client import get_redis_client
                        redis_client = await get_redis_client(self.settings)
                        if redis_client:
                            await redis_client.invalidate_citizen_cache(citizen_id)
                            await redis_client.invalidate_transfer_cache(transfer_id)
                    except Exception as cache_error:
                        logger.warning(f"Failed to invalidate cache: {cache_error}")
                    
                    break
                    
                except Exception as e:
                    logger.error(f"Failed to create read_transfer: {e}")
                    await db.rollback()
                finally:
                    await db.close()
                    
        except Exception as e:
            logger.error(f"Error projecting transfer.requested: {e}")
    
    async def _project_transfer_confirmed(self, event: Dict[str, Any]):
        """Update transfer status in read_transfers."""
        try:
            from app.database import get_db
            from sqlalchemy import update
            
            data = event.get('data', {})
            transfer_id = data.get('transfer_id')
            status = data.get('status')
            
            if not transfer_id or not status:
                logger.warning(f"Invalid transfer.confirmed event: {event}")
                return
            
            # Update read_transfer
            async for db in get_db():
                try:
                    await db.execute(
                        update(ReadTransfer)
                        .where(ReadTransfer.id == transfer_id)
                        .values(
                            status=status,
                            confirmed_at=datetime.utcnow() if status == "confirmed" else None
                        )
                    )
                    await db.commit()
                    
                    logger.info(f"Updated transfer status for {transfer_id}")
                    
                    # Invalidate cache for this transfer
                    try:
                        from app.services.redis_client import get_redis_client
                        redis_client = await get_redis_client(self.settings)
                        if redis_client:
                            await redis_client.invalidate_transfer_cache(transfer_id)
                    except Exception as cache_error:
                        logger.warning(f"Failed to invalidate cache: {cache_error}")
                    
                    break
                    
                except Exception as e:
                    logger.error(f"Failed to update transfer status: {e}")
                    await db.rollback()
                finally:
                    await db.close()
                    
        except Exception as e:
            logger.error(f"Error projecting transfer.confirmed: {e}")

