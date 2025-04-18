"""
API routes for child detail management.
"""
from typing import Any, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import get_current_active_user, get_db
from app.models import (
    User, Child, ChildDetail, ChildDetailCreate, ChildDetailUpdate,
    ChildDetailPublic, ChildDetailsPublic
)
from app.rag.child_details import (
    save_child_detail, update_child_detail_embedding,
    delete_child_detail_embedding, get_all_child_details
)

router = APIRouter()


@router.post("/", response_model=ChildDetailPublic, status_code=201)
def create_child_detail(
    *,
    db: Session = Depends(get_db),
    child_detail_in: ChildDetailCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Create a new child detail.
    """
    # Check if child exists and belongs to current user
    child = db.get(Child, child_detail_in.child_id)
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Save child detail
    child_detail = save_child_detail(db, child_detail_in)

    return child_detail


@router.get("/", response_model=ChildDetailsPublic)
def read_child_details(
    *,
    db: Session = Depends(get_db),
    child_id: uuid.UUID,
    detail_type: str = None,
    tags: List[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve child details.
    """
    # Check if child exists and belongs to current user
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Build query
    query = select(ChildDetail).where(ChildDetail.child_id == child_id)

    # Filter by detail_type if provided
    if detail_type:
        query = query.where(ChildDetail.detail_type == detail_type)

    # Add pagination
    query = query.order_by(ChildDetail.recorded_at.desc()).offset(skip).limit(limit)

    # Execute query
    child_details = db.exec(query).all()

    # Filter by tags if provided
    if tags and child_details:
        filtered_details = []
        for detail in child_details:
            if any(tag in detail.tags for tag in tags):
                filtered_details.append(detail)
        child_details = filtered_details

    # Count total
    count_query = select(ChildDetail).where(ChildDetail.child_id == child_id)
    if detail_type:
        count_query = count_query.where(ChildDetail.detail_type == detail_type)
    total_count = len(db.exec(count_query).all())

    # If tags were used for filtering, adjust the count
    if tags:
        total_count = len(child_details)

    return ChildDetailsPublic(data=child_details, count=total_count)


@router.get("/{detail_id}", response_model=ChildDetailPublic)
def read_child_detail(
    *,
    db: Session = Depends(get_db),
    detail_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get child detail by ID.
    """
    child_detail = db.get(ChildDetail, detail_id)
    if not child_detail:
        raise HTTPException(status_code=404, detail="Child detail not found")

    # Check if child belongs to current user
    child = db.get(Child, child_detail.child_id)
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return child_detail


@router.put("/{detail_id}", response_model=ChildDetailPublic)
def update_child_detail(
    *,
    db: Session = Depends(get_db),
    detail_id: uuid.UUID,
    child_detail_in: ChildDetailUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update a child detail.
    """
    child_detail = db.get(ChildDetail, detail_id)
    if not child_detail:
        raise HTTPException(status_code=404, detail="Child detail not found")

    # Check if child belongs to current user
    child = db.get(Child, child_detail.child_id)
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Update child detail attributes
    child_detail_data = child_detail_in.model_dump(exclude_unset=True)
    for key, value in child_detail_data.items():
        setattr(child_detail, key, value)

    # Update timestamp
    from datetime import datetime
    child_detail.updated_at = datetime.utcnow()

    db.add(child_detail)
    db.commit()
    db.refresh(child_detail)

    # Update embedding
    update_child_detail_embedding(db, child_detail)

    return child_detail


@router.delete("/{detail_id}", response_model=ChildDetailPublic)
def delete_child_detail(
    *,
    db: Session = Depends(get_db),
    detail_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Delete a child detail.
    """
    child_detail = db.get(ChildDetail, detail_id)
    if not child_detail:
        raise HTTPException(status_code=404, detail="Child detail not found")

    # Check if child belongs to current user
    child = db.get(Child, child_detail.child_id)
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Delete embedding
    delete_child_detail_embedding(child_detail)

    # Delete from database
    db.delete(child_detail)
    db.commit()

    return child_detail


@router.post("/batch", response_model=ChildDetailsPublic)
def create_child_details_batch(
    *,
    db: Session = Depends(get_db),
    child_details_in: List[ChildDetailCreate],
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Create multiple child details in a batch.
    """
    if not child_details_in:
        raise HTTPException(status_code=400, detail="No child details provided")

    # Check if all child details belong to the same child
    child_id = child_details_in[0].child_id
    for detail in child_details_in:
        if detail.child_id != child_id:
            raise HTTPException(status_code=400, detail="All child details must belong to the same child")

    # Check if child exists and belongs to current user
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Save child details
    child_details = []
    for detail_in in child_details_in:
        child_detail = save_child_detail(db, detail_in)
        child_details.append(child_detail)

    return ChildDetailsPublic(data=child_details, count=len(child_details))
