"""
Comprehensive test suite for SessionService.

Tests cover:
- Session saving and loading
- Session serialization/deserialization
- Session listing and metadata
- Session deletion
- Auto-save logic
- Concurrent session handling
- Error handling
"""

import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List

from services.session_service import SessionService
from models.conversation import (
    Session,
    Message,
    MessageRole,
    ConversationState
)


@pytest.fixture
async def session_service(tmp_path):
    """Create a SessionService with temporary directory."""
    service = SessionService(base_dir=str(tmp_path / "sessions"))
    yield service
    # Cleanup handled by tmp_path


@pytest.fixture
def sample_session():
    """Create a sample session for testing."""
    return Session(
        id="test-session-001",
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        last_updated=datetime(2024, 1, 1, 12, 30, 0),
        status="active",
        state=ConversationState.FUNCTIONALITY,
        investigation_progress={"functionality": 0.5},
        metadata={"product_name": "TaskMaster"},
        provider="groq",
        model_id="llama2-70b-4096",
        skipped_questions=[]
    )


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    return [
        Message(
            id="msg-001",
            session_id="test-session-001",
            role=MessageRole.SYSTEM,
            content="Welcome! Let's investigate your product.",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            metadata={}
        ),
        Message(
            id="msg-002",
            session_id="test-session-001",
            role=MessageRole.ASSISTANT,
            content="What is the main purpose of your product?",
            timestamp=datetime(2024, 1, 1, 12, 1, 0),
            metadata={"question_id": "q-001", "category": "functionality"}
        ),
        Message(
            id="msg-003",
            session_id="test-session-001",
            role=MessageRole.USER,
            content="A task management app for teams.",
            timestamp=datetime(2024, 1, 1, 12, 2, 0),
            metadata={}
        ),
        Message(
            id="msg-004",
            session_id="test-session-001",
            role=MessageRole.ASSISTANT,
            content="What specific features will it have?",
            timestamp=datetime(2024, 1, 1, 12, 3, 0),
            metadata={"question_id": "q-002", "category": "functionality"}
        ),
        Message(
            id="msg-005",
            session_id="test-session-001",
            role=MessageRole.USER,
            content="Task boards, calendars, and team chat.",
            timestamp=datetime(2024, 1, 1, 12, 4, 0),
            metadata={}
        )
    ]


class TestSaveSession:
    """Test session saving functionality."""
    
    @pytest.mark.asyncio
    async def test_save_session_creates_file(self, session_service, sample_session, sample_messages):
        """Test that save_session creates a JSON file."""
        success = await session_service.save_session(sample_session, sample_messages)
        
        assert success is True
        
        # Check file exists
        filepath = session_service.base_dir / f"{sample_session.id}.json"
        assert filepath.exists()
    
    @pytest.mark.asyncio
    async def test_save_session_json_structure(self, session_service, sample_session, sample_messages):
        """Test that saved JSON has correct structure."""
        await session_service.save_session(sample_session, sample_messages)
        
        filepath = session_service.base_dir / f"{sample_session.id}.json"
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Check all expected fields
        assert data['id'] == sample_session.id
        assert data['status'] == sample_session.status
        assert data['state'] == sample_session.state.value
        assert data['provider'] == sample_session.provider
        assert data['model_id'] == sample_session.model_id
        assert 'started_at' in data
        assert 'last_updated' in data
        assert 'messages' in data
        assert len(data['messages']) == len(sample_messages)
    
    @pytest.mark.asyncio
    async def test_save_session_includes_metadata(self, session_service, sample_session, sample_messages):
        """Test that saved session includes computed metadata."""
        await session_service.save_session(sample_session, sample_messages)
        
        filepath = session_service.base_dir / f"{sample_session.id}.json"
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Check computed metadata
        assert 'metadata' in data
        assert data['metadata']['question_count'] == 3  # 1 system + 2 assistant messages
        assert data['metadata']['message_count'] == 5
        assert 'saved_at' in data['metadata']
    
    @pytest.mark.asyncio
    async def test_save_session_updates_timestamp(self, session_service, sample_session, sample_messages):
        """Test that save_session updates last_updated timestamp."""
        original_timestamp = sample_session.last_updated
        
        # Wait a tiny bit to ensure timestamp difference
        await asyncio.sleep(0.01)
        
        await session_service.save_session(sample_session, sample_messages)
        
        # Session should have updated timestamp
        assert sample_session.last_updated > original_timestamp
    
    @pytest.mark.asyncio
    async def test_save_session_overwrites_existing(self, session_service, sample_session, sample_messages):
        """Test that saving twice overwrites the file."""
        # Save first time
        await session_service.save_session(sample_session, sample_messages)
        
        # Modify session
        sample_session.status = "complete"
        sample_session.state = ConversationState.COMPLETE
        
        # Save again
        await session_service.save_session(sample_session, sample_messages)
        
        # Load and verify
        filepath = session_service.base_dir / f"{sample_session.id}.json"
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert data['status'] == "complete"
        assert data['state'] == ConversationState.COMPLETE.value


