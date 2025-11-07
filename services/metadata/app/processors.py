"""Document event processors for metadata operations."""

import logging
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import AsyncSessionLocal inside functions to avoid early engine creation
# This prevents CancelledError during database initialization
from app.models import DocumentMetadata

logger = logging.getLogger(__name__)


def get_db_session():
    """Get database session factory (lazy import to avoid early engine creation)."""
    from app.database import AsyncSessionLocal
    return AsyncSessionLocal


class MetadataEventProcessor:
    """Processes document events for metadata operations."""
    
    async def process_document_uploaded(self, event_data: Dict[str, Any]) -> bool:
        """Process document.uploaded event.
        
        Args:
            event_data: Event data with 'event_type', 'data', 'timestamp', etc.
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            data = event_data.get("data", {})
            document_id = data.get("document_id")
            citizen_id = data.get("citizen_id")
            filename = data.get("filename")
            blob_name = data.get("blob_name")
            size_bytes = data.get("size_bytes")
            
            logger.info(
                f"📄 Processing document.uploaded: document_id={document_id}, "
                f"citizen_id={citizen_id}, filename={filename}"
            )
            
            # Update metadata in database if needed
            AsyncSessionLocal = get_db_session()
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(DocumentMetadata).where(DocumentMetadata.id == document_id)
                )
                metadata = result.scalar_one_or_none()
                
                if metadata:
                    # Update metadata fields
                    if size_bytes and not metadata.size_bytes:
                        metadata.size_bytes = size_bytes
                    if blob_name and not metadata.blob_name == blob_name:
                        metadata.blob_name = blob_name
                    metadata.is_uploaded = True
                    metadata.status = "uploaded"
                    
                    await db.commit()
                    logger.info(f"✅ Updated metadata for document {document_id}")
            
            # TODO: Future enhancements
            # 1. Indexar en OpenSearch (cuando esté disponible)
            # 2. OCR del documento (cuando esté implementado)
            # 3. Extracción de metadatos avanzados
            
            logger.info(
                f"✅ Successfully processed document.uploaded: "
                f"document_id={document_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing document.uploaded: {e}", exc_info=True)
            return False
    
    async def process_document_deleted(self, event_data: Dict[str, Any]) -> bool:
        """Process document.deleted event.
        
        Args:
            event_data: Event data with 'event_type', 'data', 'timestamp', etc.
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            data = event_data.get("data", {})
            document_id = data.get("document_id")
            citizen_id = data.get("citizen_id")
            
            logger.info(
                f"🗑️  Processing document.deleted: document_id={document_id}, "
                f"citizen_id={citizen_id}"
            )
            
            # TODO: Future enhancements
            # 1. Eliminar de OpenSearch (cuando esté disponible)
            # 2. Actualizar índices de búsqueda
            # 3. Limpiar cache relacionado
            
            logger.info(
                f"✅ Successfully processed document.deleted: "
                f"document_id={document_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing document.deleted: {e}", exc_info=True)
            return False
    
    async def process_document_authenticated(self, event_data: Dict[str, Any]) -> bool:
        """Process document.authenticated event.
        
        Args:
            event_data: Event data with 'event_type', 'data', 'timestamp', etc.
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            data = event_data.get("data", {})
            document_id = data.get("document_id")
            citizen_id = data.get("citizen_id")
            hub_signature_ref = data.get("hub_signature_ref")
            
            logger.info(
                f"🔐 Processing document.authenticated: document_id={document_id}, "
                f"citizen_id={citizen_id}, hub_signature_ref={hub_signature_ref}"
            )
            
            # Update metadata with authentication info
            AsyncSessionLocal = get_db_session()
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(DocumentMetadata).where(DocumentMetadata.id == document_id)
                )
                metadata = result.scalar_one_or_none()
                
                if metadata:
                    # Metadata is updated by Signature Service, but we log it here
                    logger.info(f"✅ Document {document_id} authenticated, metadata should be updated")
            
            # TODO: Future enhancements
            # 1. Actualizar índices de búsqueda con estado autenticado
            # 2. Notificar al ciudadano
            
            logger.info(
                f"✅ Successfully processed document.authenticated: "
                f"document_id={document_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing document.authenticated: {e}", exc_info=True)
            return False
    
    async def process_document_signed(self, event_data: Dict[str, Any]) -> bool:
        """Process document.signed event.
        
        Args:
            event_data: Event data with 'event_type', 'data', 'timestamp', etc.
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            data = event_data.get("data", {})
            document_id = data.get("document_id")
            citizen_id = data.get("citizen_id")
            
            logger.info(
                f"✍️  Processing document.signed: document_id={document_id}, "
                f"citizen_id={citizen_id}"
            )
            
            # TODO: Future enhancements
            # 1. Notificar al ciudadano por email
            # 2. Actualizar estado en frontend (WebSocket)
            # 3. Indexar estado de firma en OpenSearch
            
            logger.info(
                f"✅ Successfully processed document.signed: "
                f"document_id={document_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing document.signed: {e}", exc_info=True)
            return False
    
    async def process_document_verified(self, event_data: Dict[str, Any]) -> bool:
        """Process document.verified event.
        
        Args:
            event_data: Event data with 'event_type', 'data', 'timestamp', etc.
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            data = event_data.get("data", {})
            document_id = data.get("document_id")
            verified = data.get("verified", False)
            
            logger.info(
                f"✅ Processing document.verified: document_id={document_id}, "
                f"verified={verified}"
            )
            
            logger.info(
                f"✅ Successfully processed document.verified: "
                f"document_id={document_id}, verified={verified}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing document.verified: {e}", exc_info=True)
            return False

