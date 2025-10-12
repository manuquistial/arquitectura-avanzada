"""Documents API router - Updated for Azure."""

import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import DocumentMetadata
from app.schemas import (
    DownloadURLRequest,
    DownloadURLResponse,
    UploadURLRequest,
    UploadURLResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Detectar cloud provider
CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "azure")

if CLOUD_PROVIDER == "azure":
    from app.azure_storage import AzureBlobDocumentClient
    
    storage_client = AzureBlobDocumentClient(
        account_name=os.getenv("AZURE_STORAGE_ACCOUNT_NAME", ""),
        account_key=os.getenv("AZURE_STORAGE_ACCOUNT_KEY", ""),
        container_name=os.getenv("AZURE_STORAGE_CONTAINER_NAME", "documents"),
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        sas_ttl_minutes=int(os.getenv("SAS_TTL_MINUTES", "15")),
    )
else:
    # AWS S3 (legacy/fallback - not actively used)
    logger.warning("Using AWS S3 client (legacy mode)")
    from app.s3_client import S3DocumentClient
    
    storage_client = S3DocumentClient(
        bucket=os.getenv("S3_BUCKET", "carpeta-ciudadana-documents"),
        region=os.getenv("AWS_REGION", "us-east-1"),
    )


@router.post("/upload-url", response_model=UploadURLResponse)
async def get_upload_url(
    request: UploadURLRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UploadURLResponse:
    """Get presigned URL for uploading a document.

    The frontend will use this URL to upload directly to storage using PUT.
    Works with both Azure Blob Storage and AWS S3.
    """
    logger.info(
        f"Generating upload URL for citizen {request.citizen_id}, "
        f"file: {request.filename} (provider: {CLOUD_PROVIDER})"
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
        if CLOUD_PROVIDER == "azure":
            key = result["blob_name"]
        else:
            key = result["s3_key"]
        
        metadata = DocumentMetadata(
            id=result["document_id"],
            citizen_id=request.citizen_id,
            filename=request.filename,
            content_type=request.content_type,
            blob_name=key,
            storage_provider=CLOUD_PROVIDER,
            status="pending",
        )
        
        db.add(metadata)
        await db.commit()
        await db.refresh(metadata)
        
        logger.info(f"Document metadata stored: {metadata.id}")
        
        # TODO: Publish event to Service Bus/SQS for async processing

        # Return TTL in seconds (SAS_TTL_MINUTES * 60)
        sas_ttl_minutes = int(os.getenv("SAS_TTL_MINUTES", "15"))
        
        return UploadURLResponse(
            upload_url=result["upload_url"],
            document_id=result["document_id"],
            s3_key=key,  # Compatible field name
            expires_in=sas_ttl_minutes * 60,
        )

    except Exception as e:
        logger.error(f"Error generating upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        )


@router.post("/download-url", response_model=DownloadURLResponse)
async def get_download_url(
    request: DownloadURLRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DownloadURLResponse:
    """Get presigned URL for downloading a document."""
    logger.info(
        f"Generating download URL for document {request.document_id} "
        f"(provider: {CLOUD_PROVIDER})"
    )

    try:
        # Get blob_name/s3_key from database using document_id
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

        # TODO: Log access in audit trail
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
    document_id: str,
    sha256: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Confirm document upload and verify integrity.

    Called by frontend after successful PUT to storage.
    """
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
        
        # Update document status and hash
        metadata.sha256_hash = sha256
        metadata.status = "uploaded"
        
        await db.commit()
        await db.refresh(metadata)
        
        logger.info(f"Document {document_id} confirmed with hash {sha256[:16]}...")
        
        # TODO: Verify SHA-256 hash against actual blob/file
        # TODO: Publish event to Service Bus/SQS for async processing
        # TODO: Trigger indexing in Search service

        return {"message": "Upload confirmed", "document_id": document_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm upload",
        )