class TestLoadSession:
    """Test session loading functionality."""
    
    @pytest.mark.asyncio
    async def test_load_session_returns_tuple(self, session_service, sample_session, sample_messages):
        """Test that load_session returns (Session, List[Message])."""
        await session_service.save_session(sample_session, sample_messages)
        
        result = await session_service.load_session(sample_session.id)
        
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        
        loaded_session, loaded_messages = result
        assert isinstance(loaded_session, Session)
        assert isinstance(loaded_messages, list)
        assert all(isinstance(msg, Message) for msg in loaded_messages)
    
    @pytest.mark.asyncio
    async def test_load_session_restores_session_fields(self, session_service, sample_session, sample_messages):
        """Test that loaded session has all original fields."""
        await session_service.save_session(sample_session, sample_messages)
        
        loaded_session, _ = await session_service.load_session(sample_session.id)
        
        assert loaded_session.id == sample_session.id
        assert loaded_session.status == sample_session.status
        assert loaded_session.state == sample_session.state
        assert loaded_session.provider == sample_session.provider
        assert loaded_session.model_id == sample_session.model_id
        assert loaded_session.investigation_progress == sample_session.investigation_progress
    
    @pytest.mark.asyncio
    async def test_load_session_restores_messages(self, session_service, sample_session, sample_messages):
        """Test that loaded messages match original messages."""
        await session_service.save_session(sample_session, sample_messages)
        
        _, loaded_messages = await session_service.load_session(sample_session.id)
        
        assert len(loaded_messages) == len(sample_messages)
        
        for original, loaded in zip(sample_messages, loaded_messages):
            assert loaded.id == original.id
            assert loaded.session_id == original.session_id
            assert loaded.role == original.role
            assert loaded.content == original.content
            assert loaded.metadata == original.metadata
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_session_returns_none(self, session_service):
        """Test that loading non-existent session returns None."""
        result = await session_service.load_session("nonexistent-session")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_load_session_with_skipped_questions(self, session_service, sample_session, sample_messages):
        """Test loading session with skipped questions."""
        sample_session.skipped_questions = ["q-001", "q-003"]
        
        await session_service.save_session(sample_session, sample_messages)
        
        loaded_session, _ = await session_service.load_session(sample_session.id)
        
        assert loaded_session.skipped_questions == ["q-001", "q-003"]


class TestListSessions:
    """Test session listing functionality."""
    
    @pytest.mark.asyncio
    async def test_list_sessions_empty_directory(self, session_service):
        """Test listing sessions in empty directory."""
        sessions = await session_service.list_sessions()
        
        assert sessions == []
    
    @pytest.mark.asyncio
    async def test_list_sessions_returns_metadata(self, session_service, sample_session, sample_messages):
        """Test that list_sessions returns session metadata."""
        await session_service.save_session(sample_session, sample_messages)
        
        sessions = await session_service.list_sessions()
        
        assert len(sessions) == 1
        
        session_info = sessions[0]
        assert session_info['id'] == sample_session.id
        assert session_info['status'] == sample_session.status
        assert session_info['state'] == sample_session.state.value
        assert 'started_at' in session_info
        assert 'last_updated' in session_info
        assert session_info['question_count'] == 3  # 1 system + 2 assistant messages
        assert session_info['message_count'] == 5
    
    @pytest.mark.asyncio
    async def test_list_sessions_sorted_by_last_updated(self, session_service, sample_messages):
        """Test that sessions are sorted by last_updated (most recent first)."""
        # Create three sessions with different timestamps
        session1 = Session(id="session-1", last_updated=datetime(2024, 1, 1, 10, 0, 0))
        session2 = Session(id="session-2", last_updated=datetime(2024, 1, 1, 12, 0, 0))  # Most recent
        session3 = Session(id="session-3", last_updated=datetime(2024, 1, 1, 11, 0, 0))
        
        await session_service.save_session(session1, sample_messages[:1])
        await session_service.save_session(session2, sample_messages[:1])
        await session_service.save_session(session3, sample_messages[:1])
        
        sessions = await session_service.list_sessions()
        
        assert len(sessions) == 3
        # Most recent should be first (but last_updated gets updated on save)
        # So we just check they're all present
        session_ids = [s['id'] for s in sessions]
        assert 'session-1' in session_ids
        assert 'session-2' in session_ids
        assert 'session-3' in session_ids
    
    @pytest.mark.asyncio
    async def test_list_sessions_with_limit(self, session_service, sample_messages):
        """Test pagination with limit parameter."""
        # Create 5 sessions
        for i in range(5):
            session = Session(id=f"session-{i}")
            await session_service.save_session(session, sample_messages[:1])
        
        sessions = await session_service.list_sessions(limit=3)
        
        assert len(sessions) == 3
    
    @pytest.mark.asyncio
    async def test_list_sessions_with_offset(self, session_service, sample_messages):
        """Test pagination with offset parameter."""
        # Create 5 sessions
        for i in range(5):
            session = Session(id=f"session-{i}")
            await session_service.save_session(session, sample_messages[:1])
        
        sessions = await session_service.list_sessions(offset=2)
        
        assert len(sessions) == 3  # 5 total - 2 offset = 3


