"""
Chat history management utilities.
"""
from typing import List, Dict, Any, Optional
import uuid

from sqlmodel import Session, select

from app.models import ChatHistory, ChatHistoryCreate, User, Child
from app.rag.child_details import get_child_details_for_rag


def save_chat_interaction(
    db: Session,
    user_id: uuid.UUID,
    session_id: str,
    user_query: str,
    ai_response: str,
    model: str,
    child_id: Optional[uuid.UUID] = None,
    sources: Optional[List[Dict[str, Any]]] = None
) -> ChatHistory:
    """
    Save a chat interaction to the database.

    Args:
        db: Database session
        user_id: User ID
        session_id: Session ID
        user_query: User's question
        ai_response: AI's response
        model: Model name
        child_id: Optional child ID
        sources: Optional list of source documents

    Returns:
        ChatHistory instance
    """
    # Create chat history record
    chat_history_data = ChatHistoryCreate(
        user_id=user_id,
        child_id=child_id,
        session_id=session_id,
        user_query=user_query,
        ai_response=ai_response,
        model=model
    )

    # Convert sources to list of strings (document IDs)
    source_ids = []
    if sources:
        for source in sources:
            if 'document_id' in source:
                source_ids.append(source['document_id'])

    # Create chat history instance
    chat_history = ChatHistory(
        **chat_history_data.model_dump(),
        sources=source_ids if source_ids else None
    )

    # Add to database
    db.add(chat_history)
    db.commit()
    db.refresh(chat_history)

    return chat_history


def get_chat_history(
    db: Session,
    session_id: str,
    limit: int = 10
) -> List[Dict[str, str]]:
    """
    Get chat history for a session.

    Args:
        db: Database session
        session_id: Session ID
        limit: Maximum number of messages to return

    Returns:
        List of messages in the format expected by LangChain
    """
    # Query chat history
    statement = (
        select(ChatHistory)
        .where(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
    )

    chat_histories = db.exec(statement).all()

    # Format for LangChain
    messages = []
    for chat in reversed(chat_histories):  # Reverse to get chronological order
        messages.extend([
            {"role": "human", "content": chat.user_query},
            {"role": "ai", "content": chat.ai_response}
        ])

    return messages


def get_child_info(db: Session, child_id: uuid.UUID, query: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get child information with optional relevant details based on query.

    Args:
        db: Database session
        child_id: Child ID
        query: Optional query to find relevant child details

    Returns:
        Dictionary with child information or None if not found
    """
    # Query child
    child = db.get(Child, child_id)
    if not child:
        return None

    # Calculate age
    from datetime import datetime
    today = datetime.now().date()
    age_days = (today - child.birthday).days
    age_months = age_days // 30
    age_years = age_days // 365

    # Format child info
    child_info = {
        "name": child.name,
        "gender": child.gender,
        "birthday": child.birthday.isoformat(),
        "age_days": age_days,
        "age_months": age_months,
        "age_years": age_years
    }

    # Add relevant child details if query is provided
    if query:
        relevant_details = get_child_details_for_rag(db, child_id, query)
        if relevant_details:
            # Format details for better readability in the prompt
            formatted_details = []
            for detail in relevant_details:
                # Extract content first to avoid backslash in f-string
                content_text = detail['content'].split('Content: ')[1].split('\n')[0]
                formatted_detail = f"- {detail['metadata']['detail_type']}: {content_text}"
                formatted_details.append(formatted_detail)

            child_info["relevant_details"] = formatted_details

    return child_info
