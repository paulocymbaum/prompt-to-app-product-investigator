"""
Question Generator Service

Generates intelligent, context-aware questions for product investigation.
Uses category-based templates and LLM for dynamic follow-ups.
"""

import structlog
import uuid
from typing import List, Optional
from datetime import datetime

from models.conversation import Session, Question, ConversationState
from services.llm_service import LLMService

logger = structlog.get_logger()


class QuestionGenerator:
    """Service to generate context-aware questions for product investigation."""
    
    def __init__(self, llm_service: LLMService):
        """
        Initialize Question Generator.
        
        Args:
            llm_service: LLM service for dynamic question generation
        """
        self.llm = llm_service
        
        # Category-based question templates
        self.category_templates = {
            ConversationState.START: [
                "Let's start by understanding your product idea. What problem does your product solve?"
            ],
            ConversationState.FUNCTIONALITY: [
                "What are the main features users will interact with?",
                "How will users accomplish their primary goals with your product?",
                "What makes your product's functionality unique or innovative?"
            ],
            ConversationState.USERS: [
                "Who are the primary users of your product?",
                "What expertise level do your users have (beginner, intermediate, expert)?",
                "What are the key characteristics of your target users?"
            ],
            ConversationState.DEMOGRAPHICS: [
                "What is the age range of your target audience?",
                "What geographic regions are you primarily targeting?",
                "Are there specific demographic factors important for your product?"
            ],
            ConversationState.DESIGN: [
                "Do you have specific design preferences (modern, minimal, bold, playful)?",
                "Are there any brand colors or style guidelines you'd like to follow?",
                "What mood or feeling should the design convey to users?"
            ],
            ConversationState.MARKET: [
                "Who are your main competitors in the market?",
                "What is your unique value proposition compared to alternatives?",
                "What market segment or niche are you targeting?"
            ],
            ConversationState.TECHNICAL: [
                "Do you have any technical stack preferences or requirements?",
                "What are your scalability expectations (users, data volume)?",
                "Are there specific integrations or APIs you need to support?"
            ],
            ConversationState.REVIEW: [
                "Let me summarize what we've discussed. Does this capture your vision accurately?",
                "Is there anything important we haven't covered yet?",
                "Would you like to clarify or expand on any aspect?"
            ]
        }
        
        # State progression order
        self.state_order = [
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
        
        # Minimum answer length for acceptable responses (in words)
        self.min_answer_words = 10
        
        logger.info(
            "QuestionGenerator initialized",
            categories=len(self.category_templates),
            states=len(self.state_order)
        )
    
    async def generate_next_question(
        self,
        session: Session,
        latest_answer: str,
        context: Optional[List[str]] = None
    ) -> Optional[Question]:
        """
        Generate the next question based on session state and latest answer.
        
        Args:
            session: Current conversation session
            latest_answer: User's most recent answer
            context: RAG context chunks (optional)
            
        Returns:
            Next Question object, or None if conversation is complete
        """
        context = context or []
        
        # Check if conversation is complete
        next_state = self._determine_next_state(session.state)
        
        if next_state == ConversationState.COMPLETE:
            logger.info("Conversation complete", session_id=session.id)
            return None
        
        # Determine if we need a follow-up question
        needs_followup = self._needs_followup(latest_answer, session.state)
        
        if needs_followup:
            logger.info(
                "Generating follow-up question",
                session_id=session.id,
                state=session.state.value,
                answer_length=len(latest_answer.split())
            )
            return await self._generate_followup(
                session,
                latest_answer,
                context,
                messages=None  # Will be passed from ConversationService
            )
        else:
            logger.info(
                "Generating category question",
                session_id=session.id,
                next_state=next_state.value
            )
            return await self._generate_category_question(
                next_state,
                context,
                session,
                messages=None  # Will be passed from ConversationService
            )
    
    def _determine_next_state(
        self,
        current_state: ConversationState
    ) -> ConversationState:
        """
        Determine the next conversation state.
        
        Args:
            current_state: Current conversation state
            
        Returns:
            Next conversation state
        """
        try:
            current_idx = self.state_order.index(current_state)
            if current_idx + 1 < len(self.state_order):
                return self.state_order[current_idx + 1]
        except ValueError:
            logger.warning(
                "Unknown state, moving to START",
                state=current_state.value
            )
            return ConversationState.START
        
        return ConversationState.COMPLETE
    
    def _needs_followup(self, answer: str, current_state: ConversationState) -> bool:
        """
        Determine if the answer needs a follow-up question.
        
        Args:
            answer: User's answer
            current_state: Current conversation state
            
        Returns:
            True if follow-up is needed, False otherwise
        """
        # Don't follow-up in REVIEW state
        if current_state == ConversationState.REVIEW:
            return False
        
        # Check answer length
        word_count = len(answer.split())
        
        # Very short answers likely need clarification
        if word_count < self.min_answer_words:
            return True
        
        # Check for vague responses
        vague_indicators = [
            "i don't know",
            "not sure",
            "maybe",
            "possibly",
            "whatever",
            "anything",
            "doesn't matter"
        ]
        
        answer_lower = answer.lower()
        if any(indicator in answer_lower for indicator in vague_indicators):
            return True
        
        return False
    
    async def _generate_followup(
        self,
        session: Session,
        latest_answer: str,
        context: List[str],
        messages: Optional[List] = None
    ) -> Question:
        """
        Generate a follow-up question using LLM.
        
        Args:
            session: Current session
            latest_answer: User's latest answer
            context: RAG context chunks
            messages: Optional list of Message objects from conversation history
            
        Returns:
            Follow-up Question object
        """
        system_prompt = """You are an expert product investigator conducting a discovery interview.
Your goal is to deeply understand the user's product idea through thoughtful questions.

Generate a concise follow-up question that:
1. Digs deeper into their latest answer
2. Helps clarify vague or incomplete information
3. Reveals important details about their product
4. Is specific and actionable
5. Is friendly and conversational

Keep the question under 20 words. Do not include any preamble or explanation."""
        
        # Build context string
        context_str = "\n\n".join(context[-3:]) if context else ""
        
        # Get conversation history (last 4 exchanges)
        history_str = ""
        if messages:
            recent_messages = messages[-8:] if len(messages) >= 8 else messages
            history_str = "\n".join([
                f"{'Q' if msg.role == 'assistant' else 'A'}: {msg.content}"
                for msg in recent_messages
            ])
        
        context_section = ""
        if context_str:
            context_section = f"\nPrevious context:\n{context_str}\n"
        
        user_prompt = f"""Current investigation category: {session.state.value}

Recent conversation:
{history_str}

User's latest answer (needs clarification): {latest_answer}
{context_section}
Generate a follow-up question to better understand their product."""
        
        try:
            question_text = await self.llm.generate_response(
                system_prompt,
                user_prompt,
                temperature=0.7
            )
            
            # Clean up the response
            question_text = question_text.strip()
            
            # Ensure it ends with a question mark
            if not question_text.endswith('?'):
                question_text += '?'
            
        except Exception as e:
            logger.error(
                "LLM follow-up generation failed, using template",
                error=str(e),
                session_id=session.id
            )
            # Fallback to template-based follow-up
            question_text = self._get_template_followup(session.state, latest_answer)
        
        return Question(
            id=str(uuid.uuid4()),
            text=question_text,
            category=session.state.value,
            is_followup=True,
            timestamp=datetime.utcnow()
        )
    
    async def _generate_category_question(
        self,
        state: ConversationState,
        context: List[str],
        session: Session,
        messages: Optional[List] = None
    ) -> Optional[Question]:
        """
        Generate a category-specific question.
        
        Args:
            state: Target conversation state
            context: RAG context chunks
            session: Current session
            messages: Optional list of Message objects from conversation history
            
        Returns:
            Category Question object, or None if no templates available
        """
        templates = self.category_templates.get(state, [])
        
        if not templates:
            logger.warning(
                "No templates for state, ending conversation",
                state=state.value
            )
            return None
        
        # For MVP, use template rotation
        # Count how many questions we've asked in this category
        category_count = 0
        if messages:
            category_count = sum(
                1 for msg in messages
                if msg.role == 'assistant' and msg.metadata.get('category') == state.value
            )
        
        # Select template (rotate through available templates)
        template_idx = category_count % len(templates)
        question_text = templates[template_idx]
        
        # Optionally enhance with LLM for personalization (future enhancement)
        # For now, use templates directly
        
        return Question(
            id=str(uuid.uuid4()),
            text=question_text,
            category=state.value,
            is_followup=False,
            timestamp=datetime.utcnow()
        )
    
    def _get_template_followup(self, state: ConversationState, answer: str) -> str:
        """
        Get a template-based follow-up question (fallback).
        
        Args:
            state: Current conversation state
            answer: User's answer
            
        Returns:
            Follow-up question text
        """
        # Generic follow-up templates by category
        followup_templates = {
            ConversationState.FUNCTIONALITY: [
                "Can you give me a specific example of how that would work?",
                "What would be the most important aspect of that feature?",
                "How do you envision users interacting with that?"
            ],
            ConversationState.USERS: [
                "Can you describe a typical user's background or expertise?",
                "What would motivate someone to use your product?",
                "What problems do these users currently face?"
            ],
            ConversationState.DEMOGRAPHICS: [
                "Are there specific characteristics that define your target audience?",
                "Which demographic factors are most relevant to your product?",
                "How would you reach this audience?"
            ],
            ConversationState.DESIGN: [
                "What emotion should users feel when using your product?",
                "Are there any design examples you admire?",
                "What should be the visual focus of the interface?"
            ],
            ConversationState.MARKET: [
                "What makes your approach different from existing solutions?",
                "Who would be your ideal first customers?",
                "What's the key benefit users would pay for?"
            ],
            ConversationState.TECHNICAL: [
                "What technical capabilities are critical for your product?",
                "Do you have any performance or security requirements?",
                "What platforms or devices need to be supported?"
            ]
        }
        
        templates = followup_templates.get(
            state,
            ["Could you tell me more about that?", "Can you elaborate on that point?"]
        )
        
        # Return first template (simple fallback)
        return templates[0]
    
    def get_initial_question(self) -> Question:
        """
        Get the initial conversation question.
        
        Returns:
            Initial Question object
        """
        question_text = self.category_templates[ConversationState.START][0]
        
        return Question(
            id=str(uuid.uuid4()),
            text=question_text,
            category=ConversationState.START.value,
            is_followup=False,
            timestamp=datetime.utcnow()
        )
    
    def get_category_coverage(self, session: Session, messages: Optional[List] = None) -> dict:
        """
        Get statistics on category coverage in the conversation.
        
        Args:
            session: Current session
            messages: Optional list of Message objects from conversation history
            
        Returns:
            Dictionary with coverage statistics
        """
        covered_states = set()
        question_count_by_category = {}
        
        if messages:
            for msg in messages:
                if msg.role == 'assistant':
                    category = msg.metadata.get('category')
                    if category:
                        covered_states.add(category)
                        question_count_by_category[category] = \
                            question_count_by_category.get(category, 0) + 1
        
        total_categories = len([s for s in self.state_order 
                               if s not in [ConversationState.START, 
                                          ConversationState.COMPLETE]])
        
        return {
            'covered_categories': len(covered_states),
            'total_categories': total_categories,
            'coverage_percentage': (len(covered_states) / total_categories * 100) 
                                  if total_categories > 0 else 0,
            'questions_by_category': question_count_by_category
        }


# Singleton instance
_question_generator_instance: Optional[QuestionGenerator] = None


def get_question_generator(llm_service: Optional[LLMService] = None) -> QuestionGenerator:
    """
    Get or create Question Generator singleton.
    
    Args:
        llm_service: LLM service instance (required for first call)
        
    Returns:
        QuestionGenerator instance
    """
    global _question_generator_instance
    
    if _question_generator_instance is None:
        if llm_service is None:
            raise ValueError("llm_service required for first QuestionGenerator initialization")
        
        _question_generator_instance = QuestionGenerator(llm_service=llm_service)
    
    return _question_generator_instance
