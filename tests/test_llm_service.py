"""
Unit tests for LLM service
"""
import pytest
from app.services.llm_service import LLMService


def test_llm_service_initialization():
    """Test LLM service can be initialized"""
    service = LLMService()
    assert service is not None
    assert service.default_model is not None


def test_token_counting():
    """Test token counting estimation"""
    service = LLMService()
    text = "This is a test message with some content."
    tokens = service.count_tokens(text)
    assert tokens > 0
    assert isinstance(tokens, int)


def test_message_formatting():
    """Test message formatting for LLM"""
    service = LLMService()
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    formatted = service.format_messages_for_llm(messages)
    assert len(formatted) == 2
    assert formatted[0]["role"] == "user"
    assert formatted[0]["content"] == "Hello"

