"""
RAG chain implementation for the parenting assistant.
"""
from typing import List, Dict, Any, Optional
import uuid

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

from app.rag.vectorstore import get_retriever
from app.rag.openrouter_client import get_openrouter_chat_model
from app.core.config import settings


# Initialize output parser
output_parser = StrOutputParser()


# Context-aware question prompt
contextualize_q_system_prompt = """
Given the chat history and the latest user question, which may reference context from the chat history,
formulate a standalone question that can be understood without the chat history.
Do not answer the question, just reformulate it if needed, or return it as is.

If the question is about a child, make sure to include relevant details like age, gender, or specific concerns.
"""

contextualize_q_prompt = ChatPromptTemplate.from_messages([
    ("system", contextualize_q_system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])


# QA prompt
qa_system_prompt = """
You are an AI parenting assistant designed to provide helpful, accurate, and supportive advice to parents.
Use the following context to answer the user's question.

Context: {context}

Guidelines:
1. Base your answers on the provided context and scientific parenting knowledge.
2. If the context doesn't contain relevant information, say so and provide general advice based on child development principles.
3. Always be supportive and non-judgmental.
4. For medical questions, remind the user to consult healthcare professionals.
5. Provide age-appropriate advice when child information is available.
6. Keep answers concise but informative.

Remember that parenting is personal, and your advice should be adaptable to different parenting styles and cultural contexts.
"""

qa_prompt = ChatPromptTemplate.from_messages([
    ("system", qa_system_prompt),
    ("system", "Child Information: {child_info}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])


def get_rag_chain(model_name: str = None, child_info: Optional[Dict[str, Any]] = None):
    """
    Create a RAG chain for the parenting assistant.

    Args:
        model_name: Name of the model to use (e.g., "openai/gpt-4o-mini", "anthropic/claude-3-opus")
        child_info: Optional information about the child

    Returns:
        A RAG chain
    """
    # Initialize language model
    llm = get_openrouter_chat_model(
        model=model_name or settings.DEFAULT_LLM_MODEL,
        temperature=0.7
    )

    # Get retriever
    retriever = get_retriever(search_kwargs={"k": 3})

    # Create history-aware retriever
    history_aware_retriever = create_history_aware_retriever(
        llm,
        retriever,
        contextualize_q_prompt
    )

    # Create question-answering chain
    question_answer_chain = create_stuff_documents_chain(
        llm,
        qa_prompt
    )

    # Create retrieval chain
    rag_chain = create_retrieval_chain(
        history_aware_retriever,
        question_answer_chain
    )

    return rag_chain


async def generate_response(
    question: str,
    chat_history: List[Dict[str, str]],
    session_id: str,
    child_info: Optional[Dict[str, Any]] = None,
    model_name: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Generate a response using the RAG chain.

    Args:
        question: User's question
        chat_history: List of previous messages
        session_id: Session ID
        child_info: Optional information about the child
        model_name: Name of the OpenAI model to use

    Returns:
        Dictionary containing the answer and source documents
    """
    # Get RAG chain
    rag_chain = get_rag_chain(model_name, child_info)

    # Prepare input
    chain_input = {
        "input": question,
        "chat_history": chat_history
    }

    # Add child info if available
    if child_info:
        chain_input["child_info"] = str(child_info)
    else:
        chain_input["child_info"] = "No specific child information provided."

    # Invoke chain
    result = rag_chain.invoke(chain_input)

    # Extract answer and source documents
    answer = result.get("answer", "I couldn't generate an answer.")
    source_documents = result.get("source_documents", [])

    # Format source documents
    sources = []
    for doc in source_documents:
        if hasattr(doc, 'metadata'):
            sources.append(doc.metadata)

    return {
        "answer": answer,
        "session_id": session_id,
        "sources": sources
    }
