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
        
        # Start consumers in parallel
        await asyncio.gather(
            self.consume_citizen_registered(),
            self.consume_document_uploaded(),
            self.consume_document_authenticated(),
            self.consume_transfer_confirmed(),
            return_exceptions=True
        )
    
    async def consume_citizen_registered(self):
        """
        Consume citizen.registered events.
        
        Updates citizen_name in read_documents (denormalization).
        """
        queue_name = "citizen-registered"
        logger.info(f"📥 Starting consumer: {queue_name}")
        
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
                                
                            except Exception as e:
                                logger.error(f"Error projecting citizen.registered: {e}")
                                await receiver.dead_letter_message(msg, reason=str(e))
                    
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Consumer error: {e}")
                        await asyncio.sleep(5)
    
    async def consume_document_uploaded(self):
        """
        Consume document.uploaded events.
        
        Creates entry in read_documents.
        """
        queue_name = "document-uploaded"
        logger.info(f"📥 Starting consumer: {queue_name}")
        
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
                            except Exception as e:
                                logger.error(f"Error projecting document.uploaded: {e}")
                                await receiver.dead_letter_message(msg, reason=str(e))
                    
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Consumer error: {e}")
                        await asyncio.sleep(5)
    
    async def consume_document_authenticated(self):
        """
        Consume document.authenticated events.
        
        Updates is_authenticated in read_documents.
        """
        queue_name = "document-authenticated"
        logger.info(f"📥 Starting consumer: {queue_name}")
        
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
                            except Exception as e:
                                logger.error(f"Error projecting document.authenticated: {e}")
                                await receiver.dead_letter_message(msg, reason=str(e))
                    
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Consumer error: {e}")
                        await asyncio.sleep(5)
    
    async def consume_transfer_confirmed(self):
        """
        Consume transfer.confirmed events.
        
        Updates transfer status in read_transfers.
        """
        queue_name = "transfer-confirmed"
        logger.info(f"📥 Starting consumer: {queue_name}")
        
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
                            except Exception as e:
                                logger.error(f"Error projecting transfer.confirmed: {e}")
                                await receiver.dead_letter_message(msg, reason=str(e))
                    
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Consumer error: {e}")
                        await asyncio.sleep(5)
    
    # Projection methods
    
    async def _project_citizen_registered(self, event: Dict[str, Any]):
        """Update citizen_name in all read_documents for this citizen."""
        # TODO: Implement projection logic
        logger.info(f"Projecting citizen.registered: {event}")
    
    async def _project_document_uploaded(self, event: Dict[str, Any]):
        """Create entry in read_documents."""
        # TODO: Implement projection logic
        logger.info(f"Projecting document.uploaded: {event}")
    
    async def _project_document_authenticated(self, event: Dict[str, Any]):
        """Update is_authenticated in read_documents."""
        # TODO: Implement projection logic
        logger.info(f"Projecting document.authenticated: {event}")
    
    async def _project_transfer_confirmed(self, event: Dict[str, Any]):
        """Update transfer status in read_transfers."""
        # TODO: Implement projection logic
        logger.info(f"Projecting transfer.confirmed: {event}")

