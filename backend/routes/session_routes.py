"""
Session API Routes for session management.

This module provides REST API endpoints for:
- Manual session saving
- Session loading/restoration
- Session listing with pagination
- Session deletion

SOLID Principles:
- Single Responsibility: Handles only session API endpoints
- Open/Closed: Extensible for new session operations
- Dependency Inversion: Depends on ConversationService abstraction
"""

from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import structlog

from services.conversation_service import get_conversation_service, ConversationService

logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/api/session", tags=["sessions"])


# Pydantic Models

class SaveSessionRequest(BaseModel):
    """Request model for saving a session."""
    session_id: str = Field(..., description="Session ID to save")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc-123-def-456"
            }
        }


class SaveSessionResponse(BaseModel):
    """Response model for save session endpoint."""
    success: bool = Field(..., description="Whether save was successful")
    session_id: str = Field(..., description="ID of saved session")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session_id": "abc-123-def-456",
                "message": "Session saved successfully"
            }
        }


class LoadSessionResponse(BaseModel):
    """Response model for load session endpoint."""
    success: bool = Field(..., description="Whether load was successful")
    session_id: str = Field(..., description="ID of loaded session")
    message_count: int = Field(..., description="Number of messages restored")
    state: str = Field(..., description="Current conversation state")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session_id": "abc-123-def-456",
                "message_count": 11,
                "state": "functionality",
                "message": "Session loaded successfully"
            }
        }


class SessionListItem(BaseModel):
    """Individual session in the list."""
    id: str
    started_at: str
    last_updated: str
    status: str
    state: str
    question_count: int
    message_count: int
    provider: Optional[str] = None
    model_id: Optional[str] = None


class ListSessionsResponse(BaseModel):
    """Response model for list sessions endpoint."""
    sessions: List[SessionListItem] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total number of sessions")
    limit: Optional[int] = Field(None, description="Limit applied")
    offset: int = Field(..., description="Offset applied")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sessions": [
                    {
                        "id": "abc-123",
                        "started_at": "2024-01-01T12:00:00Z",
                        "last_updated": "2024-01-01T12:30:00Z",
                        "status": "active",
                        "state": "functionality",
                        "question_count": 5,
                        "message_count": 11,
                        "provider": "groq",
                        "model_id": "llama2-70b-4096"
                    }
                ],
                "total": 1,
                "limit": 20,
                "offset": 0
            }
        }


class DeleteSessionResponse(BaseModel):
    """Response model for delete session endpoint."""
    success: bool = Field(..., description="Whether deletion was successful")
    session_id: str = Field(..., description="ID of deleted session")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session_id": "abc-123-def-456",
                "message": "Session deleted successfully"
            }
        }


# API Endpoints

@router.post("/save", response_model=SaveSessionResponse, status_code=status.HTTP_200_OK)
async def save_session(
    request: SaveSessionRequest,
    conversation: ConversationService = Depends(get_conversation_service)
) -> SaveSessionResponse:
    """
    Manually save a session.
    
    Saves the current session state and all conversation history to disk.
    This is useful when users want to explicitly save their work.
    
    Args:
        request: Session ID to save
        conversation: ConversationService dependency
        
    Returns:
        Save confirmation with session ID
        
    Raises:
        404: Session not found
        500: Save operation failed
        
    Example:
        POST /api/session/save
        {
            "session_id": "abc-123"
        }
        
        Response:
        {
            "success": true,
            "session_id": "abc-123",
            "message": "Session saved successfully"
        }
    """
    logger.info("api_save_session", session_id=request.session_id)
    
    try:
        # Validate session exists
        session = conversation.get_session(request.session_id)
        if not session:
            logger.warning("session_not_found_for_save", session_id=request.session_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {request.session_id}"
            )
        
        # Save session
        success = await conversation.manual_save_session(request.session_id)
        
        if not success:
            logger.error("manual_save_failed", session_id=request.session_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save session"
            )
        
        logger.info("session_saved_via_api", session_id=request.session_id)
        
        return SaveSessionResponse(
            success=True,
            session_id=request.session_id,
            message="Session saved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "save_session_error",
            session_id=request.session_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save session: {str(e)}"
        )


