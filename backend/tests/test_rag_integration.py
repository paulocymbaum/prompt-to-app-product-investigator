"""
Integration tests for RAG-enhanced conversation flow.

Tests the full integration between ConversationService, RAGService,
and QuestionGenerator to ensure context-aware question generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.conversation_service import ConversationService
from services.rag_service import RAGService
from services.question_generator import QuestionGenerator
from services.llm_service import LLMService
from storage.conversation_storage import ConversationStorage
from models.conversation import (
    Question,
    ConversationState,
    MessageRole
)


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing."""
    llm = MagicMock(spec=LLMService)
    llm.generate_response = AsyncMock(
        return_value="Can you elaborate on the main features?"
    )
    return llm


@pytest.fixture
def conversation_storage(tmp_path):
    """Create conversation storage with temp directory."""
    storage_dir = tmp_path / "conversations"
    storage_dir.mkdir()
    return ConversationStorage(base_dir=str(storage_dir))


@pytest.fixture
def rag_service(conversation_storage, tmp_path):
    """Create RAG service with temp vector store."""
    vector_dir = tmp_path / "vectors"
    vector_dir.mkdir()
    return RAGService(
        storage=conversation_storage,
        persist_directory=str(vector_dir)
    )


@pytest.fixture
def question_generator(mock_llm_service):
    """Create question generator."""
    return QuestionGenerator(llm_service=mock_llm_service)


@pytest.fixture
def conversation_service(mock_llm_service, rag_service, question_generator):
    """Create conversation service with all dependencies."""
    return ConversationService(
        llm_service=mock_llm_service,
        rag_service=rag_service,
        question_generator=question_generator
    )


class TestRAGIntegrationBasics:
    """Test basic RAG integration functionality."""
    
    def test_service_initialization_with_rag(
        self,
        mock_llm_service,
        rag_service,
        question_generator
    ):
        """Test that ConversationService initializes with RAG and QuestionGen."""
        service = ConversationService(
            llm_service=mock_llm_service,
            rag_service=rag_service,
            question_generator=question_generator
        )
        
        assert service.rag is not None
        assert service.question_gen is not None
        assert service.llm is not None
    
    def test_start_investigation_uses_question_generator(
        self,
        conversation_service
    ):
        """Test that starting investigation uses QuestionGenerator."""
        session_id, question = conversation_service.start_investigation()
        
        assert session_id is not None
        assert question is not None
        assert question.text == "Let's start by understanding your product idea. What problem does your product solve?"
        assert question.category == "start"
    
    def test_fallback_without_rag_and_question_gen(self, mock_llm_service):
        """Test that service works without RAG and QuestionGen (legacy mode)."""
        service = ConversationService(llm_service=mock_llm_service)
        
        assert service.rag is None
        assert service.question_gen is None
        
        # Should still work with templates
        session_id, question = service.start_investigation()
        assert question is not None


class TestRAGPersistence:
    """Test RAG persistence during conversation."""
    
    @pytest.mark.asyncio
    async def test_interaction_persisted_to_rag(
        self,
        conversation_service,
        rag_service
    ):
        """Test that Q&A pairs are persisted to RAG."""
        # Start investigation
        session_id, initial_question = conversation_service.start_investigation()
        
        # Provide a detailed answer
        answer = "A task management app for remote teams with real-time collaboration features"
        
        # Process answer
        await conversation_service.process_answer(session_id, answer)
        
        # Verify interaction was persisted
        context = rag_service.retrieve_context(
            query="task management",
            session_id=session_id,
            top_k=5
        )
        
        assert len(context) > 0
        assert any("task management" in chunk.lower() for chunk in context)
    
    @pytest.mark.asyncio
    async def test_multiple_interactions_persisted(
        self,
        conversation_service,
        rag_service
    ):
        """Test that multiple Q&A pairs are all persisted."""
        session_id, _ = conversation_service.start_investigation()
        
        answers = [
            "A project management tool for developers",
            "It helps teams track tasks and deadlines",
            "Primary users are software development teams"
        ]
        
        for answer in answers:
            await conversation_service.process_answer(session_id, answer)
        
        # Verify all interactions are retrievable
        context = rag_service.retrieve_context(
            query="project management developers",
            session_id=session_id,
            top_k=10
        )
        
        # Should have chunks from the conversation
        assert len(context) >= 2  # At least some interactions


