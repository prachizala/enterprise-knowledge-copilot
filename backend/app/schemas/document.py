import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

VALID_STATUSES = {"uploaded", "processing", "processed", "failed"}
VALID_EXTRACTION_STATUSES = {"pending", "processing", "completed", "failed"}


class DocumentBase(BaseModel):
    """Base document metadata attributes."""
    filename: str = Field(..., min_length=1, max_length=255, examples=["security_policy.pdf"])
    original_filename: str = Field(..., min_length=1, max_length=255, examples=["security_policy.pdf"])
    file_type: str = Field(..., min_length=1, max_length=50, examples=["pdf"])
    file_size: int = Field(..., ge=0, examples=[245678])
    department: str = Field(..., min_length=1, max_length=100, examples=["Security"])
    owner: str = Field(..., min_length=1, max_length=100, examples=["Security Team"])
    description: Optional[str] = Field(None, examples=["Enterprise security policy"])
    version: str = Field("1.0", max_length=50, examples=["2.0"])


class DocumentCreate(DocumentBase):
    """Schema for registering new document metadata."""
    pass


class DocumentUpdate(BaseModel):
    """Schema for partially updating document metadata."""
    filename: Optional[str] = Field(None, min_length=1, max_length=255)
    original_filename: Optional[str] = Field(None, min_length=1, max_length=255)
    file_type: Optional[str] = Field(None, min_length=1, max_length=50)
    file_size: Optional[int] = Field(None, ge=0)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    owner: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[str] = Field(None, examples=["processed"])
    version: Optional[str] = Field(None, max_length=50)
    extraction_status: Optional[str] = Field(None, examples=["completed"])
    processing_error: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Allowed: {', '.join(sorted(VALID_STATUSES))}")
        return v.lower() if v is not None else None

    @field_validator("extraction_status")
    @classmethod
    def validate_extraction_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in VALID_EXTRACTION_STATUSES:
            raise ValueError(f"Invalid extraction status '{v}'. Allowed: {', '.join(sorted(VALID_EXTRACTION_STATUSES))}")
        return v.lower() if v is not None else None


class DocumentResponse(DocumentBase):
    """Schema for serialized document metadata output."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., examples=["9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"])
    status: str = Field(..., examples=["processed"])
    mime_type: Optional[str] = Field(None, examples=["application/pdf"])
    extraction_status: str = Field("pending", examples=["completed"])
    extracted_text_length: int = Field(0, examples=[18432])
    total_chunks: int = Field(0, examples=[12])
    embedding_status: str = Field("not_started", examples=["completed"])
    embedded_chunks: int = Field(0, examples=[12])
    embedding_model: Optional[str] = Field(None, examples=["text-embedding-3-small"])
    entity_extraction_status: str = Field("not_started", examples=["completed"])
    entity_mention_count: int = Field(0, examples=[42])
    unique_entity_count: int = Field(0, examples=[15])
    relationship_extraction_status: str = Field("not_started", examples=["completed"])
    relationship_count: int = Field(0, examples=[24])
    processing_error: Optional[str] = Field(None, examples=[None])
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Schema for paginated document list output."""
    total: int = Field(..., examples=[42])
    documents: List[DocumentResponse]


class DocumentContentResponse(BaseModel):
    """Schema for extracted document text content and word count metrics."""
    model_config = ConfigDict(from_attributes=True)

    document_id: str = Field(..., examples=["9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"])
    text: str = Field(..., description="Full extracted text content")
    character_count: int = Field(..., examples=[12345])
    word_count: int = Field(..., examples=[2100])
    page_count: Optional[int] = Field(None, examples=[5])
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentChunkResponse(BaseModel):
    """Schema for individual document text chunk and provenance."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., examples=["a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"])
    document_id: str = Field(..., examples=["9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"])
    chunk_index: int = Field(..., examples=[0])
    content: str = Field(..., description="Text passage content of the chunk")
    char_count: int = Field(..., examples=[450])
    token_count: int = Field(..., examples=[112])
    page_number: Optional[int] = Field(None, examples=[1])
    section_header: Optional[str] = Field(None, examples=["Security Policy > Authentication"])
    chunk_metadata: Optional[str] = Field(None, description="Serialized JSON metadata")
    content_hash: Optional[str] = Field(None, description="SHA-256 hash of chunk content")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @computed_field
    def metadata(self) -> Optional[Dict[str, Any]]:
        """Return parsed dictionary representation of chunk_metadata."""
        if self.chunk_metadata:
            try:
                return json.loads(self.chunk_metadata)
            except Exception:
                return {}
        return None


class DocumentChunkListResponse(BaseModel):
    """Schema for paginated list of document chunks."""
    total: int = Field(..., examples=[18])
    document_id: str = Field(..., examples=["9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"])
    skip: int = Field(0, examples=[0])
    limit: int = Field(50, examples=[50])
    chunks: List[DocumentChunkResponse]

