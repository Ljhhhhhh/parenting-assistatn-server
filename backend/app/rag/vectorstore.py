"""
Vector store utilities for RAG system.
"""
import os
from typing import List, Dict, Any, Optional
import uuid

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredHTMLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
import httpx
import numpy as np

from app.core.config import settings

# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len
)


# Initialize embedding function (will use OpenAIEmbeddings)
embedding_function = OpenAIEmbeddings(
    openai_api_base=settings.SILICONFLOW_BASE_URL,
    openai_api_key=settings.SILICONFLOW_API_KEY,
    model="BAAI/bge-m3" # Specify the SiliconFlow model name
    # Note: You might need other parameters depending on your specific needs,
    # e.g., chunk_size if dealing with very large documents.
)


# Initialize Chroma vector store
CHROMA_PERSIST_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_db")
os.makedirs(CHROMA_PERSIST_DIRECTORY, exist_ok=True)

vectorstore = Chroma(
    persist_directory=CHROMA_PERSIST_DIRECTORY,
    embedding_function=embedding_function
)


def load_and_split_document(file_path: str) -> List[Document]:
    """
    Load and split a document into chunks.

    Args:
        file_path: Path to the document file

    Returns:
        List of document chunks
    """
    if file_path.endswith('.pdf'):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith('.docx'):
        loader = Docx2txtLoader(file_path)
    elif file_path.endswith('.html'):
        loader = UnstructuredHTMLLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")

    documents = loader.load()
    return text_splitter.split_documents(documents)


def index_document(file_path: str, document_id: uuid.UUID, metadata: Optional[Dict[str, Any]] = None) -> int:
    """
    Process and index a document to the vector store.

    Args:
        file_path: Path to the document file
        document_id: UUID of the document
        metadata: Additional metadata to store with the document

    Returns:
        Number of chunks indexed
    """
    try:
        # Load and split the document
        splits = load_and_split_document(file_path)

        # Add metadata to each split
        for split in splits:
            split.metadata['document_id'] = str(document_id)
            if metadata:
                split.metadata.update(metadata)

        # Add documents to the vector store
        vectorstore.add_documents(splits)

        return len(splits)
    except Exception as e:
        print(f"Error indexing document: {e}")
        raise


def delete_document(document_id: uuid.UUID) -> bool:
    """
    Delete a document from the vector store.

    Args:
        document_id: UUID of the document to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        # Delete documents with matching document_id
        vectorstore.delete(where={"document_id": str(document_id)})
        return True
    except Exception as e:
        print(f"Error deleting document {document_id}: {e}")
        return False


def get_retriever(search_kwargs: Optional[Dict[str, Any]] = None):
    """
    Get a retriever from the vector store.

    Args:
        search_kwargs: Search parameters for the retriever

    Returns:
        A retriever instance
    """
    if search_kwargs is None:
        search_kwargs = {"k": 3}

    return vectorstore.as_retriever(search_kwargs=search_kwargs)
