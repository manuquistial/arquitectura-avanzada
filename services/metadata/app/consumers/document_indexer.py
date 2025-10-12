"""Document indexer - consumes Service Bus events and indexes in OpenSearch."""

import logging
from typing import Dict, Any
from datetime import datetime

from app.opensearch_client import OpenSearchClient
from app.config import Settings

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Indexes documents in OpenSearch from Service Bus events."""
    
    def __init__(self, opensearch_client: OpenSearchClient, settings: Settings):
        """Initialize indexer.
        
        Args:
            opensearch_client: OpenSearch client instance
            settings: Service settings
        """
        self.opensearch = opensearch_client
        self.settings = settings
        
        # Import Redis for cache invalidation
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../common'))
            from carpeta_common.redis_client import get_redis_client
            self.redis_available = True
            self._get_redis = get_redis_client
        except ImportError:
            self.redis_available = False
            logger.warning("Redis not available, cache invalidation disabled")
    
    async def handle_document_uploaded(self, event: Dict[str, Any]):
        """Handle document.uploaded event.
        
        Args:
            event: Event payload from Service Bus
        """
        try:
            data = event.get("data", {})
            document_id = data.get("document_id")
            citizen_id = data.get("citizen_id")
            filename = data.get("filename")
            sha256_hash = data.get("sha256_hash", "")
            
            logger.info(f"📑 Indexing uploaded document: {document_id}")
            
            # Index in OpenSearch
            success = await self.opensearch.index_document(
                document_id=document_id,
                citizen_id=citizen_id,
                title=data.get("title", filename),
                filename=filename,
                hash_value=sha256_hash,
                content_type=data.get("content_type", ""),
                status="uploaded",
                created_at=event.get("timestamp")
            )
            
            if success:
                # Invalidate cache for this citizen
                await self._invalidate_cache(citizen_id)
                logger.info(f"✅ Document indexed: {document_id}")
            else:
                logger.error(f"❌ Failed to index document: {document_id}")
                raise Exception("Indexing failed")
                
        except Exception as e:
            logger.error(f"❌ Error handling document.uploaded: {e}")
            raise  # Re-raise to trigger retry/DLQ
    
    async def handle_document_authenticated(self, event: Dict[str, Any]):
        """Handle document.authenticated event.
        
        Updates existing document in OpenSearch with authentication info.
        
        Args:
            event: Event payload from Service Bus
        """
        try:
            data = event.get("data", {})
            document_id = data.get("document_id")
            citizen_id = data.get("citizen_id")
            hub_success = data.get("hub_success", False)
            
            logger.info(f"📑 Updating authentication status: {document_id}")
            
            # Update document in OpenSearch (partial update)
            if not self.opensearch.client:
                logger.warning("OpenSearch not available")
                return
            
            update_body = {
                "doc": {
                    "hubAuthAt": event.get("timestamp"),
                    "signatureStatus": "authenticated" if hub_success else "failed",
                    "updatedAt": datetime.utcnow().isoformat()
                }
            }
            
            await self.opensearch.client.update(
                index=self.opensearch.INDEX_NAME,
                id=document_id,
                body=update_body,
                refresh='wait_for'
            )
            
            # Invalidate cache
            await self._invalidate_cache(citizen_id)
            
            logger.info(f"✅ Document authentication indexed: {document_id}")
            
        except Exception as e:
            logger.error(f"❌ Error handling document.authenticated: {e}")
            raise
    
    async def handle_document_deleted(self, document_id: str, citizen_id: int):
        """Handle document deletion.
        
        Args:
            document_id: Document ID to delete
            citizen_id: Citizen ID for cache invalidation
        """
        try:
            logger.info(f"🗑️  Removing document from index: {document_id}")
            
            # Delete from OpenSearch
            success = await self.opensearch.delete_document(document_id)
            
            if success:
                # Invalidate cache
                await self._invalidate_cache(citizen_id)
                logger.info(f"✅ Document removed from index: {document_id}")
                
        except Exception as e:
            logger.error(f"❌ Error deleting document from index: {e}")
    
    async def _invalidate_cache(self, citizen_id: int):
        """Invalidate search cache for citizen using Redis Pub/Sub.
        
        Publishes to channel: invalidate:search:{citizenId}
        Subscribers should clear keys: search:*, doc:{citizenId}:*
        
        Args:
            citizen_id: Citizen ID to invalidate cache for
        """
        if not self.redis_available:
            return
        
        try:
            redis = await self._get_redis()
            
            # Publish invalidation message
            channel = f"invalidate:search:{citizen_id}"
            message = {
                "citizen_id": citizen_id,
                "timestamp": datetime.utcnow().isoformat(),
                "action": "invalidate_search_cache"
            }
            
            await redis.publish(channel, json.dumps(message))
            
            # Also directly delete search cache keys for this citizen
            # Pattern: search:*citizenId:{citizen_id}*
            keys_to_delete = []
            
            async for key in redis.scan_iter(match=f"search:*{citizen_id}*"):
                keys_to_delete.append(key)
            
            if keys_to_delete:
                await redis.delete(*keys_to_delete)
                logger.info(f"🔄 Invalidated {len(keys_to_delete)} cache keys for citizen {citizen_id}")
            
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")