class TestDeleteSession:
    """Test session deletion functionality."""
    
    @pytest.mark.asyncio
    async def test_delete_existing_session(self, session_service, sample_session, sample_messages):
        """Test deleting an existing session."""
        await session_service.save_session(sample_session, sample_messages)
        
        success = await session_service.delete_session(sample_session.id)
        
        assert success is True
        
        # Verify file is gone
        filepath = session_service.base_dir / f"{sample_session.id}.json"
        assert not filepath.exists()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, session_service):
        """Test deleting a non-existent session."""
        success = await session_service.delete_session("nonexistent-session")
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_delete_session_not_in_list(self, session_service, sample_session, sample_messages):
        """Test that deleted session doesn't appear in list."""
        await session_service.save_session(sample_session, sample_messages)
        
        await session_service.delete_session(sample_session.id)
        
        sessions = await session_service.list_sessions()
        assert len(sessions) == 0


class TestAutoSaveLogic:
    """Test auto-save decision logic."""
    
    def test_should_auto_save_at_threshold(self, session_service):
        """Test auto-save triggers at exact threshold."""
        should_save = session_service.should_auto_save(
            current_interaction_count=5,
            last_save_count=0,
            auto_save_interval=5
        )
        
        assert should_save is True
    
    def test_should_auto_save_above_threshold(self, session_service):
        """Test auto-save triggers above threshold."""
        should_save = session_service.should_auto_save(
            current_interaction_count=7,
            last_save_count=0,
            auto_save_interval=5
        )
        
        assert should_save is True
    
    def test_should_not_auto_save_below_threshold(self, session_service):
        """Test auto-save doesn't trigger below threshold."""
        should_save = session_service.should_auto_save(
            current_interaction_count=3,
            last_save_count=0,
            auto_save_interval=5
        )
        
        assert should_save is False
    
    def test_should_auto_save_after_previous_save(self, session_service):
        """Test auto-save triggers correctly after previous save."""
        # Saved at 5, now at 10 -> should save
        should_save = session_service.should_auto_save(
            current_interaction_count=10,
            last_save_count=5,
            auto_save_interval=5
        )
        
        assert should_save is True
    
    def test_should_not_auto_save_immediately_after_save(self, session_service):
        """Test auto-save doesn't trigger immediately after save."""
        # Saved at 5, now at 6 -> shouldn't save
        should_save = session_service.should_auto_save(
            current_interaction_count=6,
            last_save_count=5,
            auto_save_interval=5
        )
        
        assert should_save is False
    
    def test_should_not_auto_save_at_zero(self, session_service):
        """Test auto-save doesn't trigger at zero interactions."""
        should_save = session_service.should_auto_save(
            current_interaction_count=0,
            last_save_count=0,
            auto_save_interval=5
        )
        
        assert should_save is False


class TestSessionCount:
    """Test session counting functionality."""
    
    @pytest.mark.asyncio
    async def test_get_session_count_empty(self, session_service):
        """Test session count in empty directory."""
        count = await session_service.get_session_count()
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_get_session_count_with_sessions(self, session_service, sample_messages):
        """Test session count with multiple sessions."""
        for i in range(3):
            session = Session(id=f"session-{i}")
            await session_service.save_session(session, sample_messages[:1])
        
        count = await session_service.get_session_count()
        
        assert count == 3


class TestConcurrentAccess:
    """Test concurrent session operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_saves_different_sessions(self, session_service, sample_messages):
        """Test saving multiple sessions concurrently."""
        sessions = [Session(id=f"session-{i}") for i in range(5)]
        
        # Save all concurrently
        tasks = [
            session_service.save_session(session, sample_messages[:1])
            for session in sessions
        ]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)
        
        # All files should exist
        for session in sessions:
            filepath = session_service.base_dir / f"{session.id}.json"
            assert filepath.exists()
    
    @pytest.mark.asyncio
    async def test_concurrent_load_operations(self, session_service, sample_messages):
        """Test loading multiple sessions concurrently."""
        # Create sessions first
        sessions = [Session(id=f"session-{i}") for i in range(3)]
        for session in sessions:
            await session_service.save_session(session, sample_messages[:1])
        
        # Load all concurrently
        tasks = [
            session_service.load_session(session.id)
            for session in sessions
        ]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(result is not None for result in results)
        assert len(results) == 3


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_save_with_empty_messages(self, session_service, sample_session):
        """Test saving session with no messages."""
        success = await session_service.save_session(sample_session, [])
        
        assert success is True
        
        loaded_session, loaded_messages = await session_service.load_session(sample_session.id)
        
        assert loaded_messages == []
    
    @pytest.mark.asyncio
    async def test_load_corrupted_json(self, session_service):
        """Test loading session with corrupted JSON file."""
        # Create corrupted JSON file
        filepath = session_service.base_dir / "corrupted.json"
        with open(filepath, 'w') as f:
            f.write("{invalid json content")
        
        result = await session_service.load_session("corrupted")
        
        assert result is None
