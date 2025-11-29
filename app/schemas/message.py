"""
Pydantic schemas for message requests/responses
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class MessageCreate(BaseModel):
    """Schema for creating a message"""
    content: str = Field(..., description="Message content")
    role: Optional[str] = Field(default="user", description="Message role")


class MessageResponse(BaseModel):
    """Schema for message response"""
    id: int
    message_id: str
    conversation_id: int
    role: str
    content: str
    tokens_used: int
    sequence_number: int
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreateResponse(BaseModel):
    """Schema for message creation response"""
    message: MessageResponse
    conversation_id: Optional[str] = None
    tokens_used: int
    total_tokens: int
