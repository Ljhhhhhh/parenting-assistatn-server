"""
Child detail management utilities for RAG system.
"""
from typing import List, Dict, Any, Optional
import uuid

from sqlmodel import Session, select
from langchain_core.documents import Document

from app.models import ChildDetail, ChildDetailCreate, Child
from app.rag.vectorstore import vectorstore, embedding_function


def save_child_detail(
    db: Session,
    child_detail_in: ChildDetailCreate,
) -> ChildDetail:
    """
    Save a child detail to the database and embed it in the vector store.

    Args:
        db: Database session
        child_detail_in: Child detail data

    Returns:
        ChildDetail instance
    """
    # Create child detail instance
    child_detail = ChildDetail(**child_detail_in.model_dump())

    # Add to database
    db.add(child_detail)
    db.commit()
    db.refresh(child_detail)

    # Embed in vector store
    embedding_id = embed_child_detail(child_detail)

    # Update embedding_id
    child_detail.embedding_id = embedding_id
    db.add(child_detail)
    db.commit()
    db.refresh(child_detail)

    return child_detail


def embed_child_detail(child_detail: ChildDetail) -> str:
    """
    Embed a child detail in the vector store.

    Args:
        child_detail: Child detail to embed

    Returns:
        ID of the embedding in the vector store
    """
    # Format content for embedding
    content = f"Child Detail - Type: {child_detail.detail_type}\n"
    content += f"Content: {child_detail.content}\n"
    if child_detail.tags:
        content += f"Tags: {', '.join(child_detail.tags)}\n"

    # Create document
    doc = Document(
        page_content=content,
        metadata={
            "source": "child_detail",
            "child_detail_id": str(child_detail.id),
            "child_id": str(child_detail.child_id),
            "detail_type": child_detail.detail_type,
            "tags": child_detail.tags,
            "importance": child_detail.importance,
            "recorded_at": child_detail.recorded_at.isoformat() if child_detail.recorded_at else None,
        }
    )

    # Add to vector store
    ids = vectorstore.add_documents([doc])

    return ids[0] if ids else None


def update_child_detail_embedding(
    db: Session,
    child_detail: ChildDetail
) -> bool:
    """
    Update a child detail embedding in the vector store.

    Args:
        db: Database session
        child_detail: Child detail to update

    Returns:
        True if successful
    """
    # Delete old embedding if exists
    if child_detail.embedding_id:
        vectorstore.delete([child_detail.embedding_id])

    # Create new embedding
    embedding_id = embed_child_detail(child_detail)

    # Update embedding_id
    child_detail.embedding_id = embedding_id
    db.add(child_detail)
    db.commit()
    db.refresh(child_detail)

    return True


def delete_child_detail_embedding(child_detail: ChildDetail) -> bool:
    """
    Delete a child detail embedding from the vector store.

    Args:
        child_detail: Child detail to delete

    Returns:
        True if successful
    """
    if child_detail.embedding_id:
        vectorstore.delete([child_detail.embedding_id])
        return True
    return False


def get_child_details_for_rag(
    db: Session,
    child_id: uuid.UUID,
    query: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get child details for RAG based on relevance to query.

    Args:
        db: Database session
        child_id: Child ID
        query: Query to match against
        limit: Maximum number of details to return

    Returns:
        List of child details as dictionaries
    """
    # Search vector store for relevant child details
    search_filter = {"child_id": str(child_id), "source": "child_detail"}

    try:
        # 使用新的 API 方法
        results = vectorstore.similarity_search_with_relevance_scores(
            query,
            k=limit,
            filter=search_filter
        )

        # 格式化结果
        child_details = []
        for doc, score in results:
            child_details.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": score
            })

        return child_details

    except Exception as e:
        print(f"Error searching vector store: {e}")
        # 如果搜索失败，返回空列表
        return []



def get_all_child_details(
    db: Session,
    child_id: uuid.UUID,
    detail_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 100
) -> List[ChildDetail]:
    """
    Get all child details for a child.

    Args:
        db: Database session
        child_id: Child ID
        detail_type: Optional filter by detail type
        tags: Optional filter by tags
        limit: Maximum number of details to return

    Returns:
        List of child details
    """
    # Build query
    query = select(ChildDetail).where(ChildDetail.child_id == child_id)

    # Filter by detail_type if provided
    if detail_type:
        query = query.where(ChildDetail.detail_type == detail_type)

    # Add ordering and limit
    query = query.order_by(ChildDetail.recorded_at.desc()).limit(limit)

    # Execute query
    child_details = db.exec(query).all()

    # Filter by tags if provided
    if tags and child_details:
        filtered_details = []
        for detail in child_details:
            if any(tag in detail.tags for tag in tags):
                filtered_details.append(detail)
        return filtered_details

    return child_details


def get_child_info_with_details(
    db: Session,
    child_id: uuid.UUID,
    query: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get child information with relevant details.

    Args:
        db: Database session
        child_id: Child ID
        query: Optional query to match details against

    Returns:
        Dictionary with child information and details
    """
    # Get child
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

    # Add relevant details if query provided
    if query:
        child_info["relevant_details"] = get_child_details_for_rag(db, child_id, query)

    return child_info
