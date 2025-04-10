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

from app.core.config import settings


class OpenRouterChatModel(BaseChatModel):
    """Chat model that uses OpenRouter API."""
    
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "openai/gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    
    def _generate(
        self, messages: List[BaseMessage], stop: Optional[List[str]] = None, 
        run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any
    ) -> ChatResult:
        """Generate a chat response."""
        message_dicts = []
        
        # Convert LangChain messages to OpenRouter format
        for message in messages:
            if isinstance(message, SystemMessage):
                message_dicts.append({"role": "system", "content": message.content})
            elif isinstance(message, HumanMessage):
                message_dicts.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                message_dicts.append({"role": "assistant", "content": message.content})
            elif isinstance(message, ChatMessage):
                message_dicts.append({"role": message.role, "content": message.content})
            else:
                raise ValueError(f"Got unknown message type: {message}")
        
        # Prepare the request payload
        payload = {
            "model": self.model,
            "messages": message_dicts,
            "temperature": self.temperature,
        }
        
        # Add optional parameters if provided
        if stop:
            payload["stop"] = stop
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        if self.top_p:
            payload["top_p"] = self.top_p
        
        # Add additional kwargs
        for key, value in kwargs.items():
            payload[key] = value
        
        # Make the API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.FRONTEND_HOST,  # Required by OpenRouter
            "X-Title": settings.PROJECT_NAME,  # Optional but recommended
        }
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                response_data = response.json()
                
                # Extract the response content
                message_content = response_data["choices"][0]["message"]["content"]
                
                # Create a ChatGeneration object
                generation = ChatGeneration(
                    message=AIMessage(content=message_content),
                    generation_info={"finish_reason": response_data["choices"][0].get("finish_reason")}
                )
                
                # Return the ChatResult
                return ChatResult(generations=[generation])
        
        except Exception as e:
            raise ValueError(f"Error calling OpenRouter API: {str(e)}")
    
    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return "openrouter"


def get_openrouter_chat_model(
    model: str = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
) -> OpenRouterChatModel:
    """
    Get an OpenRouterChatModel instance.
    
    Args:
        model: Model name (e.g., "openai/gpt-4o-mini", "anthropic/claude-3-opus")
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        
    Returns:
        OpenRouterChatModel instance
    """
    return OpenRouterChatModel(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        model=model or settings.DEFAULT_LLM_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
    )
