"""OpenSearch client for document indexing and search."""

import logging
from typing import Any, Dict, List, Optional
from opensearchpy import OpenSearch, AsyncOpenSearch, RequestError
from opensearchpy.helpers import async_bulk

from app.config import Settings

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """OpenSearch client for document metadata indexing."""
    
    INDEX_NAME = "documents"
    
    INDEX_MAPPING = {
        "mappings": {
            "properties": {
                "documentId": {"type": "keyword"},
                "citizenId": {"type": "long"},
                "title": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "filename": {"type": "text"},
                "issuer": {"type": "keyword"},
                "hash": {"type": "keyword"},
                "tags": {"type": "keyword"},
                "hubAuthAt": {"type": "date"},
                "createdAt": {"type": "date"},
                "updatedAt": {"type": "date"},
                "status": {"type": "keyword"},
                "contentType": {"type": "keyword"}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "refresh_interval": "5s"
        }
    }
    
    def __init__(self, settings: Settings):
        """Initialize OpenSearch client."""
        self.settings = settings
        self.client: Optional[AsyncOpenSearch] = None
        
        if settings.opensearch_host:
            self._init_client()
    
    def _init_client(self):
        """Initialize async OpenSearch client."""
        try:
            auth = None
            if self.settings.opensearch_username and self.settings.opensearch_password:
                auth = (
                    self.settings.opensearch_username,
                    self.settings.opensearch_password
                )
            
            self.client = AsyncOpenSearch(
                hosts=[{
                    'host': self.settings.opensearch_host,
                    'port': self.settings.opensearch_port
                }],
                http_auth=auth,
                use_ssl=self.settings.opensearch_use_ssl,
                verify_certs=self.settings.opensearch_verify_certs,
                timeout=30
            )
            
            logger.info(
                f"✅ OpenSearch client initialized: "
                f"{self.settings.opensearch_host}:{self.settings.opensearch_port}"
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenSearch: {e}")
            self.client = None
    
    async def ensure_index(self):
        """Create index if it doesn't exist."""
        if not self.client:
            logger.warning("OpenSearch client not initialized")
            return
        
        try:
            exists = await self.client.indices.exists(index=self.INDEX_NAME)
            
            if not exists:
                await self.client.indices.create(
                    index=self.INDEX_NAME,
                    body=self.INDEX_MAPPING
                )
                logger.info(f"✅ Created OpenSearch index: {self.INDEX_NAME}")
            else:
                logger.debug(f"Index {self.INDEX_NAME} already exists")
                
        except RequestError as e:
            logger.error(f"❌ Failed to create index: {e}")
            raise
    
    async def index_document(
        self,
        document_id: str,
        citizen_id: int,
        title: str,
        filename: str,
        hash_value: str,
        content_type: str = "",
        issuer: str = "",
        tags: List[str] = None,
        hub_auth_at: Optional[str] = None,
        status: str = "uploaded",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ) -> bool:
        """Index a document in OpenSearch.
        
        Args:
            document_id: Unique document ID
            citizen_id: Owner citizen ID
            title: Document title
            filename: Original filename
            hash_value: SHA-256 hash
            content_type: MIME type
            issuer: Document issuer
            tags: Document tags
            hub_auth_at: Hub authentication timestamp
            status: Document status
            created_at: Creation timestamp
            updated_at: Update timestamp
            
        Returns:
            True if successful
        """
        if not self.client:
            logger.warning("OpenSearch not available, skipping indexing")
            return False
        
        try:
            doc_body = {
                "documentId": document_id,
                "citizenId": citizen_id,
                "title": title,
                "filename": filename,
                "hash": hash_value,
                "contentType": content_type,
                "issuer": issuer or "self",
                "tags": tags or [],
                "status": status,
                "hubAuthAt": hub_auth_at,
                "createdAt": created_at,
                "updatedAt": updated_at
            }
            
            response = await self.client.index(
                index=self.INDEX_NAME,
                id=document_id,
                body=doc_body,
                refresh='wait_for'  # Wait for refresh to make it searchable
            )
            
            logger.info(f"✅ Indexed document: {document_id}")
            return response['result'] in ['created', 'updated']
            
        except Exception as e:
            logger.error(f"❌ Failed to index document {document_id}: {e}")
            return False
    
    async def search_documents(
        self,
        query: str = "",
        citizen_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        from_: int = 0,
        size: int = 20
    ) -> Dict[str, Any]:
        """Search documents in OpenSearch.
        
        Args:
            query: Free text search query
            citizen_id: Filter by citizen ID
            tags: Filter by tags
            status: Filter by status
            from_: Pagination offset
            size: Page size
            
        Returns:
            Search results with hits and total
        """
        if not self.client:
            logger.warning("OpenSearch not available")
            return {"total": 0, "hits": []}
        
        try:
            # Build query
            must_clauses = []
            
            # Text search on title and filename
            if query:
                must_clauses.append({
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "filename", "tags"],
                        "fuzziness": "AUTO"
                    }
                })
            
            # Filters
            filter_clauses = []
            
            if citizen_id:
                filter_clauses.append({
                    "term": {"citizenId": citizen_id}
                })
            
            if tags:
                filter_clauses.append({
                    "terms": {"tags": tags}
                })
            
            if status:
                filter_clauses.append({
                    "term": {"status": status}
                })
            
            # Build final query
            if must_clauses or filter_clauses:
                search_query = {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}],
                        "filter": filter_clauses
                    }
                }
            else:
                search_query = {"match_all": {}}
            
            # Execute search
            response = await self.client.search(
                index=self.INDEX_NAME,
                body={
                    "query": search_query,
                    "from": from_,
                    "size": size,
                    "sort": [
                        {"createdAt": {"order": "desc"}}
                    ]
                }
            )
            
            # Parse results
            hits = response['hits']['hits']
            total = response['hits']['total']['value']
            
            results = {
                "total": total,
                "hits": [
                    {
                        "id": hit['_id'],
                        "score": hit['_score'],
                        **hit['_source']
                    }
                    for hit in hits
                ]
            }
            
            logger.info(f"🔍 Search returned {len(hits)} of {total} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return {"total": 0, "hits": []}
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete document from index."""
        if not self.client:
            return False
        
        try:
            await self.client.delete(
                index=self.INDEX_NAME,
                id=document_id,
                refresh='wait_for'
            )
            logger.info(f"🗑️  Deleted document from index: {document_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete document: {e}")
            return False
    
    async def close(self):
        """Close OpenSearch client."""
        if self.client:
            await self.client.close()
            logger.info("OpenSearch client closed")