class TestContextRetrieval:
    """Test context retrieval and usage in question generation."""
    
    @pytest.mark.asyncio
    async def test_context_retrieved_before_question_generation(
        self,
        conversation_service,
        rag_service
    ):
        """Test that RAG context is retrieved before generating questions."""
        session_id, _ = conversation_service.start_investigation()
        
        # First answer
        await conversation_service.process_answer(
            session_id,
            "A comprehensive project management platform"
        )
        
        # Second answer - should retrieve context from first
        await conversation_service.process_answer(
            session_id,
            "It includes task tracking and team collaboration"
        )
        
        # Verify context exists
        context = rag_service.retrieve_context(
            query="collaboration",
            session_id=session_id
        )
        
        assert len(context) > 0
    
    @pytest.mark.asyncio
    async def test_context_passed_to_question_generator(
        self,
        mock_llm_service,
        rag_service,
        question_generator,
        monkeypatch
    ):
        """Test that retrieved context is passed to QuestionGenerator."""
        # Track calls to generate_next_question
        original_method = question_generator.generate_next_question
        calls = []
        
        async def tracked_generate(*args, **kwargs):
            calls.append(kwargs)
            return await original_method(*args, **kwargs)
        
        question_generator.generate_next_question = tracked_generate
        
        service = ConversationService(
            llm_service=mock_llm_service,
            rag_service=rag_service,
            question_generator=question_generator
        )
        
        session_id, _ = service.start_investigation()
        
        # Answer with enough detail to not trigger follow-up
        await service.process_answer(
            session_id,
            "A comprehensive project management platform with real-time collaboration features for remote teams"
        )
        
        # Second answer
        await service.process_answer(
            session_id,
            "It helps teams track tasks, deadlines, and communicate effectively across time zones"
        )
        
        # Verify context was passed
        assert len(calls) >= 1
        # Context should be passed (might be empty list or None if no relevant context)
        assert 'context' in calls[-1]


class TestConversationFlow:
    """Test full conversation flow with RAG integration."""
    
    @pytest.mark.asyncio
    async def test_complete_conversation_flow(
        self,
        conversation_service
    ):
        """Test a complete conversation from start to finish."""
        session_id, initial_q = conversation_service.start_investigation()
        
        # Simulate conversation
        answers = [
            "A task management platform for software development teams with integrated code tracking",
            "The main features include sprint planning, backlog management, code commit tracking, and team dashboards",
            "Primary users are software developers, project managers, and team leads in tech companies",
            "Target age range is 25-45, mostly in North America and Europe, with technical proficiency",
            "Modern, minimal design with dark mode support, inspired by GitHub and Linear aesthetics",
            "Main competitors are Jira, Asana, and Linear. We focus on developer experience and code integration",
            "We need integration with GitHub, GitLab, and Slack. Tech stack should be Python and React",
            "We've covered everything thoroughly. The vision is clear."
        ]
        
        for i, answer in enumerate(answers):
            next_q = await conversation_service.process_answer(session_id, answer)
            
            if i < len(answers) - 1:
                assert next_q is not None, f"Expected question after answer {i}"
                assert next_q.text is not None
        
        # Verify session state
        session = conversation_service.get_session(session_id)
        assert session is not None
        
        # Verify messages were recorded
        messages = conversation_service.get_conversation_history(session_id)
        assert len(messages) > len(answers)  # Should have questions and answers
    
    @pytest.mark.asyncio
    async def test_short_answer_triggers_followup_with_context(
        self,
        conversation_service,
        rag_service
    ):
        """Test that short answers trigger follow-ups with RAG context."""
        session_id, _ = conversation_service.start_investigation()
        
        # First detailed answer
        await conversation_service.process_answer(
            session_id,
            "A comprehensive task management platform for remote software teams"
        )
        
        # Short answer should trigger follow-up
        next_q = await conversation_service.process_answer(
            session_id,
            "Yes"  # Very short answer
        )
        
        assert next_q is not None
        assert next_q.is_followup is True
        
        # Context should be available for follow-up
        context = rag_service.retrieve_context(
            query="task management",
            session_id=session_id
        )
        assert len(context) > 0


