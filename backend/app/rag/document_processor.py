"""
Document processing utilities for RAG system.
"""
import os
import shutil
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import UploadFile, HTTPException
from sqlmodel import Session

from app.models import Document, DocumentCreate
from app.rag.vectorstore import index_document, delete_document


# Define allowed file types
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.html'}

# Define upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename.

    Args:
        filename: Name of the file

    Returns:
        File extension with dot (e.g., '.pdf')
    """
    return os.path.splitext(filename)[1].lower()


def validate_file_type(filename: str) -> None:
    """
    Validate that the file type is supported.

    Args:
        filename: Name of the file

    Raises:
        HTTPException: If the file type is not supported
    """
    extension = get_file_extension(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )


async def process_document(
    file: UploadFile,
    db: Session,
    title: str,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Document:
    """
    Process and store a document.

    Args:
        file: Uploaded file
        db: Database session
        title: Document title
        description: Document description
        metadata: Additional metadata

    Returns:
        Document model instance
    """
    # Validate file type
    validate_file_type(file.filename)

    # Create a unique filename
    file_extension = get_file_extension(file.filename)
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Create document record
        document_data = DocumentCreate(
            title=title,
            description=description,
            file_type=file_extension[1:]  # Remove the dot
        )

        document = Document(
            **document_data.model_dump(),
            id=uuid.uuid4(),
            filename=unique_filename,
            upload_timestamp=datetime.utcnow(),
            doc_metadata=metadata or {}
        )

        # Add to database
        db.add(document)
        db.commit()
        db.refresh(document)

        # Index the document
        chunk_count = index_document(
            file_path=file_path,
            document_id=document.id,
            metadata={
                "title": title,
                "description": description,
                "file_type": file_extension[1:],
                "filename": file.filename
            }
        )

        # Update metadata with chunk count
        document.doc_metadata = document.doc_metadata or {}
        document.doc_metadata["chunk_count"] = chunk_count
        db.commit()
        db.refresh(document)

        return document

    except Exception as e:
        # Clean up in case of error
        if os.path.exists(file_path):
            os.remove(file_path)

        # If document was created, delete it
        if 'document' in locals() and document.id:
            db.delete(document)
            db.commit()

        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


async def delete_document_with_file(document_id: uuid.UUID, db: Session) -> bool:
    """
    Delete a document and its associated file.

    Args:
        document_id: UUID of the document to delete
        db: Database session

    Returns:
        True if successful
    """
    # Get the document
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from vector store
    vector_delete_success = delete_document(document_id)

    # Delete the file
    file_path = os.path.join(UPLOAD_DIR, document.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from database
    db.delete(document)
    db.commit()

    return vector_delete_success
