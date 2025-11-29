"""
LLM integration service (OpenAI)
"""
import logging
import openai
from typing import List, Dict, Any, Optional
from app.config import settings
from app.utils.errors import LLMServiceError

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai.api_key = settings.OPENAI_API_KEY


class LLMService:
    """Service for interacting with OpenAI LLM"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = settings.DEFAULT_MODEL
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate response from LLM
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        
        Returns:
            Dict with 'content', 'tokens_used', 'model_used'
        """
        try:
            model = model or self.default_model
            
            logger.info(f"Calling OpenAI API with model: {model}, messages: {len(messages)}")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            assistant_message = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            logger.info(f"OpenAI response received. Tokens used: {tokens_used}")
            
            return {
                'content': assistant_message,
                'tokens_used': tokens_used,
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'model_used': model
            }
            
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit error: {e}")
            raise LLMServiceError("Rate limit exceeded. Please try again later.")
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMServiceError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in LLM service: {e}")
            raise LLMServiceError(f"Failed to generate response: {str(e)}")
    
    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Estimate token count for text
        Simple estimation: ~4 characters per token
        For accurate count, would need tiktoken library
        """
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def format_messages_for_llm(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Format messages from database format to OpenAI format
        """
        formatted = []
        for msg in messages:
            formatted.append({
                'role': msg.get('role', 'user'),
                'content': msg.get('content', '')
            })
        return formatted
