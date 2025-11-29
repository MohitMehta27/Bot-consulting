"""
Pydantic schemas for conversation requests/responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ConversationMode(str, Enum):
    """Conversation mode enum"""
    OPEN_CHAT = "open_chat"
    GROUNDED_CHAT = "grounded_chat"


class ConversationCreate(BaseModel):
    """Schema for creating a conversation"""
    user_id: str = Field(..., description="User identifier")
    first_message: str = Field(..., description="First message in the conversation")
    mode: ConversationMode = Field(default=ConversationMode.OPEN_CHAT, description="Chat mode")
    document_ids: Optional[List[str]] = Field(default=None, description="Document IDs for RAG mode")
    title: Optional[str] = Field(default=None, description="Conversation title")


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""
    title: Optional[str] = None
    status: Optional[str] = None


class ConversationResponse(BaseModel):
    """Schema for conversation response"""
    id: int
    conversation_id: str
    user_id: int
    title: Optional[str] = None
    mode: str
    status: str
    total_tokens: int
    total_messages: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Schema for conversation list response"""
    conversations: List[ConversationResponse]
    pagination: dict


class ConversationDetailResponse(BaseModel):
    """Schema for conversation detail with messages"""
    conversation_id: str
    title: Optional[str] = None
    mode: str
    status: str
    total_tokens: int
    total_messages: int
    messages: List[dict]
    created_at: datetime
    updated_at: datetime
