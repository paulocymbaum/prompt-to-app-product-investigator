"""
Unit tests for Question Generator

Tests question generation, templates, state progression, and LLM integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from services.question_generator import QuestionGenerator, get_question_generator
from services.llm_service import LLMService
from models.conversation import Session, Message, Question, ConversationState, MessageRole


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    llm = AsyncMock(spec=LLMService)
    llm.generate_response = AsyncMock(return_value="Can you elaborate on that?")
    return llm


@pytest.fixture
def question_generator(mock_llm_service):
    """Create a Question Generator instance."""
    return QuestionGenerator(llm_service=mock_llm_service)


@pytest.fixture
def sample_session():
    """Create a sample session."""
    return Session(
        id="test-session-001",
        state=ConversationState.START,
        started_at=datetime.utcnow(),
        last_updated=datetime.utcnow(),
        status="active"
    )


@pytest.fixture
def sample_messages():
    """Create sample messages."""
    return [
        Message(
            id="msg-1",
            session_id="test-session-001",
            role=MessageRole.ASSISTANT,
            content="What problem does your product solve?",
            metadata={"category": "start"}
        ),
        Message(
            id="msg-2",
            session_id="test-session-001",
            role=MessageRole.USER,
            content="A task management platform for remote teams",
            metadata={}
        )
    ]


class TestQuestionGeneratorBasics:
    """Test basic question generator functionality."""
    
    def test_initialization(self, question_generator):
        """Test Question Generator initialization."""
        assert question_generator is not None
        assert len(question_generator.category_templates) > 0
        assert len(question_generator.state_order) == 9
        assert question_generator.min_answer_words == 10
    
    def test_get_initial_question(self, question_generator):
        """Test getting the initial question."""
        question = question_generator.get_initial_question()
        
        assert question is not None
        assert isinstance(question, Question)
        assert question.category == "start"
        assert question.is_followup is False
        assert "problem" in question.text.lower() or "product" in question.text.lower()
    
    def test_singleton_access(self, mock_llm_service):
        """Test singleton access pattern."""
        # Reset singleton
        import services.question_generator as qg_module
        qg_module._question_generator_instance = None
        
        qg1 = get_question_generator(llm_service=mock_llm_service)
        qg2 = get_question_generator()
        
        assert qg1 is qg2
    
    def test_singleton_requires_llm_first_call(self):
        """Test that singleton requires LLM service on first call."""
        import services.question_generator as qg_module
        qg_module._question_generator_instance = None
        
        with pytest.raises(ValueError, match="llm_service required"):
            get_question_generator()


class TestStateProgression:
    """Test conversation state progression."""
    
    def test_determine_next_state_from_start(self, question_generator):
        """Test state progression from START."""
        next_state = question_generator._determine_next_state(ConversationState.START)
        assert next_state == ConversationState.FUNCTIONALITY
    
    def test_determine_next_state_from_functionality(self, question_generator):
        """Test state progression from FUNCTIONALITY."""
        next_state = question_generator._determine_next_state(ConversationState.FUNCTIONALITY)
        assert next_state == ConversationState.USERS
    
    def test_determine_next_state_from_review(self, question_generator):
        """Test state progression from REVIEW."""
        next_state = question_generator._determine_next_state(ConversationState.REVIEW)
        assert next_state == ConversationState.COMPLETE
    
    def test_determine_next_state_complete(self, question_generator):
        """Test that COMPLETE state stays COMPLETE."""
        next_state = question_generator._determine_next_state(ConversationState.COMPLETE)
        assert next_state == ConversationState.COMPLETE
    
    def test_state_order_completeness(self, question_generator):
        """Test that all conversation states are in state_order."""
        expected_states = [
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
        
        assert question_generator.state_order == expected_states


class TestFollowUpDecision:
    """Test follow-up question decision logic."""
    
    def test_needs_followup_short_answer(self, question_generator):
        """Test that short answers trigger follow-up."""
        short_answer = "Yes"
        needs_followup = question_generator._needs_followup(
            short_answer,
            ConversationState.FUNCTIONALITY
        )
        assert needs_followup is True
    
    def test_needs_followup_vague_answer(self, question_generator):
        """Test that vague answers trigger follow-up."""
        vague_answer = "I don't know, maybe something with users"
        needs_followup = question_generator._needs_followup(
            vague_answer,
            ConversationState.USERS
        )
        assert needs_followup is True
    
    def test_no_followup_detailed_answer(self, question_generator):
        """Test that detailed answers don't trigger follow-up."""
        detailed_answer = "A comprehensive task management platform designed specifically for remote teams, featuring real-time collaboration, automated workflows, and integrated communication tools."
        needs_followup = question_generator._needs_followup(
            detailed_answer,
            ConversationState.FUNCTIONALITY
        )
        assert needs_followup is False
    
    def test_no_followup_in_review_state(self, question_generator):
        """Test that REVIEW state never triggers follow-up."""
        short_answer = "Yes"
        needs_followup = question_generator._needs_followup(
            short_answer,
            ConversationState.REVIEW
        )
        assert needs_followup is False


