"""
API routes for chat functionality.
"""
from typing import Any, List, Dict
import uuid
import httpx

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from pydantic import BaseModel

from app.api.deps import get_current_active_user, get_db
from app.models import (
    User, Child, ChatRequest, ChatResponse, ChatHistory, ChatHistoriesPublic
)
from app.rag.rag_chain import generate_response
from app.rag.chat_history import save_chat_interaction, get_chat_history, get_child_info
from app.core.config import settings


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: str = ""


class ModelsResponse(BaseModel):
    models: List[ModelInfo]

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    *,
    db: Session = Depends(get_db),
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Chat with the AI assistant.
    """
    # Generate session ID if not provided
    session_id = chat_request.session_id or str(uuid.uuid4())

    # Get child info if child_id is provided
    child_info = None
    if chat_request.child_id:
        # Check if child exists and belongs to current user
        child = db.get(Child, chat_request.child_id)
        if not child:
            raise HTTPException(status_code=404, detail="Child not found")
        if child.parent_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        # Get child info
        child_info = get_child_info(db, chat_request.child_id)

    # Get chat history
    chat_history = get_chat_history(db, session_id)

    # Generate response
    try:
        result = await generate_response(
            question=chat_request.question,
            chat_history=chat_history,
            session_id=session_id,
            child_info=child_info,
            model_name=chat_request.model
        )

        # Save chat interaction
        save_chat_interaction(
            db=db,
            user_id=current_user.id,
            session_id=session_id,
            user_query=chat_request.question,
            ai_response=result["answer"],
            model=chat_request.model,
            child_id=chat_request.child_id,
            sources=result.get("sources")
        )

        return ChatResponse(
            answer=result["answer"],
            session_id=session_id,
            sources=result.get("sources")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=ChatHistoriesPublic)
def get_chat_histories(
    *,
    db: Session = Depends(get_db),
    session_id: str = None,
    child_id: uuid.UUID = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get chat history.
    """
    # Build query
    query = select(ChatHistory).where(ChatHistory.user_id == current_user.id)

    # Filter by session_id if provided
    if session_id:
        query = query.where(ChatHistory.session_id == session_id)

    # Filter by child_id if provided
    if child_id:
        # Check if child exists and belongs to current user
        child = db.get(Child, child_id)
        if not child:
            raise HTTPException(status_code=404, detail="Child not found")
        if child.parent_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")

        query = query.where(ChatHistory.child_id == child_id)

    # Add pagination
    query = query.order_by(ChatHistory.created_at.desc()).offset(skip).limit(limit)

    # Execute query
    chat_histories = db.exec(query).all()

    # Count total
    count_query = select(ChatHistory).where(ChatHistory.user_id == current_user.id)
    if session_id:
        count_query = count_query.where(ChatHistory.session_id == session_id)
    if child_id:
        count_query = count_query.where(ChatHistory.child_id == child_id)
    total_count = len(db.exec(count_query).all())

    return ChatHistoriesPublic(data=chat_histories, count=total_count)


@router.get("/sessions", response_model=List[str])
def get_chat_sessions(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get unique chat sessions for the current user.
    """
    query = (
        select(ChatHistory.session_id)
        .where(ChatHistory.user_id == current_user.id)
        .distinct()
    )

    sessions = db.exec(query).all()
    return sessions


@router.get("/models", response_model=ModelsResponse)
async def get_available_models(
    *,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get available models from OpenRouter.
    """
    try:
        # Define a list of recommended models for parenting assistant
        recommended_models = [
            ModelInfo(
                id="openai/gpt-4o-mini",
                name="GPT-4o Mini",
                provider="OpenAI",
                description="Smaller, faster, and more affordable version of GPT-4o"
            ),
            ModelInfo(
                id="anthropic/claude-3-opus",
                name="Claude 3 Opus",
                provider="Anthropic",
                description="Anthropic's most powerful model for complex tasks"
            ),
            ModelInfo(
                id="anthropic/claude-3-sonnet",
                name="Claude 3 Sonnet",
                provider="Anthropic",
                description="Balanced model for most tasks"
            ),
            ModelInfo(
                id="anthropic/claude-3-haiku",
                name="Claude 3 Haiku",
                provider="Anthropic",
                description="Fast and efficient model for simpler tasks"
            ),
            ModelInfo(
                id="google/gemini-pro",
                name="Gemini Pro",
                provider="Google",
                description="Google's advanced model for various tasks"
            ),
        ]

        # You could also fetch models dynamically from OpenRouter API
        # headers = {
        #     "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        #     "HTTP-Referer": settings.FRONTEND_HOST,
        # }
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         f"{settings.OPENROUTER_BASE_URL}/models",
        #         headers=headers,
        #     )
        #     response.raise_for_status()
        #     models_data = response.json()
        #     # Process models data...

        return ModelsResponse(models=recommended_models)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching models: {str(e)}")
