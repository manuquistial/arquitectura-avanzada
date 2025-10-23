"""Ingestion schemas."""

from pydantic import BaseModel, Field


class UploadURLRequest(BaseModel):
    """Request for presigned upload URL."""

    citizen_id: str = Field(..., description="Citizen ID")
    filename: str = Field(..., description="Document filename")
    content_type: str = Field(..., description="MIME type")
    title: str = Field(..., description="Document title")
    description: str | None = Field(None, description="Document description")


class UploadURLResponse(BaseModel):
    """Response with presigned upload URL."""

    upload_url: str = Field(..., description="Presigned PUT URL")
    document_id: str = Field(..., description="Document UUID")
    blob_name: str = Field(..., description="Azure Blob name")
    expires_in: int = Field(..., description="URL expiration in seconds")


class DownloadURLRequest(BaseModel):
    """Request for presigned download URL."""

    document_id: str = Field(..., description="Document UUID")


class DownloadURLResponse(BaseModel):
    """Response with presigned download URL."""

    download_url: str = Field(..., description="Presigned GET URL")
    expires_in: int = Field(..., description="URL expiration in seconds")


class DocumentMetadata(BaseModel):
    """Document metadata."""

    document_id: str
    citizen_id: str
    title: str
    description: str | None
    filename: str
    content_type: str
    blob_name: str