class TestQuestionGeneration:
    """Test question generation."""
    
    @pytest.mark.asyncio
    async def test_generate_next_question_complete(
        self,
        question_generator,
        sample_session
    ):
        """Test that COMPLETE state returns None."""
        sample_session.state = ConversationState.COMPLETE
        
        question = await question_generator.generate_next_question(
            sample_session,
            "Final answer",
            context=[]
        )
        
        assert question is None
    
    @pytest.mark.asyncio
    async def test_generate_category_question(
        self,
        question_generator,
        sample_session
    ):
        """Test generating a category question."""
        sample_session.state = ConversationState.START
        detailed_answer = "A comprehensive task management platform for remote teams with automated workflows"
        
        question = await question_generator.generate_next_question(
            sample_session,
            detailed_answer,
            context=[]
        )
        
        assert question is not None
        assert isinstance(question, Question)
        assert question.category == "functionality"
        assert question.is_followup is False
    
    @pytest.mark.asyncio
    async def test_generate_followup_question(
        self,
        question_generator,
        sample_session,
        mock_llm_service
    ):
        """Test generating a follow-up question."""
        sample_session.state = ConversationState.FUNCTIONALITY
        short_answer = "Yes"
        
        mock_llm_service.generate_response.return_value = "What specific features are most important"
        
        question = await question_generator.generate_next_question(
            sample_session,
            short_answer,
            context=[]
        )
        
        assert question is not None
        assert isinstance(question, Question)
        assert question.is_followup is True
        assert question.category == "functionality"
        mock_llm_service.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_followup_with_context(
        self,
        question_generator,
        sample_session,
        sample_messages,
        mock_llm_service
    ):
        """Test generating follow-up with context."""
        sample_session.state = ConversationState.FUNCTIONALITY
        short_answer = "Not sure"
        context = ["Previous: Q: What is your product? A: A task management app"]
        
        mock_llm_service.generate_response.return_value = "Can you describe the main workflow"
        
        question = await question_generator.generate_next_question(
            sample_session,
            short_answer,
            context=context
        )
        
        assert question is not None
        assert question.is_followup is True
        
        # Verify context was passed to LLM
        call_args = mock_llm_service.generate_response.call_args
        user_prompt = call_args[0][1]
        assert "Previous context" in user_prompt or "context" in user_prompt.lower()


class TestTemplates:
    """Test question templates."""
    
    def test_all_states_have_templates(self, question_generator):
        """Test that all states have question templates."""
        required_states = [
            ConversationState.START,
            ConversationState.FUNCTIONALITY,
            ConversationState.USERS,
            ConversationState.DEMOGRAPHICS,
            ConversationState.DESIGN,
            ConversationState.MARKET,
            ConversationState.TECHNICAL,
            ConversationState.REVIEW
        ]
        
        for state in required_states:
            templates = question_generator.category_templates.get(state)
            assert templates is not None, f"No templates for {state.value}"
            assert len(templates) > 0, f"Empty templates for {state.value}"
    
    def test_template_content_quality(self, question_generator):
        """Test that templates are well-formed questions."""
        for state, templates in question_generator.category_templates.items():
            for template in templates:
                # Should be a string
                assert isinstance(template, str)
                
                # Should not be empty
                assert len(template) > 10
                
                # Should end with question mark
                assert template.endswith('?')
                
                # Should be capitalized
                assert template[0].isupper()
    
    @pytest.mark.asyncio
    async def test_template_rotation(
        self,
        question_generator,
        sample_session,
        sample_messages
    ):
        """Test that templates rotate through available options."""
        sample_session.state = ConversationState.START
        
        # Simulate multiple questions in same category
        messages = []
        for i in range(5):
            msg = Message(
                id=f"msg-{i}",
                session_id="test-session-001",
                role=MessageRole.ASSISTANT,
                content=f"Question {i}",
                metadata={"category": "functionality"}
            )
            messages.append(msg)
        
        question = await question_generator._generate_category_question(
            ConversationState.FUNCTIONALITY,
            [],
            sample_session,
            messages=messages
        )
        
        assert question is not None
        # Should select template based on count


class TestCategoryCoverage:
    """Test category coverage tracking."""
    
    def test_get_category_coverage_empty(
        self,
        question_generator,
        sample_session
    ):
        """Test coverage with no messages."""
        coverage = question_generator.get_category_coverage(
            sample_session,
            messages=[]
        )
        
        assert coverage['covered_categories'] == 0
        assert coverage['total_categories'] == 7  # Excluding START and COMPLETE
        assert coverage['coverage_percentage'] == 0
    
    def test_get_category_coverage_partial(
        self,
        question_generator,
        sample_session
    ):
        """Test coverage with some categories."""
        messages = [
            Message(
                id="msg-1",
                session_id="test-session-001",
                role=MessageRole.ASSISTANT,
                content="Question 1",
                metadata={"category": "functionality"}
            ),
            Message(
                id="msg-2",
                session_id="test-session-001",
                role=MessageRole.ASSISTANT,
                content="Question 2",
                metadata={"category": "users"}
            ),
            Message(
                id="msg-3",
                session_id="test-session-001",
                role=MessageRole.USER,
                content="Answer",
                metadata={}
            )
        ]
        
        coverage = question_generator.get_category_coverage(
            sample_session,
            messages=messages
        )
        
        assert coverage['covered_categories'] == 2
        assert coverage['total_categories'] == 7
        assert coverage['coverage_percentage'] > 0
        assert 'functionality' in coverage['questions_by_category']
        assert 'users' in coverage['questions_by_category']


