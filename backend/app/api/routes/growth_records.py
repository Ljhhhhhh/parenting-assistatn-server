"""
API routes for growth record management.
"""
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import get_current_active_user, get_db
from app.models import (
    User, Child, GrowthRecord, GrowthRecordCreate, GrowthRecordUpdate, 
    GrowthRecordPublic, GrowthRecordsPublic
)

router = APIRouter()


@router.post("/", response_model=GrowthRecordPublic, status_code=201)
def create_growth_record(
    *,
    db: Session = Depends(get_db),
    growth_record_in: GrowthRecordCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Create a new growth record.
    """
    # Check if child exists and belongs to current user
    child = db.get(Child, growth_record_in.child_id)
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    growth_record = GrowthRecord(**growth_record_in.model_dump())
    db.add(growth_record)
    db.commit()
    db.refresh(growth_record)
    return growth_record


@router.get("/", response_model=GrowthRecordsPublic)
def read_growth_records(
    *,
    db: Session = Depends(get_db),
    child_id: uuid.UUID,
    record_type: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve growth records.
    """
    # Check if child exists and belongs to current user
    child = db.get(Child, child_id)
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Build query
    query = select(GrowthRecord).where(GrowthRecord.child_id == child_id)
    
    # Filter by record type if provided
    if record_type:
        query = query.where(GrowthRecord.record_type == record_type)
    
    # Add pagination
    query = query.order_by(GrowthRecord.recorded_at.desc()).offset(skip).limit(limit)
    
    # Execute query
    growth_records = db.exec(query).all()
    
    # Count total
    count_query = select(GrowthRecord).where(GrowthRecord.child_id == child_id)
    if record_type:
        count_query = count_query.where(GrowthRecord.record_type == record_type)
    total_count = len(db.exec(count_query).all())
    
    return GrowthRecordsPublic(data=growth_records, count=total_count)


@router.get("/{record_id}", response_model=GrowthRecordPublic)
def read_growth_record(
    *,
    db: Session = Depends(get_db),
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get growth record by ID.
    """
    growth_record = db.get(GrowthRecord, record_id)
    if not growth_record:
        raise HTTPException(status_code=404, detail="Growth record not found")
    
    # Check if child belongs to current user
    child = db.get(Child, growth_record.child_id)
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return growth_record


@router.put("/{record_id}", response_model=GrowthRecordPublic)
def update_growth_record(
    *,
    db: Session = Depends(get_db),
    record_id: uuid.UUID,
    growth_record_in: GrowthRecordUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update a growth record.
    """
    growth_record = db.get(GrowthRecord, record_id)
    if not growth_record:
        raise HTTPException(status_code=404, detail="Growth record not found")
    
    # Check if child belongs to current user
    child = db.get(Child, growth_record.child_id)
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Update growth record attributes
    growth_record_data = growth_record_in.model_dump(exclude_unset=True)
    for key, value in growth_record_data.items():
        setattr(growth_record, key, value)
    
    db.add(growth_record)
    db.commit()
    db.refresh(growth_record)
    return growth_record


@router.delete("/{record_id}", response_model=GrowthRecordPublic)
def delete_growth_record(
    *,
    db: Session = Depends(get_db),
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Delete a growth record.
    """
    growth_record = db.get(GrowthRecord, record_id)
    if not growth_record:
        raise HTTPException(status_code=404, detail="Growth record not found")
    
    # Check if child belongs to current user
    child = db.get(Child, growth_record.child_id)
    if child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db.delete(growth_record)
    db.commit()
    return growth_record
