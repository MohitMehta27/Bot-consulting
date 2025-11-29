"""
Custom error handlers
"""
from fastapi import HTTPException, status
from typing import Optional


class BotGPTException(HTTPException):
    """Base exception for Bot GPT application"""
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An error occurred",
        headers: Optional[dict] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class ConversationNotFoundError(BotGPTException):
    """Raised when conversation is not found"""
    def __init__(self, conversation_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )


class UserNotFoundError(BotGPTException):
    """Raised when user is not found"""
    def __init__(self, user_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )


class DocumentNotFoundError(BotGPTException):
    """Raised when document is not found"""
    def __init__(self, document_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )


class LLMServiceError(BotGPTException):
    """Raised when LLM service fails"""
    def __init__(self, detail: str = "LLM service error"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )


class ContextTooLongError(BotGPTException):
    """Raised when context exceeds token limit"""
    def __init__(self, detail: str = "Context too long. Please start a new conversation."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
