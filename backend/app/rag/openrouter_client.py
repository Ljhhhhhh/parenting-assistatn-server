"""
OpenRouter client for LLM integration.
"""
from typing import Dict, List, Any, Optional
import json
import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_openai import ChatOpenAI

from app.core.config import settings


def get_openrouter_chat_model(
    model: str = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    streaming: bool = False,
) -> ChatOpenAI:
    """
    Get an OpenRouterChatModel instance.

    Args:
        model: Model name (e.g., "openai/gpt-4o-mini", "anthropic/claude-3-opus")
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        streaming: Whether to enable streaming

    Returns:
        ChatOpenAI instance configured for OpenRouter
    """
    # Verify API key is available
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "changethis":
        raise ValueError("OpenRouter API key is not configured properly. Please check your .env file.")

    # Print debug information
    print(f"OpenRouter Base URL: {settings.OPENROUTER_BASE_URL}")
    print(f"Using model: {model or settings.DEFAULT_LLM_MODEL}")

    # Required headers for OpenRouter
    headers = {
        "HTTP-Referer": settings.FRONTEND_HOST,  # Optional, for including your website URL
        "X-Title": settings.PROJECT_NAME,       # Optional, for including your app name
    }

    # Instantiate ChatOpenAI and configure it for OpenRouter
    try:
        return ChatOpenAI(
            openai_api_key=settings.OPENROUTER_API_KEY,
            openai_api_base=settings.OPENROUTER_BASE_URL,
            model=model or settings.DEFAULT_LLM_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            streaming=streaming,
            default_headers=headers
        )
    except Exception as e:
        print(f"Error initializing OpenRouter chat model: {str(e)}")
        raise
