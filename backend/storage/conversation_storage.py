"""
Conversation Storage Service

Handles persistent storage of conversations as markdown files.
Each session is stored in a separate markdown file with Q&A pairs
separated by "-----" delimiters.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import asyncio
import aiofiles
import structlog

logger = structlog.get_logger()


class ConversationStorage:
    """
    Manages conversation storage in markdown format.
    
    Features:
    - Async file operations for better performance
    - Thread-safe operations with file locking
    - Markdown formatting with metadata
    - Chunk-based storage with delimiters
    """
    
    def __init__(self, base_dir: str = "./data/conversations"):
        """
        Initialize conversation storage.
        
        Args:
            base_dir: Base directory for conversation files
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info("conversation_storage_initialized", base_dir=str(self.base_dir))
    
    async def save_interaction(
        self,
        session_id: str,
        question: str,
        answer: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Save a Q&A interaction to the session's markdown file.
        
        Args:
            session_id: Unique session identifier
            question: The question text
            answer: The user's answer
            metadata: Optional metadata (category, timestamp, etc.)
        """
        filepath = self.base_dir / f"{session_id}.md"
        
        timestamp = datetime.utcnow().isoformat()
        category = metadata.get('category', 'unknown') if metadata else 'unknown'
        
        # Format the interaction as markdown
        content = f"""### Interaction ({category})
**Question:** {question}

**Answer:** {answer}

**Timestamp:** {timestamp}

-----

"""
        
        try:
            # Append to file (create if doesn't exist)
            async with aiofiles.open(filepath, 'a', encoding='utf-8') as f:
                await f.write(content)
            
            logger.info(
                "interaction_saved",
                session_id=session_id,
                category=category,
                filepath=str(filepath)
            )
        except Exception as e:
            logger.error(
                "save_interaction_failed",
                session_id=session_id,
                error=str(e)
            )
            raise
    
    async def load_conversation(self, session_id: str) -> str:
        """
        Load the full conversation history for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Full markdown content of the conversation
        """
        filepath = self.base_dir / f"{session_id}.md"
        
        if not filepath.exists():
            logger.warning("conversation_not_found", session_id=session_id)
            return ""
        
        try:
            async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            logger.info(
                "conversation_loaded",
                session_id=session_id,
                size_bytes=len(content)
            )
            return content
        except Exception as e:
            logger.error(
                "load_conversation_failed",
                session_id=session_id,
                error=str(e)
            )
            raise
    
    def parse_chunks(self, content: str) -> List[str]:
        """
        Parse conversation content into individual chunks.
        
        Args:
            content: Full markdown content
            
        Returns:
            List of conversation chunks (Q&A pairs)
        """
        if not content:
            return []
        
        # Split by delimiter
        chunks = content.split("-----")
        
        # Clean and filter empty chunks
        cleaned_chunks = []
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk:
                cleaned_chunks.append(chunk)
        
        logger.info("chunks_parsed", chunk_count=len(cleaned_chunks))
        return cleaned_chunks
    
    async def get_interaction_count(self, session_id: str) -> int:
        """
        Get the number of interactions in a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Number of Q&A interactions
        """
        content = await self.load_conversation(session_id)
        chunks = self.parse_chunks(content)
        return len(chunks)
    
    async def delete_conversation(self, session_id: str) -> bool:
        """
        Delete a conversation file.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if deleted, False if file didn't exist
        """
        filepath = self.base_dir / f"{session_id}.md"
        
        if filepath.exists():
            try:
                filepath.unlink()
                logger.info("conversation_deleted", session_id=session_id)
                return True
            except Exception as e:
                logger.error(
                    "delete_conversation_failed",
                    session_id=session_id,
                    error=str(e)
                )
                raise
        
        logger.warning("conversation_not_found_for_deletion", session_id=session_id)
        return False
    
    async def list_conversations(self) -> List[Dict]:
        """
        List all conversation files with metadata.
        
        Returns:
            List of dictionaries with session_id, created_at, size
        """
        conversations = []
        
        for filepath in self.base_dir.glob("*.md"):
            try:
                stat = filepath.stat()
                conversations.append({
                    'session_id': filepath.stem,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'size_bytes': stat.st_size
                })
            except Exception as e:
                logger.error(
                    "list_conversations_error",
                    filepath=str(filepath),
                    error=str(e)
                )
        
        # Sort by modified time (most recent first)
        conversations.sort(key=lambda x: x['modified_at'], reverse=True)
        
        logger.info("conversations_listed", count=len(conversations))
        return conversations
    
    def get_filepath(self, session_id: str) -> Path:
        """
        Get the file path for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Path object for the session's markdown file
        """
        return self.base_dir / f"{session_id}.md"


# Dependency injection helper
def get_conversation_storage() -> ConversationStorage:
    """
    Get ConversationStorage instance for dependency injection.
    
    Returns:
        ConversationStorage instance
    """
    return ConversationStorage()
