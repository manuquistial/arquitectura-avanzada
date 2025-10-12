"""Service Bus event consumer for metadata service."""

import asyncio
import logging
from typing import Dict, Any

from app.config import Settings
from app.opensearch_client import OpenSearchClient
from app.consumers.document_indexer import DocumentIndexer

logger = logging.getLogger(__name__)


class MetadataEventConsumer:
    """Consumes events from Service Bus and processes them."""
    
    def __init__(self, settings: Settings, opensearch_client: OpenSearchClient):
        """Initialize consumer.
        
        Args:
            settings: Service settings
            opensearch_client: OpenSearch client
        """
        self.settings = settings
        self.indexer = DocumentIndexer(opensearch_client, settings)
        self.bus_client = None
        
        # Initialize Service Bus client
        try:
            from carpeta_common.bus import ServiceBusClient as CommonBusClient
            self.bus_client = CommonBusClient(settings.servicebus_connection_string)
        except ImportError:
            logger.warning("carpeta_common not available, consumer disabled")
    
    async def start_consumers(self):
        """Start all event consumers (runs in background)."""
        if not self.bus_client:
            logger.warning("Service Bus client not initialized, consumers not started")
            return
        
        logger.info("🚀 Starting metadata event consumers...")
        
        # Start consumers concurrently
        await asyncio.gather(
            self._consume_document_uploaded(),
            self._consume_document_authenticated(),
            return_exceptions=True
        )
    
    async def _consume_document_uploaded(self):
        """Consume document.uploaded events."""
        logger.info("📭 Starting consumer: document-uploaded")
        
        try:
            await self.bus_client.consume_queue(
                queue_name="document-uploaded",
                handler=self.indexer.handle_document_uploaded,
                max_messages=10,
                max_wait_time=30
            )
        except Exception as e:
            logger.error(f"❌ document-uploaded consumer error: {e}")
    
    async def _consume_document_authenticated(self):
        """Consume document.authenticated events."""
        logger.info("📭 Starting consumer: document-authenticated")
        
        try:
            await self.bus_client.consume_queue(
                queue_name="document-authenticated",
                handler=self.indexer.handle_document_authenticated,
                max_messages=10,
                max_wait_time=30
            )
        except Exception as e:
            logger.error(f"❌ document-authenticated consumer error: {e}")
    
    async def stop_consumers(self):
        """Stop all consumers."""
        if self.bus_client:
            await self.bus_client.close()
        logger.info("🛑 Metadata event consumers stopped")