class TestSessionIsolation:
    """Test that RAG contexts are isolated between sessions."""
    
    @pytest.mark.asyncio
    async def test_sessions_have_separate_rag_contexts(
        self,
        conversation_service,
        rag_service
    ):
        """Test that different sessions maintain separate RAG contexts."""
        # Session 1
        session1_id, _ = conversation_service.start_investigation()
        await conversation_service.process_answer(
            session1_id,
            "A project management tool for construction companies"
        )
        
        # Session 2
        session2_id, _ = conversation_service.start_investigation()
        await conversation_service.process_answer(
            session2_id,
            "A fitness tracking app for marathon runners"
        )
        
        # Verify contexts are separate
        context1 = rag_service.retrieve_context(
            query="construction",
            session_id=session1_id
        )
        context2 = rag_service.retrieve_context(
            query="fitness",
            session_id=session2_id
        )
        
        # Each session should retrieve its own context
        assert any("construction" in chunk.lower() for chunk in context1)
        assert any("fitness" in chunk.lower() for chunk in context2)
        
        # Cross-contamination check
        assert not any("fitness" in chunk.lower() for chunk in context1)
        assert not any("construction" in chunk.lower() for chunk in context2)


class TestErrorHandling:
    """Test error handling in RAG integration."""
    
    @pytest.mark.asyncio
    async def test_graceful_handling_of_rag_persistence_error(
        self,
        mock_llm_service,
        question_generator
    ):
        """Test that conversation continues if RAG persistence fails."""
        # Create RAG service that throws errors
        failing_rag = MagicMock(spec=RAGService)
        failing_rag.persist_interaction = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        failing_rag.retrieve_context = MagicMock(return_value=[])
        
        service = ConversationService(
            llm_service=mock_llm_service,
            rag_service=failing_rag,
            question_generator=question_generator
        )
        
        session_id, _ = service.start_investigation()
        
        # Should not raise exception, should log error and continue
        next_q = await service.process_answer(
            session_id,
            "A project management tool"
        )
        
        assert next_q is not None
    
    @pytest.mark.asyncio
    async def test_graceful_handling_of_rag_retrieval_error(
        self,
        mock_llm_service,
        question_generator
    ):
        """Test that conversation continues if RAG retrieval fails."""
        # Create RAG service with failing retrieval
        failing_rag = MagicMock(spec=RAGService)
        failing_rag.persist_interaction = AsyncMock(return_value=None)
        failing_rag.retrieve_context = MagicMock(
            side_effect=Exception("Vector store unavailable")
        )
        
        service = ConversationService(
            llm_service=mock_llm_service,
            rag_service=failing_rag,
            question_generator=question_generator
        )
        
        session_id, _ = service.start_investigation()
        
        # Should handle error gracefully
        next_q = await service.process_answer(
            session_id,
            "A task management platform"
        )
        
        assert next_q is not None


class TestQuestionQuality:
    """Test that RAG context improves question quality."""
    
    @pytest.mark.asyncio
    async def test_context_available_for_relevant_questions(
        self,
        conversation_service,
        rag_service
    ):
        """Test that relevant context is retrieved for question generation."""
        session_id, _ = conversation_service.start_investigation()
        
        # Build up context
        await conversation_service.process_answer(
            session_id,
            "A project management platform specifically designed for software development teams"
        )
        
        await conversation_service.process_answer(
            session_id,
            "It integrates directly with version control systems like Git to track code changes"
        )
        
        # Query for relevant context
        context = rag_service.retrieve_context(
            query="software development version control",
            session_id=session_id,
            top_k=3
        )
        
        # Context should be relevant
        assert len(context) > 0
        assert any("software" in chunk.lower() or "development" in chunk.lower() for chunk in context)
