"""
Session Service for managing conversation session persistence.

This service handles:
- Session serialization to JSON format
- Session deserialization with full context restoration
- Auto-save functionality (every N interactions)
- Session listing and metadata management
- Session deletion

SOLID Principles:
- Single Responsibility: Manages only session persistence
- Open/Closed: Extensible for different storage backends
- Dependency Inversion: Could abstract storage interface
"""

import json
import aiofiles
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import structlog

from models.conversation import (
    Session,
    Message,
    MessageRole,
    ConversationState
)

logger = structlog.get_logger()


class SessionService:
    """
    Service for managing session persistence and loading.
    
    Handles session serialization, auto-save, and session management
    operations with file-based JSON storage.
    """
    
    def __init__(self, base_dir: str = "./data/sessions"):
        """
        Initialize the session service.
        
        Args:
            base_dir: Directory path for storing session JSON files
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "session_service_initialized",
            base_dir=str(self.base_dir)
        )
    
    async def save_session(
        self,
        session: Session,
        messages: List[Message]
    ) -> bool:
        """
        Save session to JSON file.
        
        Serializes session metadata and full message history to a JSON file.
        Updates the session's last_updated timestamp automatically.
        
        Args:
            session: Session object to save
            messages: List of messages in the session
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            filepath = self.base_dir / f"{session.id}.json"
            
            # Update session timestamp
            session.last_updated = datetime.utcnow()
            
            # Count questions (messages with ASSISTANT/SYSTEM role)
            question_count = len([
                msg for msg in messages 
                if msg.role in (MessageRole.ASSISTANT, MessageRole.SYSTEM)
            ])
            
            # Build session data structure
            session_data = {
                'id': session.id,
                'started_at': session.started_at.isoformat(),
                'last_updated': session.last_updated.isoformat(),
                'status': session.status,
                'state': session.state.value,
                'investigation_progress': session.investigation_progress,
                'metadata': {
                    **session.metadata,
                    'question_count': question_count,
                    'message_count': len(messages),
                    'saved_at': datetime.utcnow().isoformat()
                },
                'provider': session.provider,
                'model_id': session.model_id,
                'skipped_questions': session.skipped_questions,
                'messages': [
                    {
                        'id': msg.id,
                        'session_id': msg.session_id,
                        'role': msg.role.value,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat(),
                        'metadata': msg.metadata
                    }
                    for msg in messages
                ]
            }
            
            # Write to file with pretty formatting
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(session_data, indent=2))
            
            logger.info(
                "session_saved",
                session_id=session.id,
                question_count=question_count,
                message_count=len(messages),
                filepath=str(filepath)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "session_save_failed",
                session_id=session.id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def load_session(
        self,
        session_id: str
    ) -> Optional[Tuple[Session, List[Message]]]:
        """
        Load session from JSON file.
        
        Deserializes session metadata and message history, fully restoring
        the conversation state.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Tuple of (Session, List[Message]) if found, None otherwise
        """
        try:
            filepath = self.base_dir / f"{session_id}.json"
            
            if not filepath.exists():
                logger.warning(
                    "session_not_found",
                    session_id=session_id,
                    filepath=str(filepath)
                )
                return None
            
            # Read session data
            async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                content = await f.read()
                session_data = json.loads(content)
            
            # Reconstruct Session object
            session = Session(
                id=session_data['id'],
                started_at=datetime.fromisoformat(session_data['started_at']),
                last_updated=datetime.fromisoformat(session_data['last_updated']),
                status=session_data['status'],
                state=ConversationState(session_data['state']),
                investigation_progress=session_data.get('investigation_progress', {}),
                metadata=session_data.get('metadata', {}),
                provider=session_data.get('provider'),
                model_id=session_data.get('model_id'),
                skipped_questions=session_data.get('skipped_questions', [])
            )
            
            # Reconstruct Message objects
            messages = [
                Message(
                    id=msg_data['id'],
                    session_id=msg_data['session_id'],
                    role=MessageRole(msg_data['role']),
                    content=msg_data['content'],
                    timestamp=datetime.fromisoformat(msg_data['timestamp']),
                    metadata=msg_data.get('metadata', {})
                )
                for msg_data in session_data.get('messages', [])
            ]
            
            logger.info(
                "session_loaded",
                session_id=session_id,
                message_count=len(messages),
                state=session.state.value,
                status=session.status
            )
            
            return (session, messages)
            
        except Exception as e:
            logger.error(
                "session_load_failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    
    async def list_sessions(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        List all saved sessions with metadata.
        
        Returns session summaries sorted by last_updated (most recent first).
        Useful for session picker UI.
        
        Args:
            limit: Maximum number of sessions to return (None = all)
            offset: Number of sessions to skip (for pagination)
            
        Returns:
            List of session metadata dictionaries
        """
        try:
            sessions = []
            
            # Scan all JSON files in the sessions directory
            for filepath in self.base_dir.glob("*.json"):
                try:
                    async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        data = json.loads(content)
                    
                    # Extract summary metadata
                    sessions.append({
                        'id': data['id'],
                        'started_at': data['started_at'],
                        'last_updated': data['last_updated'],
                        'status': data['status'],
                        'state': data['state'],
                        'question_count': data.get('metadata', {}).get('question_count', 0),
                        'message_count': data.get('metadata', {}).get('message_count', 0),
                        'provider': data.get('provider'),
                        'model_id': data.get('model_id')
                    })
                    
                except Exception as e:
                    logger.warning(
                        "session_read_error",
                        filepath=str(filepath),
                        error=str(e)
                    )
                    continue
            
            # Sort by last_updated (most recent first)
            sessions.sort(
                key=lambda x: x['last_updated'],
                reverse=True
            )
            
            # Apply pagination
            if limit is not None:
                sessions = sessions[offset:offset + limit]
            elif offset > 0:
                sessions = sessions[offset:]
            
            logger.info(
                "sessions_listed",
                total_count=len(sessions),
                limit=limit,
                offset=offset
            )
            
            return sessions
            
        except Exception as e:
            logger.error(
                "session_list_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session file.
        
        Permanently removes the session JSON file from storage.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if deleted successfully, False if not found or error
        """
        try:
            filepath = self.base_dir / f"{session_id}.json"
            
            if not filepath.exists():
                logger.warning(
                    "session_delete_not_found",
                    session_id=session_id
                )
                return False
            
            # Delete the file
            filepath.unlink()
            
            logger.info(
                "session_deleted",
                session_id=session_id,
                filepath=str(filepath)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "session_delete_failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    def should_auto_save(
        self,
        current_interaction_count: int,
        last_save_count: int = 0,
        auto_save_interval: int = 5
    ) -> bool:
        """
        Determine if session should be auto-saved.
        
        Auto-save triggers every N interactions (default: 5).
        
        Args:
            current_interaction_count: Current number of Q&A interactions
            last_save_count: Interaction count at last save
            auto_save_interval: Number of interactions between auto-saves
            
        Returns:
            True if auto-save should trigger, False otherwise
        """
        if current_interaction_count == 0:
            return False
        
        # Check if we've crossed an auto-save boundary
        interactions_since_save = current_interaction_count - last_save_count
        should_save = interactions_since_save >= auto_save_interval
        
        if should_save:
            logger.info(
                "auto_save_triggered",
                current_count=current_interaction_count,
                last_save_count=last_save_count,
                interactions_since_save=interactions_since_save,
                interval=auto_save_interval
            )
        
        return should_save
    
    async def get_session_count(self) -> int:
        """
        Get total number of saved sessions.
        
        Returns:
            Count of session JSON files
        """
        try:
            count = len(list(self.base_dir.glob("*.json")))
            logger.info("session_count_retrieved", count=count)
            return count
        except Exception as e:
            logger.error(
                "session_count_failed",
                error=str(e)
            )
            return 0


__all__ = ['SessionService']
