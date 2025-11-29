"""
Conversation API endpoints
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
    ConversationDetailResponse
)
from app.schemas.message import MessageCreateResponse, MessageResponse
from app.repositories.user_repository import UserRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.document_repository import DocumentRepository
from app.services.llm_service import LLMService
from app.services.context_manager import ContextManager
from app.services.rag_service import RAGService
from app.utils.errors import ConversationNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])

# Initialize services
user_repo = UserRepository()
conversation_repo = ConversationRepository()
message_repo = MessageRepository()
document_repo = DocumentRepository()
llm_service = LLMService()
context_manager = ContextManager()
rag_service = RAGService()


@router.post("", response_model=MessageCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(conversation_data: ConversationCreate):
    """
    Create a new conversation with first message
    """
    try:
        # Get or create user
        user = user_repo.get_or_create_user(
            user_id=conversation_data.user_id,
            username=None,
            email=None
        )
        user_db_id = user['id']
        
        # Create conversation
        conversation = conversation_repo.create_conversation(
            user_db_id=user_db_id,
            mode=conversation_data.mode.value,
            title=conversation_data.title
        )
        conv_db_id = conversation['id']
        conversation_id = conversation['conversation_id']
        
        # Link documents if RAG mode
        if conversation_data.mode.value == "grounded_chat" and conversation_data.document_ids:
            for doc_id in conversation_data.document_ids:
                try:
                    document = document_repo.get_document_by_id(doc_id)
                    conversation_repo.link_document(conv_db_id, document['id'])
                except Exception as e:
                    logger.warning(f"Failed to link document {doc_id}: {e}")
        
        # Save user's first message
        user_message = message_repo.create_message(
            conv_db_id=conv_db_id,
            role="user",
            content=conversation_data.first_message
        )
        
        # Prepare context for LLM
        messages = [user_message]
        
        # Retrieve chunks if RAG mode
        retrieved_chunks = None
        if conversation_data.mode.value == "grounded_chat":
            retrieved_chunks = rag_service.retrieve_relevant_chunks(
                conversation_id=conversation_id,
                user_query=conversation_data.first_message
            )
        
        # Prepare context
        rag_enabled = conversation_data.mode.value == "grounded_chat" or bool(conversation_data.document_ids)
        if rag_enabled:
            system_prompt = context_manager.build_rag_system_prompt(conversation_data.first_message)
        else:
            system_prompt = context_manager.build_open_chat_system_prompt()
        
        context_messages = context_manager.prepare_context(
            messages=llm_service.format_messages_for_llm(messages),
            system_prompt=system_prompt,
            retrieved_chunks=retrieved_chunks,
            rag_enabled=rag_enabled,
        )
        
        # Call LLM
        llm_response = llm_service.generate_response(context_messages)
        
        # Save assistant response
        assistant_message = message_repo.create_message(
            conv_db_id=conv_db_id,
            role="assistant",
            content=llm_response['content'],
            tokens_used=llm_response['tokens_used'],
            metadata={
                'model': llm_response['model_used'],
                'prompt_tokens': llm_response['prompt_tokens'],
                'completion_tokens': llm_response['completion_tokens']
            }
        )
        
        # Parse metadata JSON string to dict if needed
        if assistant_message.get('metadata') and isinstance(assistant_message['metadata'], str):
            import json
            assistant_message['metadata'] = json.loads(assistant_message['metadata'])
        
        # Update conversation stats
        total_tokens = llm_response['tokens_used']
        message_count = message_repo.get_message_count(conv_db_id)
        conversation_repo.update_conversation_stats(conv_db_id, total_tokens, message_count)
        
        return MessageCreateResponse(
            message=MessageResponse(**assistant_message),
            conversation_id=conversation_id,
            tokens_used=llm_response['tokens_used'],
            total_tokens=total_tokens
        )
        
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page")
):
    """
    List all conversations for a user
    """
    try:
        user = user_repo.get_user_by_id(user_id)
        conversations, total = conversation_repo.list_conversations(
            user_db_id=user['id'],
            page=page,
            limit=limit
        )
        
        return ConversationListResponse(
            conversations=[ConversationResponse(**conv) for conv in conversations],
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: str):
    """
    Get conversation details with all messages
    """
    try:
        conversation = conversation_repo.get_conversation_by_id(conversation_id)
        conv_db_id = conversation['id']
        
        # Get all messages
        messages = message_repo.get_messages_by_conversation(conv_db_id)
        
        # Format messages
        formatted_messages = [
            {
                "role": msg['role'],
                "content": msg['content'],
                "sequence_number": msg['sequence_number'],
                "created_at": msg['created_at'].isoformat() if hasattr(msg['created_at'], 'isoformat') else str(msg['created_at'])
            }
            for msg in messages
        ]
        
        return ConversationDetailResponse(
            conversation_id=conversation['conversation_id'],
            title=conversation.get('title'),
            mode=conversation['mode'],
            status=conversation['status'],
            total_tokens=conversation['total_tokens'],
            total_messages=conversation['total_messages'],
            messages=formatted_messages,
            created_at=conversation['created_at'],
            updated_at=conversation['updated_at']
        )
        
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation (soft delete)
    """
    try:
        conversation_repo.delete_conversation(conversation_id)
        return {"message": "Conversation deleted successfully"}
        
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
