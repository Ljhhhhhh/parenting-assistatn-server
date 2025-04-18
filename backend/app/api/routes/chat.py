"""
API routes for chat functionality.
"""
from typing import Any, List, Dict
import uuid
import httpx
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from pydantic import BaseModel

from app.api.deps import get_current_active_user, get_db
from app.models import (
    User, Child, ChatRequest, ChatResponse, ChatHistory, ChatHistoriesPublic
)
from app.rag.vectorstore import get_retriever
from app.rag.chat_history import save_chat_interaction, get_chat_history, get_child_info
from app.rag.rag_chain import (
    get_openrouter_chat_model,
    create_history_aware_retriever,
    create_stuff_documents_chain,
    contextualize_q_prompt,
    qa_prompt
)
from app.core.config import settings


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: str = ""


class ModelsResponse(BaseModel):
    models: List[ModelInfo]

router = APIRouter()


@router.post("/", response_model=None)
async def chat(
    *,
    db: Session = Depends(get_db),
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """
    Chat with the AI assistant (Streaming).
    """
    session_id = chat_request.session_id or str(uuid.uuid4())

    async def stream_generator():
        full_answer = ""
        sources = []
        retrieved_docs = []

        try:
            # 1. Initial Setup (Child Info, History)
            child_info = None
            if chat_request.child_id:
                child = db.get(Child, chat_request.child_id)
                if not child or child.parent_id != current_user.id:
                    # Yield an error event for the client to handle
                    yield f"event: error\ndata: {json.dumps({'detail': 'Child not found or not permitted'})}\n\n"
                    return # Stop generation
                # Pass the user's question to get relevant child details
                child_info = get_child_info(db, chat_request.child_id, query=chat_request.question)
                print(f"Child Info: {child_info}")


            chat_history = get_chat_history(db, session_id)

            # 2. Instantiate RAG Components
            # Ensure LLM supports streaming (LangChain's ChatOpenAI/OpenRouter usually do)
            actual_model_name = chat_request.model or settings.DEFAULT_LLM_MODEL
            
            # Enhanced debugging for API key
            if settings.OPENROUTER_API_KEY:
                masked_key = f"...{settings.OPENROUTER_API_KEY[-5:]}" if len(settings.OPENROUTER_API_KEY) > 5 else "[INVALID KEY]"
                print(f"--- Using API Key (last 5 chars): {masked_key}")
            else:
                print("--- WARNING: No OpenRouter API key found!")
                
            print(f"--- Using Model: {actual_model_name}")
            print(f"--- OpenRouter Base URL: {settings.OPENROUTER_BASE_URL}")

            try:
                llm = get_openrouter_chat_model(
                    model=actual_model_name, # 使用已确定的模型名称
                    temperature=0.7,
                    streaming=True # Explicitly enable streaming if the function supports it
                )
            except Exception as e:
                error_msg = f"Failed to initialize LLM: {str(e)}"
                print(error_msg)
                yield f"event: error\ndata: {json.dumps({'detail': error_msg})}\n\n"
                return
            retriever = get_retriever(search_kwargs={"k": 3}) # Make sure get_retriever is accessible

            # 为什么宝宝的信息没有被加载成功 child_info
            history_aware_retriever = create_history_aware_retriever(
                llm, retriever, contextualize_q_prompt
            )
            question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

            # 3. Retrieve Documents and Send Sources
            retriever_input = {
                "input": chat_request.question,
                "chat_history": chat_history
            }
            # Use ainvoke for async operation
            # NOTE: The structure of Langchain chains evolves. Depending on the version,
            # `history_aware_retriever.ainvoke` might return a rephrased question or docs.
            # Let's assume it returns docs for now. If it returns a question, we'd need:
            # rephrased_q = await history_aware_retriever.ainvoke(retriever_input)
            # retrieved_docs = await retriever.ainvoke(rephrased_q['input']) # Or similar structure
            retrieved_docs = await history_aware_retriever.ainvoke(retriever_input)

            # Format sources from documents
            sources = []
            for doc in retrieved_docs:
                 if hasattr(doc, 'metadata'):
                     # Ensure metadata is serializable
                     serializable_metadata = {k: str(v) for k, v in doc.metadata.items()}
                     sources.append(serializable_metadata)

            yield f"{json.dumps({'sources': sources})}\n\n"

            # 4. Stream Answer
            qa_input = {
                "input": chat_request.question,
                "context": retrieved_docs,
                "chat_history": chat_history, # Include history if qa_prompt uses it
                "child_info": str(child_info) if child_info else "No specific child information provided." # Add child_info
            }

            # Construct a chain without the default StrOutputParser for true streaming
            # The original `question_answer_chain` (from create_stuff_documents_chain) implicitly adds StrOutputParser
            qa_chain_without_parser = qa_prompt | llm

            async for chunk in qa_chain_without_parser.astream(qa_input):
                # Adapt based on the actual structure of chunks from astream.
                # Common patterns:
                # - chunk directly is a string token
                # - chunk is AIMessageChunk(content='token')
                # - chunk is a dict {'answer': 'token'}
                token = "" # Default empty token
                # Expecting AIMessageChunk directly from the LLM now
                if hasattr(chunk, 'content'):
                    token = chunk.content

                if token:
                    full_answer += token
                    # Send token wrapped in JSON for easier frontend parsing
                    yield f"{json.dumps({'token': token})}\n\n"



        except Exception as e:
            import traceback
            error_type = type(e).__name__
            error_trace = traceback.format_exc()
            
            # Check for specific authentication errors
            if "AuthenticationError" in error_type or "401" in str(e):
                error_msg = "Authentication failed with OpenRouter. Please check your API key configuration."
                print(f"OpenRouter authentication error: {e}\n{error_trace}")
            else:
                error_msg = f"An error occurred: {str(e)}"
                print(f"Error during streaming: {e}\n{error_trace}") # Log the error server-side
            
            # Yield an error event to the client
            yield f"event: error\ndata: {json.dumps({'detail': error_msg, 'type': error_type})}\n\n"
            # Stop the generator by returning
            return
        finally:
            # 5. Save Interaction (always try to save if full_answer was populated)
            # This runs after the stream finishes or if an error occurred after some answer was generated
            if full_answer: # Only save if we got some answer
                 try:
                      save_chat_interaction(
                          db=db,
                          user_id=current_user.id,
                          session_id=session_id,
                          user_query=chat_request.question,
                          ai_response=full_answer, # Save the complete answer
                          model=chat_request.model or settings.DEFAULT_LLM_MODEL,
                          child_id=chat_request.child_id,
                          sources=sources # Save the retrieved sources
                      )
                 except Exception as db_error:
                      print(f"Error saving chat interaction: {db_error}") # Log DB save error

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


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
