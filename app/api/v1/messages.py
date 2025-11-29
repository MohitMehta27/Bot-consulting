"""
Message API endpoints
"""
import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.message import MessageCreate, MessageCreateResponse, MessageResponse
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.llm_service import LLMService
from app.services.context_manager import ContextManager
from app.services.rag_service import RAGService
from app.utils.errors import ConversationNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["messages"])

# Initialize services
conversation_repo = ConversationRepository()
message_repo = MessageRepository()
llm_service = LLMService()
context_manager = ContextManager()
rag_service = RAGService()


@router.post("/{conversation_id}/messages", response_model=MessageCreateResponse, status_code=status.HTTP_201_CREATED)
async def add_message(conversation_id: str, message_data: MessageCreate):
    """
    Add a new message to an existing conversation
    """
    try:
        # Get conversation
        conversation = conversation_repo.get_conversation_by_id(conversation_id)
        conv_db_id = conversation['id']
        mode = conversation['mode']
        
        # Save user message
        user_message = message_repo.create_message(
            conv_db_id=conv_db_id,
            role="user",
            content=message_data.content
        )
        
        # Get conversation history
        all_messages = message_repo.get_messages_by_conversation(conv_db_id)
        
        # Retrieve chunks if RAG should be enabled
        retrieved_chunks = None
        # Enable RAG either when mode is explicitly grounded_chat or when the conversation has linked documents
        linked_docs = conversation_repo.get_linked_documents(conv_db_id)
        rag_enabled = mode == "grounded_chat" or bool(linked_docs)
        if rag_enabled:
            retrieved_chunks = rag_service.retrieve_relevant_chunks(
                conversation_id=conversation_id,
                user_query=message_data.content
            )
        
        # Prepare context
        if rag_enabled:
            system_prompt = context_manager.build_rag_system_prompt(message_data.content)
        else:
            system_prompt = context_manager.build_open_chat_system_prompt()
        
        # Format messages for LLM
        formatted_messages = llm_service.format_messages_for_llm(all_messages)
        
        # Prepare context with token management
        context_messages = context_manager.prepare_context(
            messages=formatted_messages,
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
        
        # Get updated conversation for total tokens
        updated_conv = conversation_repo.get_conversation_by_db_id(conv_db_id)
        
        return MessageCreateResponse(
            message=MessageResponse(**assistant_message),
            tokens_used=llm_response['tokens_used'],
            total_tokens=updated_conv['total_tokens']
        )
        
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
