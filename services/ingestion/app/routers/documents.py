"""Documents API router - Updated for Azure."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import DocumentMetadata
from app.schemas import (
    DownloadURLRequest,
    DownloadURLResponse,
    UploadURLRequest,
    UploadURLResponse,
)
from app.service_bus import service_bus_publisher
from app.hash_verification import HashVerificationService
from app.config import get_config

logger = logging.getLogger(__name__)
router = APIRouter()

# Get configuration
config = get_config()

# Azure Blob Storage client
from app.azure_storage import AzureBlobDocumentClient

storage_client = AzureBlobDocumentClient(
    account_name=config.azure_storage_account_name,
    account_key=config.azure_storage_account_key,
    container_name=config.azure_storage_container_name,
    connection_string=config.azure_storage_connection_string,
    sas_ttl_minutes=config.azure_storage_sas_ttl_minutes,
)


@router.post("/upload-url", response_model=UploadURLResponse)
async def get_upload_url(
    request: UploadURLRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UploadURLResponse:
    """Get presigned URL for uploading a document.

    The frontend will use this URL to upload directly to Azure Blob Storage using PUT.
    """
    logger.info(
        f"Generating upload URL for citizen {request.citizen_id}, "
        f"file: {request.filename}"
    )

    try:
        # Use default TTL from storage_client (SAS_TTL_MINUTES from ConfigMap)
        result = storage_client.generate_presigned_put(
            citizen_id=request.citizen_id,
            filename=request.filename,
            content_type=request.content_type,
            # expires_in will use sas_ttl_minutes from client config
        )

        # Store metadata in database
        key = result["blob_name"]
        
        metadata = DocumentMetadata(
            id=result["document_id"],
            citizen_id=request.citizen_id,
            title=request.title,
            filename=request.filename,
            content_type=request.content_type,
            blob_name=key,
            storage_provider="azure",
            status="pending",
            description=request.description,
        )
        
        db.add(metadata)
        await db.commit()
        await db.refresh(metadata)
        
        logger.info(f"Document metadata stored: {metadata.id}")
        
        # Publish event to Service Bus for async processing
        await service_bus_publisher.publish_document_uploaded(
            document_id=result["document_id"],
            citizen_id=str(request.citizen_id),
            filename=request.filename,
            content_type=request.content_type,
            blob_name=key,
            size_bytes=None  # Size will be available after upload
        )

        # Return TTL in seconds (SAS_TTL_MINUTES * 60)
        sas_ttl_minutes = config.azure_storage_sas_ttl_minutes
        
        return UploadURLResponse(
            upload_url=result["upload_url"],
            document_id=result["document_id"],
            blob_name=key,  # Azure blob name
            expires_in=sas_ttl_minutes * 60,
        )

    except Exception as e:
        logger.error(f"Error generating upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        )


@router.post("/upload-direct")
async def upload_document_direct(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    citizen_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
) -> dict:
    """Upload document directly through backend to avoid CORS issues."""
    logger.info(f"Direct upload for citizen {citizen_id}, file: {file.filename}")
    
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Generate a SAS PUT URL for this blob and upload server-side to avoid CORS and Auth issues
        sas_result = storage_client.generate_presigned_put(
            citizen_id=int(citizen_id) if isinstance(citizen_id, str) and citizen_id.isdigit() else citizen_id,  # handle str/int
            filename=file.filename,
            content_type=file.content_type,
        )
        upload_url = sas_result["upload_url"]
        # Use IDs from SAS generation to keep metadata consistent
        doc_id = sas_result["document_id"]
        blob_name = sas_result["blob_name"]

        # Perform HTTP PUT to Azure Blob Storage with required headers
        import httpx
        headers = {
            "Content-Type": file.content_type or "application/octet-stream",
            "x-ms-blob-type": "BlockBlob",
        }
        async with httpx.AsyncClient(timeout=None) as client:
            put_resp = await client.put(upload_url, content=content, headers=headers)
            if put_resp.status_code >= 400:
                raise RuntimeError(f"Azure PUT failed: {put_resp.status_code} {put_resp.text}")
        
        # Calculate SHA-256 hash
        import hashlib
        sha256_hash = hashlib.sha256(content).hexdigest()
        
        # Store metadata in database
        metadata = DocumentMetadata(
            id=doc_id,
            citizen_id=citizen_id,
            title=title,
            filename=file.filename,
            content_type=file.content_type,
            blob_name=blob_name,
            storage_provider="azure",
            status="uploaded",
            description=description,
            sha256_hash=sha256_hash,
            size_bytes=file_size,
        )
        
        db.add(metadata)
        await db.commit()
        await db.refresh(metadata)
        
        logger.info(f"Document uploaded directly: {doc_id}")
        
        # Publish event to Service Bus
        await service_bus_publisher.publish_document_uploaded(
            document_id=doc_id,
            citizen_id=citizen_id,
            filename=file.filename,
            content_type=file.content_type,
            blob_name=blob_name,
            size_bytes=file_size
        )
        
        return {
            "message": "Document uploaded successfully",
            "document_id": doc_id,
            "filename": file.filename,
            "size_bytes": file_size,
            "sha256_hash": sha256_hash
        }
        
    except Exception as e:
        logger.error(f"Error in direct upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.post("/download-url", response_model=DownloadURLResponse)
async def get_download_url(
    request: DownloadURLRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DownloadURLResponse:
    """Get presigned URL for downloading a document."""
    logger.info(
        f"Generating download URL for document {request.document_id}"
    )

    try:
        # Get blob_name from database using document_id
        from sqlalchemy import select
        result = await db.execute(
            select(DocumentMetadata).where(DocumentMetadata.id == request.document_id)
        )
        metadata = result.scalar_one_or_none()
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {request.document_id} not found"
            )
        
        if metadata.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Document {request.document_id} has been deleted"
            )

        download_url = storage_client.generate_presigned_get(
            metadata.blob_name,
            expires_in=3600,
        )

        # Audit trail logging
        logger.info(f"Generated download URL for document {request.document_id}")

        return DownloadURLResponse(
            download_url=download_url,
            expires_in=3600,
        )

    except Exception as e:
        logger.error(f"Error generating download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL",
        )


@router.post("/confirm-upload")
async def confirm_upload(
    request: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Confirm document upload and verify integrity.

    Called by frontend after successful PUT to storage.
    """
    document_id = request.get("document_id")
    sha256 = request.get("sha256")
    size = request.get("size")
    
    if not document_id or not sha256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_id and sha256 are required"
        )
    
    logger.info(f"Confirming upload for document {document_id}")

    try:
        # Get document metadata from database
        from sqlalchemy import select
        result = await db.execute(
            select(DocumentMetadata).where(DocumentMetadata.id == document_id)
        )
        metadata = result.scalar_one_or_none()
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        # Verify document integrity
        hash_verifier = HashVerificationService(storage_client)
        integrity_result = await hash_verifier.verify_document_integrity(
            document_id=document_id,
            blob_name=metadata.blob_name,
            expected_hash=sha256,
            expected_size=size
        )
        
        if not integrity_result["verified"]:
            logger.error(f"Document integrity verification failed for {document_id}: {integrity_result.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document integrity verification failed: {integrity_result.get('error')}"
            )
        
        # Update document status and hash
        metadata.sha256_hash = sha256
        metadata.status = "uploaded"
        if size:
            metadata.size_bytes = size
        
        await db.commit()
        await db.refresh(metadata)
        
        logger.info(f"Document {document_id} confirmed with hash {sha256[:16]}...")
        
        # Publish document uploaded event
        await service_bus_publisher.publish_document_uploaded(
            document_id=document_id,
            citizen_id=str(metadata.citizen_id),
            filename=metadata.filename,
            content_type=metadata.content_type,
            blob_name=metadata.blob_name,
            size_bytes=metadata.size_bytes
        )

        return {
            "message": "Upload confirmed", 
            "document_id": document_id,
            "integrity_verified": True,
            "hash_verified": integrity_result["hash_verified"],
            "size_verified": integrity_result["size_verified"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm upload",
        )


@router.get("/")
async def list_documents(
    citizen_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    """List all documents for a citizen."""
    logger.info(f"Listing documents for citizen {citizen_id}")

    try:
        from sqlalchemy import select
        result = await db.execute(
            select(DocumentMetadata)
            .where(DocumentMetadata.citizen_id == citizen_id)
            .where(DocumentMetadata.is_deleted == False)
            .order_by(DocumentMetadata.created_at.desc())
        )
        documents = result.scalars().all()
        
        logger.info(f"Found {len(documents)} documents for citizen {citizen_id}")
        
        return [
            {
                "id": doc.id,
                "title": doc.title,
                "filename": doc.filename,
                "content_type": doc.content_type,
                "status": doc.status,
                "size_bytes": doc.size_bytes,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
            }
            for doc in documents
        ]

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        # Return empty list instead of raising exception
        return []


@router.get("/stats")
async def get_document_stats(
    citizen_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get document statistics for dashboard."""
    logger.info(f"Getting document stats for citizen {citizen_id}")

    try:
        from sqlalchemy import select, func
        from sqlalchemy.orm import aliased
        
        # Total documents
        total_result = await db.execute(
            select(func.count(DocumentMetadata.id))
            .where(DocumentMetadata.citizen_id == citizen_id)
            .where(DocumentMetadata.is_deleted == False)
        )
        total_documents = total_result.scalar() or 0
        
        # Signed documents (assuming status 'signed' means signed)
        signed_result = await db.execute(
            select(func.count(DocumentMetadata.id))
            .where(DocumentMetadata.citizen_id == citizen_id)
            .where(DocumentMetadata.status == "signed")
            .where(DocumentMetadata.is_deleted == False)
        )
        signed_documents = signed_result.scalar() or 0
        
        # For now, return mock data for transfers
        # Transfer service stats
        return {
            "totalDocuments": total_documents,
            "signedDocuments": signed_documents,
            "pendingTransfers": 0,
        }

    except Exception as e:
        logger.error(f"Error getting document stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document stats",
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    citizen_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Soft delete a document."""
    logger.info(f"Deleting document {document_id} for citizen {citizen_id}")

    try:
        from sqlalchemy import select
        result = await db.execute(
            select(DocumentMetadata)
            .where(DocumentMetadata.id == document_id)
            .where(DocumentMetadata.citizen_id == citizen_id)
        )
        metadata = result.scalar_one_or_none()
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        if metadata.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Document {document_id} already deleted"
            )
        
        # Soft delete
        metadata.is_deleted = True
        await db.commit()
        
        logger.info(f"Document {document_id} soft deleted")
        
        # Publish document deleted event
        await service_bus_publisher.publish_document_deleted(
            document_id=document_id,
            citizen_id=citizen_id
        )
        
        return {"message": "Document deleted successfully", "document_id": document_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )


@router.post("/{document_id}/verify-integrity")
async def verify_document_integrity(
    document_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Verify document integrity by checking hash and size."""
    logger.info(f"Verifying integrity for document {document_id}")

    try:
        from sqlalchemy import select
        result = await db.execute(
            select(DocumentMetadata).where(DocumentMetadata.id == document_id)
        )
        metadata = result.scalar_one_or_none()
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        if metadata.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Document {document_id} has been deleted"
            )
        
        if not metadata.sha256_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document {document_id} has no hash stored"
            )
        
        # Verify document integrity
        hash_verifier = HashVerificationService(storage_client)
        integrity_result = await hash_verifier.verify_document_integrity(
            document_id=document_id,
            blob_name=metadata.blob_name,
            expected_hash=metadata.sha256_hash,
            expected_size=metadata.size_bytes
        )
        
        return {
            "document_id": document_id,
            "integrity_verified": integrity_result["verified"],
            "hash_verified": integrity_result["hash_verified"],
            "size_verified": integrity_result["size_verified"],
            "actual_hash": integrity_result.get("actual_hash"),
            "expected_hash": integrity_result.get("expected_hash"),
            "blob_size": integrity_result.get("blob_size"),
            "error": integrity_result.get("error")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying document integrity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify document integrity",
        )


@router.get("/config")
async def get_service_config() -> dict:
    """Get service configuration (debug only)."""
    if not config.debug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Configuration endpoint only available in debug mode"
        )
    
    return {
        "environment": config.environment,
        "debug": config.debug,
        "log_level": config.log_level,
        "database": {
            "host": config.database_host,
            "port": config.database_port,
            "name": config.database_name,
            "user": config.database_user,
            "sslmode": config.database_sslmode,
            "is_azure": config.is_azure_environment()
        },
        "azure_storage": {
            "account_name": config.azure_storage_account_name,
            "container_name": config.azure_storage_container_name,
            "sas_ttl_minutes": config.azure_storage_sas_ttl_minutes,
            "has_connection_string": bool(config.azure_storage_connection_string),
            "has_account_key": bool(config.azure_storage_account_key)
        },
        "servicebus": {
            "enabled": config.servicebus_enabled,
            "has_connection_string": bool(config.servicebus_connection_string),
            "namespace": config.servicebus_namespace
        },
        "max_file_size": config.max_file_size,
        "allowed_extensions": config.allowed_extensions
    }