class TestLLMIntegration:
    """Test LLM integration."""
    
    @pytest.mark.asyncio
    async def test_llm_prompt_construction(
        self,
        question_generator,
        sample_session,
        mock_llm_service
    ):
        """Test LLM prompt is properly constructed."""
        sample_session.state = ConversationState.FUNCTIONALITY
        
        await question_generator._generate_followup(
            sample_session,
            "Short answer",
            context=["Previous context"],
            messages=[]
        )
        
        mock_llm_service.generate_response.assert_called_once()
        
        # Check system prompt
        system_prompt = mock_llm_service.generate_response.call_args[0][0]
        assert "product investigator" in system_prompt.lower()
        assert "concise" in system_prompt.lower()
        
        # Check user prompt
        user_prompt = mock_llm_service.generate_response.call_args[0][1]
        assert "Short answer" in user_prompt
        assert "functionality" in user_prompt.lower()
    
    @pytest.mark.asyncio
    async def test_llm_fallback_on_error(
        self,
        question_generator,
        sample_session,
        mock_llm_service
    ):
        """Test fallback to template when LLM fails."""
        sample_session.state = ConversationState.FUNCTIONALITY
        
        # Make LLM raise an error
        mock_llm_service.generate_response.side_effect = Exception("LLM Error")
        
        question = await question_generator._generate_followup(
            sample_session,
            "Short answer",
            context=[],
            messages=[]
        )
        
        # Should still return a question (fallback)
        assert question is not None
        assert question.is_followup is True
        assert question.text.endswith('?')
    
    @pytest.mark.asyncio
    async def test_followup_question_formatting(
        self,
        question_generator,
        sample_session,
        mock_llm_service
    ):
        """Test that follow-up questions are properly formatted."""
        sample_session.state = ConversationState.USERS
        
        # Return answer without question mark
        mock_llm_service.generate_response.return_value = "Can you tell me more"
        
        question = await question_generator._generate_followup(
            sample_session,
            "Short",
            context=[],
            messages=[]
        )
        
        # Should add question mark
        assert question.text.endswith('?')


class TestTemplateFollowups:
    """Test template-based followups (fallback)."""
    
    def test_get_template_followup_functionality(self, question_generator):
        """Test template followup for FUNCTIONALITY."""
        followup = question_generator._get_template_followup(
            ConversationState.FUNCTIONALITY,
            "Some answer"
        )
        
        assert isinstance(followup, str)
        assert len(followup) > 10
        assert followup.endswith('?')
    
    def test_get_template_followup_all_categories(self, question_generator):
        """Test template followup for all categories."""
        categories = [
            ConversationState.FUNCTIONALITY,
            ConversationState.USERS,
            ConversationState.DEMOGRAPHICS,
            ConversationState.DESIGN,
            ConversationState.MARKET,
            ConversationState.TECHNICAL
        ]
        
        for category in categories:
            followup = question_generator._get_template_followup(category, "answer")
            assert followup is not None
            assert len(followup) > 5
            assert followup.endswith('?')


class TestEdgeCases:
    """Test edge cases."""
    
    @pytest.mark.asyncio
    async def test_generate_with_empty_context(
        self,
        question_generator,
        sample_session
    ):
        """Test generation with empty context."""
        sample_session.state = ConversationState.START
        
        question = await question_generator.generate_next_question(
            sample_session,
            "Detailed answer about my product",
            context=[]
        )
        
        assert question is not None
    
    @pytest.mark.asyncio
    async def test_generate_with_none_context(
        self,
        question_generator,
        sample_session
    ):
        """Test generation with None context."""
        sample_session.state = ConversationState.START
        
        question = await question_generator.generate_next_question(
            sample_session,
            "Detailed answer about my product",
            context=None
        )
        
        assert question is not None
    
    def test_vague_answer_indicators(self, question_generator):
        """Test detection of vague answer indicators."""
        vague_answers = [
            "I don't know",
            "Not sure about that",
            "Maybe something",
            "Whatever works",
            "Doesn't matter to me",
            "Possibly yes"
        ]
        
        for answer in vague_answers:
            needs_followup = question_generator._needs_followup(
                answer,
                ConversationState.FUNCTIONALITY
            )
            assert needs_followup is True, f"Failed to detect vague: {answer}"
    
    @pytest.mark.asyncio
    async def test_generate_question_at_boundary_state(
        self,
        question_generator,
        sample_session
    ):
        """Test question generation at boundary state (REVIEW)."""
        sample_session.state = ConversationState.REVIEW
        
        question = await question_generator.generate_next_question(
            sample_session,
            "Everything looks good",
            context=[]
        )
        
        # Should move to COMPLETE and return None
        assert question is None
