"""
Pydantic schemas for document requests/responses
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentCreate(BaseModel):
    """Schema for creating a document"""
    user_id: str = Field(..., description="User identifier")
    filename: str = Field(..., description="Document filename")
    file_type: Optional[str] = None
    file_size: Optional[int] = None


class DocumentResponse(BaseModel):
    """Schema for document response"""
    id: int
    document_id: str
    user_id: int
    filename: str
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentChunkResponse(BaseModel):
    """Schema for document chunk response"""
    id: int
    chunk_id: str
    document_id: int
    chunk_text: str
    chunk_index: int
    token_count: int
    created_at: datetime

    class Config:
        from_attributes = True
