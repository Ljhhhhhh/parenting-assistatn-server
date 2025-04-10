"""
API routes for document management.
"""
from typing import Any, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlmodel import Session, select

from app.api.deps import get_current_active_user, get_db
from app.models import (
    User, Document, DocumentUpdate, DocumentPublic, DocumentsPublic
)
from app.rag.document_processor import process_document, delete_document_with_file
from app.core.config import settings

router = APIRouter()


@router.post("/upload", response_model=DocumentPublic, status_code=201)
async def upload_document(
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(None),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Upload a new document.
    """
    # Check document count limit
    statement = select(Document)
    document_count = len(db.exec(statement).all())
    if document_count >= settings.MAX_DOCUMENTS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum number of documents ({settings.MAX_DOCUMENTS_PER_USER}) reached"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Go to the end of the file
    file_size = file.file.tell()  # Get the position (size)
    file.file.seek(0)  # Go back to the start
    
    max_size = settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024  # Convert MB to bytes
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.MAX_DOCUMENT_SIZE_MB}MB"
        )
    
    # Process document
    try:
        document = await process_document(
            file=file,
            db=db,
            title=title,
            description=description,
            metadata={"uploaded_by": str(current_user.id)}
        )
        return document
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=DocumentsPublic)
def read_documents(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve documents.
    """
    statement = (
        select(Document)
        .where(Document.status == "active")
        .order_by(Document.upload_timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    documents = db.exec(statement).all()
    
    # Count total
    count_statement = select(Document).where(Document.status == "active")
    total_count = len(db.exec(count_statement).all())
    
    return DocumentsPublic(data=documents, count=total_count)


@router.get("/{document_id}", response_model=DocumentPublic)
def read_document(
    *,
    db: Session = Depends(get_db),
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get document by ID.
    """
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "active":
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.put("/{document_id}", response_model=DocumentPublic)
def update_document(
    *,
    db: Session = Depends(get_db),
    document_id: uuid.UUID,
    document_in: DocumentUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update a document.
    """
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "active":
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update document attributes
    document_data = document_in.model_dump(exclude_unset=True)
    for key, value in document_data.items():
        setattr(document, key, value)
    
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.delete("/{document_id}", response_model=DocumentPublic)
async def delete_document(
    *,
    db: Session = Depends(get_db),
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Delete a document.
    """
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "active":
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete document
    await delete_document_with_file(document_id, db)
    
    return document
