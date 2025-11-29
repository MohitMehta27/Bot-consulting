"""
Pydantic schemas for user requests/responses
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for creating a user"""
    user_id: str = Field(..., description="External user identifier")
    username: Optional[str] = None
    email: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