@router.get("/load/{session_id}", response_model=LoadSessionResponse, status_code=status.HTTP_200_OK)
async def load_session(
    session_id: str,
    conversation: ConversationService = Depends(get_conversation_service)
) -> LoadSessionResponse:
    """
    Load a previously saved session.
    
    Restores full conversation context including all messages and session state.
    The loaded session becomes active in the conversation service.
    
    Args:
        session_id: ID of session to load
        conversation: ConversationService dependency
        
    Returns:
        Load confirmation with session details
        
    Raises:
        404: Session not found
        500: Load operation failed
        
    Example:
        GET /api/session/load/abc-123
        
        Response:
        {
            "success": true,
            "session_id": "abc-123",
            "message_count": 11,
            "state": "functionality",
            "message": "Session loaded successfully"
        }
    """
    logger.info("api_load_session", session_id=session_id)
    
    try:
        # Load session
        success = await conversation.load_saved_session(session_id)
        
        if not success:
            logger.warning("session_not_found_for_load", session_id=session_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )
        
        # Get loaded session details
        session = conversation.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Session loaded but not accessible"
            )
        
        messages = conversation.get_conversation_history(session_id)
        
        logger.info(
            "session_loaded_via_api",
            session_id=session_id,
            message_count=len(messages),
            state=session.state.value
        )
        
        return LoadSessionResponse(
            success=True,
            session_id=session_id,
            message_count=len(messages),
            state=session.state.value,
            message="Session loaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "load_session_error",
            session_id=session_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load session: {str(e)}"
        )


@router.get("/list", response_model=ListSessionsResponse, status_code=status.HTTP_200_OK)
async def list_sessions(
    limit: Optional[int] = Query(None, ge=1, le=100, description="Maximum sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    conversation: ConversationService = Depends(get_conversation_service)
) -> ListSessionsResponse:
    """
    List all saved sessions.
    
    Returns a paginated list of session metadata sorted by last_updated (most recent first).
    Useful for showing users their previous investigations.
    
    Args:
        limit: Maximum number of sessions to return (1-100, default: all)
        offset: Number of sessions to skip for pagination (default: 0)
        conversation: ConversationService dependency
        
    Returns:
        List of sessions with metadata
        
    Raises:
        500: List operation failed
        
    Example:
        GET /api/session/list?limit=20&offset=0
        
        Response:
        {
            "sessions": [{...}],
            "total": 5,
            "limit": 20,
            "offset": 0
        }
    """
    logger.info("api_list_sessions", limit=limit, offset=offset)
    
    try:
        # Check if session service is available
        if not conversation.session_svc:
            logger.warning("session_service_not_available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session service not available"
            )
        
        # Get session list
        sessions = await conversation.session_svc.list_sessions(limit=limit, offset=offset)
        total = await conversation.session_svc.get_session_count()
        
        # Convert to response model
        session_items = [
            SessionListItem(**session)
            for session in sessions
        ]
        
        logger.info(
            "sessions_listed_via_api",
            count=len(sessions),
            total=total,
            limit=limit,
            offset=offset
        )
        
        return ListSessionsResponse(
            sessions=session_items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "list_sessions_error",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.delete("/{session_id}", response_model=DeleteSessionResponse, status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: str,
    conversation: ConversationService = Depends(get_conversation_service)
) -> DeleteSessionResponse:
    """
    Delete a saved session.
    
    Permanently removes the session file from storage.
    This action cannot be undone.
    
    Args:
        session_id: ID of session to delete
        conversation: ConversationService dependency
        
    Returns:
        Deletion confirmation
        
    Raises:
        404: Session not found
        500: Delete operation failed
        
    Example:
        DELETE /api/session/abc-123
        
        Response:
        {
            "success": true,
            "session_id": "abc-123",
            "message": "Session deleted successfully"
        }
    """
    logger.info("api_delete_session", session_id=session_id)
    
    try:
        # Check if session service is available
        if not conversation.session_svc:
            logger.warning("session_service_not_available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session service not available"
            )
        
        # Delete session
        success = await conversation.session_svc.delete_session(session_id)
        
        if not success:
            logger.warning("session_not_found_for_delete", session_id=session_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}"
            )
        
        # Remove from active sessions if present
        if session_id in conversation.sessions:
            del conversation.sessions[session_id]
        if session_id in conversation.messages:
            del conversation.messages[session_id]
        if session_id in conversation.last_save_counts:
            del conversation.last_save_counts[session_id]
        
        logger.info("session_deleted_via_api", session_id=session_id)
        
        return DeleteSessionResponse(
            success=True,
            session_id=session_id,
            message="Session deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "delete_session_error",
            session_id=session_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )


__all__ = ['router']
