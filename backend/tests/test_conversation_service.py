"""
Unit tests for Conversation Service.

Tests cover:
- Session initialization
- State machine transitions
- Initial question generation
- Follow-up question generation
- Message history tracking
- Session isolation
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime

from services.conversation_service import ConversationService, get_conversation_service
from services.llm_service import LLMService
from models.conversation import (
    Session,
    Message,
    Question,
    MessageRole,
    ConversationState
)


@pytest.fixture
def mock_llm_service():
    """Create a mock LLMService"""
    mock = Mock(spec=LLMService)
    mock.generate_response = AsyncMock(
        return_value="Can you tell me more about the specific features your users will interact with?"
    )
    return mock


@pytest.fixture
def conversation_service(mock_llm_service):
    """Create ConversationService instance with mocked LLM"""
    return ConversationService(llm_service=mock_llm_service)


class TestConversationServiceInitialization:
    """Test suite for conversation service initialization"""
    
    def test_service_creation(self, conversation_service):
        """Test that ConversationService can be created"""
        assert conversation_service.sessions == {}
        assert conversation_service.messages == {}
        assert len(conversation_service.STATE_ORDER) == 9
        assert len(conversation_service.QUESTION_TEMPLATES) == 7
    
    def test_state_order_sequence(self, conversation_service):
        """Test that state order is correct"""
        expected_order = [
            ConversationState.START,
            ConversationState.FUNCTIONALITY,
            ConversationState.USERS,
            ConversationState.DEMOGRAPHICS,
            ConversationState.DESIGN,
            ConversationState.MARKET,
            ConversationState.TECHNICAL,
            ConversationState.REVIEW,
            ConversationState.COMPLETE
        ]
        assert conversation_service.STATE_ORDER == expected_order
    
    def test_question_templates_exist(self, conversation_service):
        """Test that question templates exist for all categories"""
        assert ConversationState.FUNCTIONALITY in conversation_service.QUESTION_TEMPLATES
        assert ConversationState.USERS in conversation_service.QUESTION_TEMPLATES
        assert ConversationState.DEMOGRAPHICS in conversation_service.QUESTION_TEMPLATES
        assert ConversationState.DESIGN in conversation_service.QUESTION_TEMPLATES
        assert ConversationState.MARKET in conversation_service.QUESTION_TEMPLATES
        assert ConversationState.TECHNICAL in conversation_service.QUESTION_TEMPLATES
        assert ConversationState.REVIEW in conversation_service.QUESTION_TEMPLATES


class TestStartInvestigation:
    """Test suite for starting investigations"""
    
    def test_start_investigation_creates_session(self, conversation_service):
        """Test that starting investigation creates a new session"""
        session_id, question = conversation_service.start_investigation()
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID4 length
        assert session_id in conversation_service.sessions
        assert session_id in conversation_service.messages
    
    def test_start_investigation_initial_question(self, conversation_service):
        """Test that initial question is about functionality"""
        session_id, question = conversation_service.start_investigation()
        
        assert question.category == ConversationState.FUNCTIONALITY.value
        assert question.is_followup is False
        assert "functionality" in question.text.lower() or "product" in question.text.lower()
        assert question.id is not None
    
    def test_start_investigation_session_state(self, conversation_service):
        """Test that session starts with correct state"""
        session_id, question = conversation_service.start_investigation()
        
        session = conversation_service.sessions[session_id]
        assert session.state == ConversationState.START
        assert session.status == "active"
        assert session.investigation_progress == {}
    
    def test_start_investigation_with_provider(self, conversation_service):
        """Test starting investigation with specific provider"""
        session_id, question = conversation_service.start_investigation(
            provider="groq",
            model_id="llama2-70b-4096"
        )
        
        session = conversation_service.sessions[session_id]
        assert session.provider == "groq"
        assert session.model_id == "llama2-70b-4096"
    
    def test_start_investigation_adds_system_message(self, conversation_service):
        """Test that initial question is added to message history"""
        session_id, question = conversation_service.start_investigation()
        
        messages = conversation_service.messages[session_id]
        assert len(messages) == 1
        assert messages[0].role == MessageRole.SYSTEM
        assert messages[0].content == question.text
        assert messages[0].metadata["question_id"] == question.id


class TestProcessAnswer:
    """Test suite for processing answers"""
    
    @pytest.mark.asyncio
    async def test_process_answer_adds_user_message(self, conversation_service):
        """Test that processing answer adds user message to history"""
        session_id, _ = conversation_service.start_investigation()
        
        answer = "A task management app for remote teams with real-time collaboration features."
        next_question = await conversation_service.process_answer(session_id, answer)
        
        messages = conversation_service.messages[session_id]
        user_messages = [m for m in messages if m.role == MessageRole.USER]
        assert len(user_messages) == 1
        assert user_messages[0].content == answer
    
    @pytest.mark.asyncio
    async def test_process_answer_generates_next_question(self, conversation_service):
        """Test that processing answer generates next question"""
        session_id, _ = conversation_service.start_investigation()
        
        answer = "A task management app for remote teams with real-time collaboration features."
        next_question = await conversation_service.process_answer(session_id, answer)
        
        assert next_question is not None
        assert next_question.text is not None
        assert next_question.id is not None
    
    @pytest.mark.asyncio
    async def test_process_answer_session_not_found(self, conversation_service):
        """Test error when session not found"""
        with pytest.raises(ValueError, match="Session .* not found"):
            await conversation_service.process_answer("invalid-session-id", "answer")
    
    @pytest.mark.asyncio
    async def test_process_answer_updates_session_timestamp(self, conversation_service):
        """Test that processing answer updates session timestamp"""
        session_id, _ = conversation_service.start_investigation()
        original_timestamp = conversation_service.sessions[session_id].last_updated
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        await conversation_service.process_answer(session_id, "A task management app")
        
        updated_timestamp = conversation_service.sessions[session_id].last_updated
        assert updated_timestamp > original_timestamp
    
    @pytest.mark.asyncio
    async def test_process_short_answer_triggers_followup(self, conversation_service, mock_llm_service):
        """Test that short answers trigger follow-up questions"""
        session_id, _ = conversation_service.start_investigation()
        
        # Short answer (< 15 words)
        short_answer = "Task management"
        next_question = await conversation_service.process_answer(session_id, short_answer)
        
        # Should call LLM for follow-up
        assert mock_llm_service.generate_response.called
        assert next_question.is_followup is True
        assert next_question.category == ConversationState.START.value
    
    @pytest.mark.asyncio
    async def test_process_long_answer_moves_to_next_state(self, conversation_service, mock_llm_service):
        """Test that long answers move to next state"""
        session_id, _ = conversation_service.start_investigation()
        
        # Long answer (>= 15 words)
        long_answer = "A comprehensive task management platform designed for remote teams with features including real-time collaboration, deadline tracking, and automated workflows."
        next_question = await conversation_service.process_answer(session_id, long_answer)
        
        # Should move to next state (FUNCTIONALITY)
        session = conversation_service.sessions[session_id]
        assert session.state == ConversationState.FUNCTIONALITY
        assert next_question.is_followup is False
        assert next_question.category == ConversationState.FUNCTIONALITY.value


class TestStateTransitions:
    """Test suite for state machine transitions"""
    
    @pytest.mark.asyncio
    async def test_state_transition_sequence(self, conversation_service):
        """Test full state transition sequence"""
        session_id, _ = conversation_service.start_investigation()
        
        # Provide long answers (>= 15 words) to move through states
        long_answer = "This is a comprehensive solution with multiple advanced features specifically designed for modern remote teams working on collaborative business projects together."
        
        states_visited = [ConversationState.START]
        
        for _ in range(8):  # Go through all states
            question = await conversation_service.process_answer(session_id, long_answer)
            if question is None:
                break
            session = conversation_service.sessions[session_id]
            states_visited.append(session.state)
        
        # Should have visited all states in order
        assert ConversationState.FUNCTIONALITY in states_visited
        assert ConversationState.USERS in states_visited
        assert ConversationState.DEMOGRAPHICS in states_visited
    
    @pytest.mark.asyncio
    async def test_investigation_completion(self, conversation_service):
        """Test that investigation completes after all states"""
        session_id, _ = conversation_service.start_investigation()
        
        # Long answer (>= 15 words) to progress through states
        long_answer = "This is a comprehensive solution with multiple advanced features specifically designed for modern remote teams working on collaborative business projects together."
        
        question = None
        for _ in range(10):  # More than enough iterations
            question = await conversation_service.process_answer(session_id, long_answer)
            if question is None:
                break
        
        # Should complete and return None
        assert question is None
        
        session = conversation_service.sessions[session_id]
        assert session.state == ConversationState.COMPLETE
        assert session.status == "complete"
    
    def test_get_next_state(self, conversation_service):
        """Test state transition logic"""
        next_state = conversation_service._get_next_state(ConversationState.START)
        assert next_state == ConversationState.FUNCTIONALITY
        
        next_state = conversation_service._get_next_state(ConversationState.FUNCTIONALITY)
        assert next_state == ConversationState.USERS
        
        next_state = conversation_service._get_next_state(ConversationState.REVIEW)
        assert next_state == ConversationState.COMPLETE


class TestQuestionGeneration:
    """Test suite for question generation"""
    
    def test_generate_initial_question(self, conversation_service):
        """Test initial question generation"""
        question = conversation_service._generate_initial_question()
        
        assert question.category == ConversationState.FUNCTIONALITY.value
        assert question.is_followup is False
        assert question.id is not None
        assert len(question.text) > 0
    
    def test_generate_category_question(self, conversation_service):
        """Test category-specific question generation"""
        question = conversation_service._generate_category_question(ConversationState.USERS)
        
        assert question.category == ConversationState.USERS.value
        assert question.is_followup is False
        assert question.id is not None
        assert len(question.text) > 0
    
    @pytest.mark.asyncio
    async def test_generate_followup_question(self, conversation_service, mock_llm_service):
        """Test follow-up question generation"""
        session_id, _ = conversation_service.start_investigation()
        session = conversation_service.sessions[session_id]
        
        question = await conversation_service._generate_followup_question(
            session=session,
            latest_answer="Task management"
        )
        
        assert question.is_followup is True
        assert question.category == session.state.value
        assert mock_llm_service.generate_response.called
    
    def test_needs_followup_logic(self, conversation_service):
        """Test follow-up determination logic"""
        # Short answer needs follow-up
        assert conversation_service._needs_followup("Task management") is True
        assert conversation_service._needs_followup("A simple app") is True
        
        # Long answer doesn't need follow-up
        long_answer = "A comprehensive task management platform with real-time collaboration, deadline tracking, and automated workflows for remote teams."
        assert conversation_service._needs_followup(long_answer) is False


class TestConversationHistory:
    """Test suite for conversation history"""
    
    @pytest.mark.asyncio
    async def test_get_conversation_history(self, conversation_service):
        """Test retrieving conversation history"""
        session_id, _ = conversation_service.start_investigation()
        
        await conversation_service.process_answer(session_id, "A task management app")
        
        history = conversation_service.get_conversation_history(session_id)
        
        assert len(history) >= 2  # At least system + user messages
        assert any(m.role == MessageRole.SYSTEM for m in history)
        assert any(m.role == MessageRole.USER for m in history)
    
    def test_get_conversation_history_not_found(self, conversation_service):
        """Test error when getting history for non-existent session"""
        with pytest.raises(ValueError, match="Session .* not found"):
            conversation_service.get_conversation_history("invalid-session-id")
    
    @pytest.mark.asyncio
    async def test_message_ordering(self, conversation_service):
        """Test that messages are in chronological order"""
        session_id, _ = conversation_service.start_investigation()
        
        await conversation_service.process_answer(session_id, "First answer")
        await conversation_service.process_answer(session_id, "Second answer")
        
        history = conversation_service.get_conversation_history(session_id)
        
        # Check timestamps are in order
        for i in range(len(history) - 1):
            assert history[i].timestamp <= history[i + 1].timestamp


class TestSessionManagement:
    """Test suite for session management"""
    
    def test_get_session(self, conversation_service):
        """Test getting session metadata"""
        session_id, _ = conversation_service.start_investigation()
        
        session = conversation_service.get_session(session_id)
        
        assert session is not None
        assert session.id == session_id
        assert session.status == "active"
    
    def test_get_session_not_found(self, conversation_service):
        """Test getting non-existent session returns None"""
        session = conversation_service.get_session("invalid-session-id")
        assert session is None
    
    def test_is_investigation_complete(self, conversation_service):
        """Test checking if investigation is complete"""
        session_id, _ = conversation_service.start_investigation()
        
        # Not complete initially
        assert conversation_service.is_investigation_complete(session_id) is False
        
        # Set to complete
        conversation_service.sessions[session_id].state = ConversationState.COMPLETE
        assert conversation_service.is_investigation_complete(session_id) is True
    
    def test_session_isolation(self, conversation_service):
        """Test that multiple sessions don't interfere"""
        session_id_1, _ = conversation_service.start_investigation(provider="groq")
        session_id_2, _ = conversation_service.start_investigation(provider="openai")
        
        # Sessions should be separate
        assert session_id_1 != session_id_2
        assert conversation_service.sessions[session_id_1].provider == "groq"
        assert conversation_service.sessions[session_id_2].provider == "openai"
        
        # Message histories should be separate
        assert len(conversation_service.messages[session_id_1]) == 1
        assert len(conversation_service.messages[session_id_2]) == 1


class TestDependencyInjection:
    """Test suite for dependency injection"""
    
    def test_get_conversation_service(self):
        """Test dependency injection helper"""
        service = get_conversation_service()
        
        assert isinstance(service, ConversationService)
        assert isinstance(service.llm, LLMService)
