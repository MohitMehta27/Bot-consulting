"""
Context management service for token/cost optimization
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.config import settings
from app.services.llm_service import LLMService
from app.utils.errors import ContextTooLongError

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages conversation context and token limits"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.max_context_tokens = settings.MAX_CONTEXT_TOKENS
    
    def prepare_context(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        retrieved_chunks: Optional[List[str]] = None,
        rag_enabled: bool = False,
    ) -> List[Dict[str, str]]:
        """
        Prepare context for LLM call with token management
        
        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            retrieved_chunks: Optional retrieved document chunks for RAG
        
        Returns:
            Formatted messages list ready for LLM
        """
        context_messages = []
        
        # Add system prompt if provided
        if system_prompt:
            context_messages.append({
                'role': 'system',
                'content': system_prompt
            })
        
        # Add retrieved chunks as context if RAG mode
        if retrieved_chunks:
            chunks_text = "\n\n".join([f"[Context {i+1}]\n{chunk}" for i, chunk in enumerate(retrieved_chunks)])
            context_content = f"""Use the following context from uploaded documents to answer the user's questions. 
If the user asks about "the file" or "this file", they are referring to the content below.
Answer based on the provided context. If the context doesn't contain enough information, say so.

Context from documents:
{chunks_text}"""
            context_messages.append({
                'role': 'system',
                'content': context_content
            })
            logger.info(f"Added {len(retrieved_chunks)} retrieved chunks to context")
        elif rag_enabled:
            logger.warning("RAG mode enabled but no chunks retrieved")
        
        # Add conversation messages with sliding window
        conversation_messages = self._apply_sliding_window(messages)
        context_messages.extend(conversation_messages)
        
        # Check total token count
        total_tokens = self._estimate_total_tokens(context_messages)
        
        if total_tokens > self.max_context_tokens:
            logger.warning(f"Context too long: {total_tokens} tokens. Applying truncation.")
            context_messages = self._truncate_context(context_messages)
        
        return context_messages
    
    def _apply_sliding_window(self, messages: List[Dict[str, Any]], max_messages: int = 20) -> List[Dict[str, Any]]:
        """
        Apply sliding window: keep only the most recent N messages
        """
        if len(messages) <= max_messages:
            return messages
        
        logger.info(f"Applying sliding window: keeping last {max_messages} of {len(messages)} messages")
        return messages[-max_messages:]
    
    def _estimate_total_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate total tokens in messages"""
        total = 0
        for msg in messages:
            content = msg.get('content', '')
            # Rough estimation: 1 token ≈ 4 characters
            total += len(content) // 4
            # Add overhead for message structure
            total += 5
        return total
    
    def _truncate_context(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Truncate context if it exceeds token limit
        Keeps system prompts and recent messages
        """
        if not messages:
            return messages
        
        # Separate system messages from conversation
        system_msgs = [msg for msg in messages if msg.get('role') == 'system']
        conversation_msgs = [msg for msg in messages if msg.get('role') != 'system']
        
        # Calculate available tokens for conversation
        system_tokens = self._estimate_total_tokens(system_msgs)
        available_tokens = self.max_context_tokens - system_tokens - 100  # Reserve for response
        
        # Keep as many conversation messages as fit
        truncated_conversation = []
        current_tokens = 0
        
        for msg in reversed(conversation_msgs):
            msg_tokens = self._estimate_total_tokens([msg])
            if current_tokens + msg_tokens <= available_tokens:
                truncated_conversation.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        result = system_msgs + truncated_conversation
        
        if not truncated_conversation:
            raise ContextTooLongError("Context too long even after truncation. Please start a new conversation.")
        
        logger.info(f"Truncated context: {len(result)} messages, ~{current_tokens + system_tokens} tokens")
        return result
    
    def build_rag_system_prompt(self, user_query: str) -> str:
        """Build system prompt for RAG mode"""
        # Convert current UTC time to IST (UTC+5:30)
        now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        now = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
        return (
            "You are a helpful assistant that answers questions based on the provided context from documents.\n"
            f"Current date and time: {now}.\n"
            "If the context doesn't contain enough information to answer the question, say so.\n"
            "Always cite which part of the context you're using when possible."
        )

    def build_open_chat_system_prompt(self) -> str:
        """Build system prompt for open chat mode"""
        # Convert current UTC time to IST (UTC+5:30)
        now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        now = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
        return (
            "You are a helpful, honest, and concise AI assistant.\n"
            f"Current date and time: {now}.\n"
            "Use your general knowledge and reasoning to answer the user clearly and directly."
        )
