"""Documents API router - Updated for Azure."""

import logging
import os

from fastapi import APIRouter, HTTPException, status

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
    )
else:
    # AWS S3 (legacy)
    from app.s3_client import S3DocumentClient
    
    storage_client = S3DocumentClient(
        bucket=os.getenv("S3_BUCKET", "carpeta-ciudadana-documents"),
        region=os.getenv("AWS_REGION", "us-east-1"),
    )


@router.post("/upload-url", response_model=UploadURLResponse)
async def get_upload_url(request: UploadURLRequest) -> UploadURLResponse:
    """Get presigned URL for uploading a document.

    The frontend will use this URL to upload directly to storage using PUT.
    Works with both Azure Blob Storage and AWS S3.
    """
    logger.info(
        f"Generating upload URL for citizen {request.citizen_id}, "
        f"file: {request.filename} (provider: {CLOUD_PROVIDER})"
    )

    try:
        result = storage_client.generate_presigned_put(
            citizen_id=request.citizen_id,
            filename=request.filename,
            content_type=request.content_type,
            expires_in=3600,
        )

        # TODO: Store metadata in database
        # TODO: Publish event to Service Bus/SQS

        if CLOUD_PROVIDER == "azure":
            key = result["blob_name"]
        else:
            key = result["s3_key"]

        return UploadURLResponse(
            upload_url=result["upload_url"],
            document_id=result["document_id"],
            s3_key=key,  # Compatible field name
            expires_in=3600,
        )

    except Exception as e:
        logger.error(f"Error generating upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        )


@router.post("/download-url", response_model=DownloadURLResponse)
async def get_download_url(request: DownloadURLRequest) -> DownloadURLResponse:
    """Get presigned URL for downloading a document."""
    logger.info(
        f"Generating download URL for document {request.document_id} "
        f"(provider: {CLOUD_PROVIDER})"
    )

    try:
        # TODO: Get blob_name/s3_key from database using document_id
        # For now, using placeholder
        if CLOUD_PROVIDER == "azure":
            key = f"documents/{request.document_id}"
        else:
            key = f"documents/{request.document_id}"

        download_url = storage_client.generate_presigned_get(
            key,
            expires_in=3600,
        )

        # TODO: Log access in audit trail

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
) -> dict[str, str]:
    """Confirm document upload and verify integrity.

    Called by frontend after successful PUT to storage.
    """
    logger.info(f"Confirming upload for document {document_id}")

    try:
        # TODO: Get document metadata from database
        # TODO: Verify SHA-256 hash
        # TODO: Update document status
        # TODO: Publish event to Service Bus/SQS
        # TODO: Trigger indexing in Search service

        return {"message": "Upload confirmed", "document_id": document_id}

    except Exception as e:
        logger.error(f"Error confirming upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm upload",
        )
