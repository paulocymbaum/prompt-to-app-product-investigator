"""
Chat API Routes for conversation management.

This module provides REST and WebSocket endpoints for:
- Starting new investigations
- Sending messages and getting responses
- Retrieving conversation history
- Streaming responses via WebSocket

SOLID Principles:
- Single Responsibility: Handles only chat-related API endpoints
- Dependency Inversion: Depends on ConversationService abstraction
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
import structlog

from models.conversation import Message, Question
from services.conversation_service import ConversationService, get_conversation_service

logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/api/chat", tags=["chat"])


# Request/Response Models

class StartInvestigationRequest(BaseModel):
    """Request model for starting an investigation"""
    provider: Optional[str] = Field(None, description="LLM provider (groq/openai)")
    model_id: Optional[str] = Field(None, description="Model identifier")


class StartInvestigationResponse(BaseModel):
    """Response model for starting an investigation"""
    session_id: str = Field(..., description="Unique session identifier")
    question: dict = Field(..., description="Initial question")
    message: str = Field(default="Investigation started successfully")


class MessageRequest(BaseModel):
    """Request model for sending a message"""
    session_id: str = Field(..., description="Session identifier")
    message: str = Field(..., min_length=1, description="User's message/answer")


class MessageResponse(BaseModel):
    """Response model for message submission"""
    question: Optional[dict] = Field(None, description="Next question, or null if complete")
    complete: bool = Field(default=False, description="Whether investigation is complete")
    message: str = Field(default="Message processed successfully")


class HistoryResponse(BaseModel):
    """Response model for conversation history"""
    session_id: str = Field(..., description="Session identifier")
    messages: List[dict] = Field(..., description="List of messages in chronological order")
    total_messages: int = Field(..., description="Total number of messages")


class SessionStatusResponse(BaseModel):
    """Response model for session status"""
    session_id: str = Field(..., description="Session identifier")
    exists: bool = Field(..., description="Whether session exists")
    complete: bool = Field(default=False, description="Whether investigation is complete")
    state: Optional[str] = Field(None, description="Current conversation state")
    message_count: int = Field(default=0, description="Number of messages in conversation")


class SkipQuestionRequest(BaseModel):
    """Request model for skipping a question"""
    session_id: str = Field(..., description="Session identifier")


class SkipQuestionResponse(BaseModel):
    """Response model for skipping a question"""
    question: Optional[dict] = Field(None, description="Next question, or null if complete")
    complete: bool = Field(default=False, description="Whether investigation is complete")
    message: str = Field(default="Question skipped successfully")


class EditAnswerRequest(BaseModel):
    """Request model for editing a previous answer"""
    session_id: str = Field(..., description="Session identifier")
    message_id: str = Field(..., description="Message ID of the answer to edit")
    new_answer: str = Field(..., min_length=1, description="New answer text")


class EditAnswerResponse(BaseModel):
    """Response model for editing an answer"""
    success: bool = Field(..., description="Whether edit was successful")
    message: str = Field(default="Answer edited successfully")


# API Endpoints

@router.post("/start", response_model=StartInvestigationResponse, status_code=status.HTTP_201_CREATED)
async def start_investigation(
    request: StartInvestigationRequest = StartInvestigationRequest(provider=None, model_id=None),
    conversation: ConversationService = Depends(get_conversation_service)
) -> StartInvestigationResponse:
    """
    Start a new product investigation session.
    
    Creates a new conversation session and returns the initial question
    about the product's functionality.
    
    Args:
        request: Optional provider and model configuration
        conversation: ConversationService dependency
        
    Returns:
        Session ID and initial question
        
    Example:
        POST /api/chat/start
        {
            "provider": "groq",
            "model_id": "llama2-70b-4096"
        }
    """
    logger.info(
        "api_start_investigation",
        provider=request.provider,
        model_id=request.model_id
    )
    
    try:
        session_id, initial_question = conversation.start_investigation(
            provider=request.provider,
            model_id=request.model_id
        )
        
        logger.info("investigation_started_via_api", session_id=session_id)
        
        return StartInvestigationResponse(
            session_id=session_id,
            question=initial_question.model_dump(mode='json'),
            message="Investigation started successfully"
        )
        
    except Exception as e:
        logger.error("start_investigation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start investigation: {str(e)}"
        )


@router.post("/message", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    conversation: ConversationService = Depends(get_conversation_service)
) -> MessageResponse:
    """
    Send a message and get the next question.
    
    Processes the user's answer and generates the next question based on
    the conversation state and context.
    
    Args:
        request: Session ID and user's message
        conversation: ConversationService dependency
        
    Returns:
        Next question or completion indicator
        
    Raises:
        404: Session not found
        500: Processing error
        
    Example:
        POST /api/chat/message
        {
            "session_id": "abc-123",
            "message": "A task management app for remote teams"
        }
    """
    logger.info(
        "api_send_message",
        session_id=request.session_id,
        message_length=len(request.message)
    )
    
    try:
        next_question = await conversation.process_answer(
            session_id=request.session_id,
            answer_text=request.message
        )
        
        if next_question is None:
            # Investigation complete
            logger.info("investigation_completed_via_api", session_id=request.session_id)
            return MessageResponse(
                question=None,
                complete=True,
                message="Investigation complete! All questions answered."
            )
        
        logger.info(
            "next_question_generated_via_api",
            session_id=request.session_id,
            question_id=next_question.id
        )
        
        return MessageResponse(
            question=next_question.model_dump(mode='json'),
            complete=False,
            message="Message processed successfully"
        )
        
    except ValueError as e:
        logger.warning("session_not_found", session_id=request.session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {request.session_id}"
        )
    except Exception as e:
        logger.error(
            "send_message_error",
            session_id=request.session_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(
    session_id: str,
    conversation: ConversationService = Depends(get_conversation_service)
) -> HistoryResponse:
    """
    Get the full conversation history for a session.
    
    Returns all messages in chronological order, including both user
    messages and system questions.
    
    Args:
        session_id: Session identifier
        conversation: ConversationService dependency
        
    Returns:
        List of all messages
        
    Raises:
        404: Session not found
        
    Example:
        GET /api/chat/history/abc-123
    """
    logger.info("api_get_history", session_id=session_id)
    
    try:
        messages = conversation.get_conversation_history(session_id)
        
        logger.info(
            "history_retrieved_via_api",
            session_id=session_id,
            message_count=len(messages)
        )
        
        return HistoryResponse(
            session_id=session_id,
            messages=[msg.model_dump(mode='json') for msg in messages],
            total_messages=len(messages)
        )
        
    except ValueError as e:
        logger.warning("session_not_found", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )
    except Exception as e:
        logger.error("get_history_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@router.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    conversation: ConversationService = Depends(get_conversation_service)
) -> SessionStatusResponse:
    """
    Get the status of a conversation session.
    
    Returns information about whether the session exists, is complete,
    and other metadata.
    
    Args:
        session_id: Session identifier
        conversation: ConversationService dependency
        
    Returns:
        Session status information
        
    Example:
        GET /api/chat/status/abc-123
    """
    logger.info("api_get_session_status", session_id=session_id)
    
    try:
        session = conversation.get_session(session_id)
        
        if session is None:
            return SessionStatusResponse(
                session_id=session_id,
                exists=False,
                complete=False,
                state=None,
                message_count=0
            )
        
        messages = conversation.get_conversation_history(session_id)
        is_complete = conversation.is_investigation_complete(session_id)
        
        return SessionStatusResponse(
            session_id=session_id,
            exists=True,
            complete=is_complete,
            state=session.state.value if session else None,
            message_count=len(messages)
        )
        
    except Exception as e:
        logger.error("get_session_status_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session status: {str(e)}"
        )


@router.post("/skip", response_model=SkipQuestionResponse)
async def skip_question(
    request: SkipQuestionRequest,
    conversation: ConversationService = Depends(get_conversation_service)
) -> SkipQuestionResponse:
    """
    Skip the current question and move to the next category.
    
    Marks the current question as skipped and generates a new question
    from the next conversation category.
    
    Args:
        request: Session ID
        conversation: ConversationService dependency
        
    Returns:
        Next question or completion indicator
        
    Raises:
        404: Session not found
        500: Processing error
        
    Example:
        POST /api/chat/skip
        {
            "session_id": "abc-123"
        }
    """
    logger.info("api_skip_question", session_id=request.session_id)
    
    try:
        next_question = await conversation.skip_current_question(request.session_id)
        
        if next_question is None:
            # Investigation complete
            logger.info("investigation_completed_after_skip", session_id=request.session_id)
            return SkipQuestionResponse(
                question=None,
                complete=True,
                message="All categories explored! Investigation complete."
            )
        
        logger.info(
            "question_skipped_via_api",
            session_id=request.session_id,
            next_question_id=next_question.id
        )
        
        return SkipQuestionResponse(
            question=next_question.model_dump(mode='json'),
            complete=False,
            message="Question skipped successfully"
        )
        
    except ValueError as e:
        logger.warning("session_not_found_skip", session_id=request.session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {request.session_id}"
        )
    except Exception as e:
        logger.error(
            "skip_question_error",
            session_id=request.session_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to skip question: {str(e)}"
        )


@router.put("/edit", response_model=EditAnswerResponse)
async def edit_answer(
    request: EditAnswerRequest,
    conversation: ConversationService = Depends(get_conversation_service)
) -> EditAnswerResponse:
    """
    Edit a previous answer and update RAG context.
    
    Updates the specified message with new answer text and syncs
    the change to the RAG vector store for improved context retrieval.
    
    Note: This updates the answer in place but does not regenerate
    subsequent questions in the conversation.
    
    Args:
        request: Session ID, message ID, and new answer text
        conversation: ConversationService dependency
        
    Returns:
        Success indicator
        
    Raises:
        404: Session or message not found
        500: Processing error
        
    Example:
        PUT /api/chat/edit
        {
            "session_id": "abc-123",
            "message_id": "msg-456",
            "new_answer": "Updated answer with more details"
        }
    """
    logger.info(
        "api_edit_answer",
        session_id=request.session_id,
        message_id=request.message_id,
        new_answer_length=len(request.new_answer)
    )
    
    try:
        success = await conversation.edit_previous_answer(
            session_id=request.session_id,
            message_id=request.message_id,
            new_answer=request.new_answer
        )
        
        if not success:
            logger.warning(
                "message_not_found_edit",
                session_id=request.session_id,
                message_id=request.message_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message not found: {request.message_id}"
            )
        
        logger.info(
            "answer_edited_via_api",
            session_id=request.session_id,
            message_id=request.message_id
        )
        
        return EditAnswerResponse(
            success=True,
            message="Answer edited successfully. RAG context updated."
        )
        
    except ValueError as e:
        logger.warning("session_not_found_edit", session_id=request.session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {request.session_id}"
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "edit_answer_error",
            session_id=request.session_id,
            message_id=request.message_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to edit answer: {str(e)}"
        )


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket endpoint for real-time streaming responses.
    
    Accepts a WebSocket connection and streams LLM responses in real-time
    as they are generated, providing a better user experience for long
    responses.
    
    Args:
        websocket: WebSocket connection
        session_id: Session identifier
        
    Protocol:
        Client sends: {"message": "user's answer"}
        Server streams: {"type": "chunk", "content": "..."}
        Server final: {"type": "complete", "question_id": "..."}
        
    Example:
        WS /api/chat/ws/abc-123
    """
    await websocket.accept()
    logger.info("websocket_connected", session_id=session_id)
    
    try:
        # Get conversation service
        # Note: Can't use Depends() in WebSocket, so create manually
        conversation = get_conversation_service()
        
        # Verify session exists
        session = conversation.get_session(session_id)
        if session is None:
            await websocket.send_json({
                "type": "error",
                "message": f"Session not found: {session_id}"
            })
            await websocket.close(code=1008)  # Policy violation
            return
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "WebSocket connected successfully"
        })
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            
            if "message" not in data:
                await websocket.send_json({
                    "type": "error",
                    "message": "Missing 'message' field in request"
                })
                continue
            
            user_message = data["message"]
            
            logger.info(
                "websocket_message_received",
                session_id=session_id,
                message_length=len(user_message)
            )
            
            # Process the answer
            try:
                next_question = await conversation.process_answer(
                    session_id=session_id,
                    answer_text=user_message
                )
                
                if next_question is None:
                    # Investigation complete
                    await websocket.send_json({
                        "type": "complete",
                        "message": "Investigation complete!"
                    })
                else:
                    # Send next question
                    await websocket.send_json({
                        "type": "question",
                        "question": next_question.model_dump(mode='json')
                    })
                    
            except ValueError as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
            except Exception as e:
                logger.error(
                    "websocket_processing_error",
                    session_id=session_id,
                    error=str(e)
                )
                await websocket.send_json({
                    "type": "error",
                    "message": f"Processing error: {str(e)}"
                })
                
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", session_id=session_id)
    except Exception as e:
        logger.error("websocket_error", session_id=session_id, error=str(e))
        try:
            await websocket.close(code=1011)  # Internal error
        except:
            pass
