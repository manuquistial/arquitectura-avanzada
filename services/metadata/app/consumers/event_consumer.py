"""Service Bus event consumer for metadata service."""

import asyncio
import logging
from typing import Dict, Any

from app.config import get_config
from app.opensearch_client import OpenSearchClient
from app.consumers.document_indexer import DocumentIndexer

logger = logging.getLogger(__name__)


class MetadataEventConsumer:
    """Consumes events from Service Bus and processes them."""
    
    def __init__(self, config, opensearch_client: OpenSearchClient):
        """Initialize consumer.
        
        Args:
            config: Service configuration
            opensearch_client: OpenSearch client
        """
        self.config = config
        self.indexer = DocumentIndexer(opensearch_client, config)
        self.bus_client = None
        
        # Initialize Service Bus client
        try:
            from carpeta_common.bus import ServiceBusClient as CommonBusClient
            self.bus_client = CommonBusClient(config.servicebus.connection_string)
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
        """Consume document.uploaded events with Azure-specific error handling."""
        logger.info("📭 Starting consumer: document-uploaded")
        
        try:
            await self.bus_client.consume_queue(
                queue_name="document-uploaded",
                handler=self.indexer.handle_document_uploaded,
                max_messages=10,
                max_wait_time=30
            )
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"❌ document-uploaded consumer error: {e}")
            logger.error(f"Error type: {error_type}")
            
            # Azure-specific error handling
            if "connection" in str(e).lower():
                logger.error("❌ Service Bus connection failed for document-uploaded consumer")
                logger.error("💡 Check Azure Service Bus availability and network connectivity")
            elif "permission" in str(e).lower():
                logger.error("❌ Service Bus permission denied for document-uploaded consumer")
                logger.error("💡 Check Service Bus connection string and permissions")
            elif "timeout" in str(e).lower():
                logger.error("❌ Service Bus connection timeout for document-uploaded consumer")
                logger.error("💡 Check Service Bus performance and network latency")
            elif "queue" in str(e).lower():
                logger.error("❌ Service Bus queue not found for document-uploaded consumer")
                logger.error("💡 Check if Service Bus queue exists and is accessible")
            else:
                logger.error(f"❌ Unexpected Service Bus error for document-uploaded consumer: {error_type}")
    
    async def _consume_document_authenticated(self):
        """Consume document.authenticated events with Azure-specific error handling."""
        logger.info("📭 Starting consumer: document-authenticated")
        
        try:
            await self.bus_client.consume_queue(
                queue_name="document-authenticated",
                handler=self.indexer.handle_document_authenticated,
                max_messages=10,
                max_wait_time=30
            )
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"❌ document-authenticated consumer error: {e}")
            logger.error(f"Error type: {error_type}")
            
            # Azure-specific error handling
            if "connection" in str(e).lower():
                logger.error("❌ Service Bus connection failed for document-authenticated consumer")
                logger.error("💡 Check Azure Service Bus availability and network connectivity")
            elif "permission" in str(e).lower():
                logger.error("❌ Service Bus permission denied for document-authenticated consumer")
                logger.error("💡 Check Service Bus connection string and permissions")
            elif "timeout" in str(e).lower():
                logger.error("❌ Service Bus connection timeout for document-authenticated consumer")
                logger.error("💡 Check Service Bus performance and network latency")
            elif "queue" in str(e).lower():
                logger.error("❌ Service Bus queue not found for document-authenticated consumer")
                logger.error("💡 Check if Service Bus queue exists and is accessible")
            else:
                logger.error(f"❌ Unexpected Service Bus error for document-authenticated consumer: {error_type}")
    
    async def stop_consumers(self):
        """Stop all consumers."""
        if self.bus_client:
            await self.bus_client.close()
        logger.info("🛑 Metadata event consumers stopped")

