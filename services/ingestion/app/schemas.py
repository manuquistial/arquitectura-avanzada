"""Ingestion schemas."""

from pydantic import BaseModel, Field


class UploadURLRequest(BaseModel):
    """Request for presigned upload URL."""

    citizen_id: int = Field(..., description="Citizen ID")
    filename: str = Field(..., description="Document filename")
    content_type: str = Field(..., description="MIME type")
    title: str = Field(..., description="Document title")
    description: str | None = Field(None, description="Document description")


class UploadURLResponse(BaseModel):
    """Response with presigned upload URL."""

    upload_url: str = Field(..., description="Presigned PUT URL")
    document_id: str = Field(..., description="Document UUID")
    s3_key: str = Field(..., description="S3 object key")
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
    citizen_id: int
    title: str
    description: str | None
    filename: str
    content_type: str
    s3_key: str
    s3_bucket: str

