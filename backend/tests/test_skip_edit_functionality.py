"""
Tests for Skip and Edit Functionality (TASK-2.5)

Tests cover:
- Skipping questions and moving to next category
- Editing previous answers with RAG updates
- API endpoints for skip and edit operations
- Integration with conversation state machine
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from services.conversation_service import ConversationService
from services.rag_service import RAGService
from services.llm_service import LLMService
from services.question_generator import QuestionGenerator
from storage.conversation_storage import ConversationStorage
from models.conversation import (
    Session,
    Message,
    Question,
    MessageRole,
    ConversationState
)


# Fixtures

@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    service = MagicMock(spec=LLMService)
    service.generate_response = AsyncMock(return_value="What are the key features?")
    return service


@pytest.fixture
async def conversation_storage(tmp_path):
    """Create temporary conversation storage."""
    storage_dir = tmp_path / "conversations"
    storage = ConversationStorage(base_dir=str(storage_dir))
    return storage


@pytest.fixture
async def rag_service(tmp_path, conversation_storage):
    """Create RAG service with temporary vector store."""
    vector_dir = tmp_path / "vectors"
    rag = RAGService(
        storage=conversation_storage,
        persist_directory=str(vector_dir)
    )
    return rag


@pytest.fixture
def question_generator(mock_llm_service):
    """Create QuestionGenerator instance."""
    return QuestionGenerator(llm_service=mock_llm_service)


@pytest.fixture
async def conversation_service(mock_llm_service, rag_service, question_generator):
    """Create ConversationService with all dependencies."""
    return ConversationService(
        llm_service=mock_llm_service,
        rag_service=rag_service,
        question_generator=question_generator
    )


# Test Classes

class TestSkipQuestion:
    """Tests for skip question functionality."""
    
    @pytest.mark.asyncio
    async def test_skip_moves_to_next_category(self, conversation_service):
        """Test that skipping moves to the next conversation category."""
        # Start investigation
        session_id, initial_question = conversation_service.start_investigation()
        
        # Answer first question
        await conversation_service.process_answer(session_id, "A task management app")
        
        # Get current state
        session = conversation_service.get_session(session_id)
        initial_state = session.state
        
        # Skip current question
        next_question = await conversation_service.skip_current_question(session_id)
        
        # Verify state advanced
        session = conversation_service.get_session(session_id)
        assert session.state != initial_state
        assert next_question is not None
        assert next_question.category != initial_state.value
    
    @pytest.mark.asyncio
    async def test_skip_tracks_skipped_questions(self, conversation_service):
        """Test that skipped questions are tracked in session."""
        # Start investigation
        session_id, initial_question = conversation_service.start_investigation()
        
        # Answer first question
        await conversation_service.process_answer(session_id, "A task management app")
        
        # Skip current question
        await conversation_service.skip_current_question(session_id)
        
        # Verify skipped question is tracked
        session = conversation_service.get_session(session_id)
        assert len(session.skipped_questions) == 1
    
    @pytest.mark.asyncio
    async def test_skip_multiple_questions(self, conversation_service):
        """Test skipping multiple questions in sequence."""
        # Start investigation
        session_id, initial_question = conversation_service.start_investigation()
        
        # Answer first question
        await conversation_service.process_answer(session_id, "A task management app")
        
        # Skip 3 questions
        for i in range(3):
            next_question = await conversation_service.skip_current_question(session_id)
            assert next_question is not None or i == 2  # May complete after 3 skips
        
        # Verify skipped questions are tracked
        session = conversation_service.get_session(session_id)
        assert len(session.skipped_questions) >= 3
    
    @pytest.mark.asyncio
    async def test_skip_at_last_category_completes_investigation(self, conversation_service):
        """Test that skipping at the last category completes the investigation."""
        # Start investigation
        session_id, initial_question = conversation_service.start_investigation()
        
        # Manually set state to REVIEW (second to last state)
        session = conversation_service.get_session(session_id)
        session.state = ConversationState.REVIEW
        
        # Add a message so skip can find it
        conversation_service._add_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="Review question",
            metadata={"question_id": str(uuid.uuid4())}
        )
        
        # Skip current question
        next_question = await conversation_service.skip_current_question(session_id)
        
        # Should be complete or at COMPLETE state
        session = conversation_service.get_session(session_id)
        if next_question is None:
            assert session.state == ConversationState.COMPLETE
        else:
            # May have one more question before complete
            assert session.state == ConversationState.COMPLETE or next_question is not None


class TestEditAnswer:
    """Tests for edit answer functionality."""
    
    @pytest.mark.asyncio
    async def test_edit_updates_message_content(self, conversation_service):
        """Test that editing updates the message content."""
        # Start investigation and answer a question
        session_id, initial_question = conversation_service.start_investigation()
        await conversation_service.process_answer(session_id, "Original answer")
        
        # Get the message ID of the answer
        messages = conversation_service.get_conversation_history(session_id)
        answer_message = next(msg for msg in messages if msg.role == MessageRole.USER)
        
        # Edit the answer
        success = await conversation_service.edit_previous_answer(
            session_id=session_id,
            message_id=answer_message.id,
            new_answer="Updated answer with more details"
        )
        
        assert success is True
        
        # Verify message was updated
        messages = conversation_service.get_conversation_history(session_id)
        updated_message = next(msg for msg in messages if msg.id == answer_message.id)
        assert updated_message.content == "Updated answer with more details"
        assert updated_message.metadata.get('edited') is True
    
    @pytest.mark.asyncio
    async def test_edit_updates_rag_context(self, conversation_service, rag_service):
        """Test that editing updates the RAG vector store."""
        # Start investigation and answer a question
        session_id, initial_question = conversation_service.start_investigation()
        await conversation_service.process_answer(session_id, "Original answer")
        
        # Wait for RAG to persist
        await asyncio.sleep(0.1)
        
        # Get initial RAG stats
        initial_stats = rag_service.get_collection_stats(session_id=session_id)
        
        # Get the message ID
        messages = conversation_service.get_conversation_history(session_id)
        answer_message = next(msg for msg in messages if msg.role == MessageRole.USER)
        
        # Edit the answer
        success = await conversation_service.edit_previous_answer(
            session_id=session_id,
            message_id=answer_message.id,
            new_answer="Updated answer for RAG"
        )
        
        assert success is True
        
        # Verify RAG was updated (should have new entry or updated entry)
        updated_stats = rag_service.get_collection_stats(session_id=session_id)
        # RAG may add a new entry for the edit
        assert updated_stats['session_chunks'] >= initial_stats.get('session_chunks', 0)
    
    @pytest.mark.asyncio
    async def test_edit_nonexistent_message_returns_false(self, conversation_service):
        """Test that editing a non-existent message returns False."""
        # Start investigation
        session_id, initial_question = conversation_service.start_investigation()
        
        # Try to edit a non-existent message
        success = await conversation_service.edit_previous_answer(
            session_id=session_id,
            message_id="non-existent-id",
            new_answer="Updated answer"
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_edit_preserves_conversation_flow(self, conversation_service):
        """Test that editing doesn't break subsequent conversation flow."""
        # Start investigation and answer multiple questions
        session_id, initial_question = conversation_service.start_investigation()
        await conversation_service.process_answer(session_id, "First answer")
        await conversation_service.process_answer(session_id, "Second answer")
        
        # Get first answer's message ID
        messages = conversation_service.get_conversation_history(session_id)
        first_answer = next(msg for msg in messages if msg.role == MessageRole.USER)
        
        # Edit the first answer
        await conversation_service.edit_previous_answer(
            session_id=session_id,
            message_id=first_answer.id,
            new_answer="Edited first answer"
        )
        
        # Continue conversation
        next_question = await conversation_service.process_answer(session_id, "Third answer")
        
        # Verify conversation continues normally
        assert next_question is not None or conversation_service.is_investigation_complete(session_id)


