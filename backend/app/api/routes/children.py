"""
API routes for child management.
"""
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import get_current_active_user, get_db
from app.models import (
    User, Child, ChildCreate, ChildUpdate, ChildPublic, ChildrenPublic
)

router = APIRouter()


@router.post("/", response_model=ChildPublic, status_code=201)
def create_child(
    *,
    db: Session = Depends(get_db),
    child_in: ChildCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Create a new child.
    """
    child = Child(
        **child_in.model_dump(),
        parent_id=current_user.id
    )
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@router.get("/", response_model=ChildrenPublic)
def read_children(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve children.
    """
    statement = (
        select(Child)
        .where(Child.parent_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    children = db.exec(statement).all()
    
    # Count total
    count_statement = select(Child).where(Child.parent_id == current_user.id)
    total_count = len(db.exec(count_statement).all())
    
    return ChildrenPublic(data=children, count=total_count)


@router.get("/{child_id}", response_model=ChildPublic)
def read_child(
    *,
    db: Session = Depends(get_db),
    child_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get child by ID.
    """
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return child


@router.put("/{child_id}", response_model=ChildPublic)
def update_child(
    *,
    db: Session = Depends(get_db),
    child_id: uuid.UUID,
    child_in: ChildUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update a child.
    """
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Update child attributes
    child_data = child_in.model_dump(exclude_unset=True)
    for key, value in child_data.items():
        setattr(child, key, value)
    
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@router.delete("/{child_id}", response_model=ChildPublic)
def delete_child(
    *,
    db: Session = Depends(get_db),
    child_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Delete a child.
    """
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db.delete(child)
    db.commit()
    return child
