"""OpenSearch client for document indexing and search - Updated for Azure."""

import logging
from typing import Any, Dict, List, Optional
from opensearchpy import OpenSearch, RequestError
from opensearchpy.helpers import bulk

from app.config import get_config

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
                "contentType": {"type": "keyword"},
                "state": {"type": "keyword"},
                "wormLocked": {"type": "boolean"},
                "signedAt": {"type": "date"},
                "retentionUntil": {"type": "date"},
                "lifecycleTier": {"type": "keyword"}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "refresh_interval": "5s"
        }
    }
    
    def __init__(self, config):
        """Initialize OpenSearch client."""
        self.config = config
        self.client: Optional[OpenSearch] = None
        
        if config.opensearch.host:
            self._init_client()
    
    def _init_client(self):
        """Initialize async OpenSearch client with Azure-specific error handling."""
        try:
            auth = None
            if self.config.opensearch.username and self.config.opensearch.password:
                auth = (
                    self.config.opensearch.username,
                    self.config.opensearch.password
                )
            
            self.client = OpenSearch(
                hosts=[{
                    'host': self.config.opensearch.host,
                    'port': self.config.opensearch.port
                }],
                http_auth=auth,
                use_ssl=self.config.opensearch.use_ssl,
                verify_certs=self.config.opensearch.verify_certs,
                timeout=30
            )
            
            logger.info(
                f"✅ OpenSearch client initialized: "
                f"{self.config.opensearch.host}:{self.config.opensearch.port}"
            )
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"❌ Failed to initialize OpenSearch: {e}")
            logger.error(f"Error type: {error_type}")
            
            # Azure-specific error handling
            if "connection" in str(e).lower():
                logger.error("❌ OpenSearch connection failed - check network and credentials")
                logger.error("💡 Verify OpenSearch cluster is running and accessible")
            elif "ssl" in str(e).lower():
                logger.error("❌ SSL connection failed - check SSL configuration")
                logger.error("💡 Verify SSL certificates and OpenSearch SSL settings")
            elif "authentication" in str(e).lower():
                logger.error("❌ Authentication failed - check OpenSearch credentials")
                logger.error("💡 Verify username and password for OpenSearch")
            elif "timeout" in str(e).lower():
                logger.error("❌ Connection timeout - check OpenSearch availability")
                logger.error("💡 Verify OpenSearch cluster is running and network connectivity")
            else:
                logger.error(f"❌ Unexpected OpenSearch initialization error: {error_type}")
                
            self.client = None
    
    def ensure_index(self):
        """Create index if it doesn't exist with Azure-specific error handling."""
        if not self.client:
            logger.warning("OpenSearch client not initialized")
            raise ConnectionError("OpenSearch client not available")
        
        try:
            exists = self.client.indices.exists(index=self.INDEX_NAME)
            
            if not exists:
                self.client.indices.create(
                    index=self.INDEX_NAME,
                    body=self.INDEX_MAPPING
                )
                logger.info(f"✅ Created OpenSearch index: {self.INDEX_NAME}")
            else:
                logger.debug(f"Index {self.INDEX_NAME} already exists")
                
        except RequestError as e:
            error_type = type(e).__name__
            logger.error(f"❌ Failed to create index: {e}")
            logger.error(f"Error type: {error_type}")
            
            # Azure-specific error handling
            if "index_already_exists" in str(e).lower():
                logger.warning("⚠️ Index already exists, continuing...")
            elif "permission" in str(e).lower():
                logger.error("❌ Permission denied creating OpenSearch index")
                logger.error("💡 Check OpenSearch user permissions for index creation")
                raise
            elif "connection" in str(e).lower():
                logger.error("❌ OpenSearch connection failed during index creation")
                logger.error("💡 Check OpenSearch cluster availability and network connectivity")
                raise
            else:
                logger.error(f"❌ Unexpected OpenSearch index creation error: {error_type}")
                raise
                
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"❌ OpenSearch connection failed: {e}")
            logger.error(f"Error type: {error_type}")
            
            # Azure-specific error handling
            if "connection" in str(e).lower():
                logger.error("❌ OpenSearch connection failed - check network and credentials")
                logger.error("💡 Verify OpenSearch cluster is running and accessible")
            elif "ssl" in str(e).lower():
                logger.error("❌ SSL connection failed - check SSL configuration")
                logger.error("💡 Verify SSL certificates and OpenSearch SSL settings")
            elif "timeout" in str(e).lower():
                logger.error("❌ Connection timeout - check OpenSearch availability")
                logger.error("💡 Verify OpenSearch cluster is running and network connectivity")
            else:
                logger.error(f"❌ Unexpected OpenSearch connection error: {error_type}")
                
            raise
    
    def index_document(
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
            
            response = self.client.index(
                index=self.INDEX_NAME,
                id=document_id,
                body=doc_body,
                refresh='wait_for'  # Wait for refresh to make it searchable
            )
            
            logger.info(f"✅ Indexed document: {document_id}")
            return response['result'] in ['created', 'updated']
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"❌ Failed to index document {document_id}: {e}")
            logger.error(f"Error type: {error_type}")
            
            # Azure-specific error handling
            if "connection" in str(e).lower():
                logger.error("❌ OpenSearch connection failed during document indexing")
                logger.error("💡 Check OpenSearch cluster availability and network connectivity")
            elif "permission" in str(e).lower():
                logger.error("❌ Permission denied indexing document in OpenSearch")
                logger.error("💡 Check OpenSearch user permissions for document indexing")
            elif "timeout" in str(e).lower():
                logger.error("❌ Connection timeout during document indexing")
                logger.error("💡 Check OpenSearch cluster performance and network latency")
            elif "index_not_found" in str(e).lower():
                logger.error("❌ OpenSearch index not found during document indexing")
                logger.error("💡 Check if OpenSearch index exists and is accessible")
            else:
                logger.error(f"❌ Unexpected OpenSearch indexing error: {error_type}")
                
            return False
    
    def search_documents(
        self,
        query: str = "",
        citizen_id: Optional[str] = None,
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
                    "term": {"citizen_id": citizen_id}
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
            response = self.client.search(
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
            error_type = type(e).__name__
            logger.error(f"❌ Search failed: {e}")
            logger.error(f"Error type: {error_type}")
            
            # Azure-specific error handling
            if "connection" in str(e).lower():
                logger.error("❌ OpenSearch connection failed during search")
                logger.error("💡 Check OpenSearch cluster availability and network connectivity")
            elif "permission" in str(e).lower():
                logger.error("❌ Permission denied searching OpenSearch")
                logger.error("💡 Check OpenSearch user permissions for search operations")
            elif "timeout" in str(e).lower():
                logger.error("❌ Connection timeout during search")
                logger.error("💡 Check OpenSearch cluster performance and network latency")
            elif "index_not_found" in str(e).lower():
                logger.error("❌ OpenSearch index not found during search")
                logger.error("💡 Check if OpenSearch index exists and is accessible")
            elif "query" in str(e).lower():
                logger.error("❌ Invalid search query")
                logger.error("💡 Check search query syntax and parameters")
            else:
                logger.error(f"❌ Unexpected OpenSearch search error: {error_type}")
                
            return {"total": 0, "hits": []}
    
    def delete_document(self, document_id: str) -> bool:
        """Delete document from index with Azure-specific error handling."""
        if not self.client:
            return False
        
        try:
            self.client.delete(
                index=self.INDEX_NAME,
                id=document_id,
                refresh='wait_for'
            )
            logger.info(f"🗑️  Deleted document from index: {document_id}")
            return True
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"❌ Failed to delete document: {e}")
            logger.error(f"Error type: {error_type}")
            
            # Azure-specific error handling
            if "connection" in str(e).lower():
                logger.error("❌ OpenSearch connection failed during document deletion")
                logger.error("💡 Check OpenSearch cluster availability and network connectivity")
            elif "permission" in str(e).lower():
                logger.error("❌ Permission denied deleting document from OpenSearch")
                logger.error("💡 Check OpenSearch user permissions for document deletion")
            elif "timeout" in str(e).lower():
                logger.error("❌ Connection timeout during document deletion")
                logger.error("💡 Check OpenSearch cluster performance and network latency")
            elif "not_found" in str(e).lower():
                logger.warning(f"⚠️ Document {document_id} not found in OpenSearch index")
                logger.info("💡 Document may have been already deleted or never indexed")
                return True  # Consider this a success since document is not in index
            elif "index_not_found" in str(e).lower():
                logger.error("❌ OpenSearch index not found during document deletion")
                logger.error("💡 Check if OpenSearch index exists and is accessible")
            else:
                logger.error(f"❌ Unexpected OpenSearch deletion error: {error_type}")
                
            return False
    
    def close(self):
        """Close OpenSearch client."""
        if self.client:
            self.client.close()
            logger.info("OpenSearch client closed")