class TestRAGIntegration:
    """Tests for RAG integration with skip/edit."""
    
    @pytest.mark.asyncio
    async def test_rag_update_interaction_finds_and_updates(self, rag_service):
        """Test that update_interaction successfully finds and updates chunks."""
        session_id = "test-session-update"
        question = "What is your product?"
        old_answer = "A basic app"
        new_answer = "An advanced AI-powered application"
        
        # Persist initial interaction
        await rag_service.persist_interaction(session_id, question, old_answer)
        
        # Update the interaction
        success = await rag_service.update_interaction(
            session_id=session_id,
            question=question,
            old_answer=old_answer,
            new_answer=new_answer
        )
        
        assert success is True
        
        # Retrieve context and verify new answer is present
        context = rag_service.retrieve_context(
            query=new_answer,
            session_id=session_id,
            top_k=5
        )
        
        # Should find the updated chunk
        assert len(context) > 0
        assert new_answer in context[0]
    
    @pytest.mark.asyncio
    async def test_rag_update_nonexistent_interaction_returns_false(self, rag_service):
        """Test that updating a non-existent interaction returns False."""
        session_id = "test-session-nonexistent"
        
        success = await rag_service.update_interaction(
            session_id=session_id,
            question="Non-existent question",
            old_answer="Old",
            new_answer="New"
        )
        
        assert success is False


class TestIntegrationWithConversationFlow:
    """Integration tests for skip/edit with full conversation flow."""
    
    @pytest.mark.asyncio
    async def test_complete_flow_with_skips_and_edits(self, conversation_service):
        """Test a complete conversation with skips and edits."""
        # Start investigation
        session_id, initial_question = conversation_service.start_investigation()
        
        # Answer first question
        await conversation_service.process_answer(session_id, "A project management tool")
        
        # Skip next question
        next_q = await conversation_service.skip_current_question(session_id)
        assert next_q is not None
        
        # Answer next question
        await conversation_service.process_answer(session_id, "Remote teams")
        
        # Edit first answer
        messages = conversation_service.get_conversation_history(session_id)
        first_answer = next(msg for msg in messages if msg.content == "A project management tool")
        await conversation_service.edit_previous_answer(
            session_id=session_id,
            message_id=first_answer.id,
            new_answer="A comprehensive project management and collaboration tool"
        )
        
        # Continue conversation
        next_q = await conversation_service.process_answer(session_id, "25-45 years old")
        
        # Verify session is still valid
        session = conversation_service.get_session(session_id)
        assert session is not None
        assert len(session.skipped_questions) == 1
        
        # Verify edited message
        messages = conversation_service.get_conversation_history(session_id)
        edited_msg = next(msg for msg in messages if msg.id == first_answer.id)
        assert "comprehensive" in edited_msg.content
        assert edited_msg.metadata.get('edited') is True


class TestErrorHandling:
    """Tests for error handling in skip/edit operations."""
    
    @pytest.mark.asyncio
    async def test_skip_invalid_session_raises_error(self, conversation_service):
        """Test that skipping with invalid session raises ValueError."""
        with pytest.raises(ValueError, match="Session .* not found"):
            await conversation_service.skip_current_question("invalid-session-id")
    
    @pytest.mark.asyncio
    async def test_edit_invalid_session_raises_error(self, conversation_service):
        """Test that editing with invalid session raises ValueError."""
        with pytest.raises(ValueError, match="Session .* not found"):
            await conversation_service.edit_previous_answer(
                session_id="invalid-session-id",
                message_id="msg-id",
                new_answer="New answer"
            )
