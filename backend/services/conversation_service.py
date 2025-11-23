"""
Conversation Service for managing investigation conversations.

This service handles:
- Session initialization and management
- Conversation state machine (START → FUNCTIONALITY → ... → COMPLETE)
- Initial and follow-up question generation
- Message history tracking
- State transitions

SOLID Principles:
- Single Responsibility: Manages only conversation flow
- Open/Closed: Extensible for new conversation states
- Dependency Inversion: Depends on LLMService abstraction
"""

import uuid
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import structlog

from models.conversation import (
    Session,
    Message,
    Question,
    MessageRole,
    ConversationState
)
from services.llm_service import LLMService
from services.rag_service import RAGService
from services.question_generator import QuestionGenerator
from services.session_service import SessionService

logger = structlog.get_logger()


class ConversationService:
    """
    Service for orchestrating product investigation conversations.
    
    Manages conversation state machine, session lifecycle, and
    question generation flow.
    """
    
    # State machine order
    STATE_ORDER = [
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
    
    # Question templates by category
    QUESTION_TEMPLATES = {
        ConversationState.FUNCTIONALITY: [
            "Let's start by understanding what your product does. Can you describe the main functionality or purpose of your product idea?",
            "What specific problem does your product solve for users?",
            "What are the key features users will interact with?"
        ],
        ConversationState.USERS: [
            "Who are the primary users of your product?",
            "What is the typical user journey through your product?",
            "What roles or user types exist in your product?"
        ],
        ConversationState.DEMOGRAPHICS: [
            "What is the age range of your target audience?",
            "What geographic regions are you targeting?",
            "What is the technical proficiency level of your users?"
        ],
        ConversationState.DESIGN: [
            "Do you have specific design preferences (modern, minimal, bold, colorful)?",
            "Are there any brand colors or style guidelines to follow?",
            "Should the product work on desktop, mobile, or both?"
        ],
        ConversationState.MARKET: [
            "Who are your main competitors in this space?",
            "What is your unique value proposition compared to competitors?",
            "What is your business model or monetization strategy?"
        ],
        ConversationState.TECHNICAL: [
            "Do you have any technical stack preferences or requirements?",
            "What are your performance and scalability requirements?",
            "Do you need any specific integrations with other services?"
        ],
        ConversationState.REVIEW: [
            "Is there anything else important about your product that we haven't covered?",
            "Would you like to add or clarify any information from our conversation?"
        ]
    }
    
    def __init__(
        self,
        llm_service: LLMService,
        rag_service: Optional[RAGService] = None,
        question_generator: Optional[QuestionGenerator] = None,
        session_service: Optional[SessionService] = None
    ):
        """
        Initialize the conversation service.
        
        Args:
            llm_service: Service for LLM interactions
            rag_service: Service for RAG context retrieval (optional)
            question_generator: Service for intelligent question generation (optional)
            session_service: Service for session persistence (optional)
        """
        self.llm = llm_service
        self.rag = rag_service
        self.question_gen = question_generator
        self.session_svc = session_service
        self.sessions: Dict[str, Session] = {}
        self.messages: Dict[str, List[Message]] = {}
        self.last_save_counts: Dict[str, int] = {}  # Track interaction count at last save
        
        logger.info(
            "conversation_service_initialized",
            rag_enabled=rag_service is not None,
            question_gen_enabled=question_generator is not None,
            session_service_enabled=session_service is not None
        )
    
    def start_investigation(
        self,
        provider: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Tuple[str, Question]:
        """
        Start a new product investigation session.
        
        Creates a new session with unique ID and returns the initial question.
        
        Args:
            provider: LLM provider to use (optional, defaults to active)
            model_id: Model ID to use (optional, defaults to selected)
            
        Returns:
            Tuple of (session_id, initial_question)
        """
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create session
        session = Session(
            id=session_id,
            started_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            status="active",
            state=ConversationState.START,
            investigation_progress={},
            metadata={},
            provider=provider,
            model_id=model_id
        )
        
        # Store session
        self.sessions[session_id] = session
        self.messages[session_id] = []
        
        logger.info(
            "investigation_started",
            session_id=session_id,
            provider=provider,
            model_id=model_id
        )
        
        # Generate initial question
        initial_question = self._generate_initial_question()
        
        # Add system message to history
        self._add_message(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=initial_question.text,
            metadata={"question_id": initial_question.id, "category": initial_question.category}
        )
        
        return session_id, initial_question
    
    def _generate_initial_question(self) -> Question:
        """
        Generate the initial question to start the investigation.
        
        Returns:
            Initial question about product functionality
        """
        # Use QuestionGenerator if available
        if self.question_gen:
            question = self.question_gen.get_initial_question()
            logger.info(
                "initial_question_generated",
                question_id=question.id,
                source="question_generator"
            )
            return question
        
        # Fallback to template-based question
        question = Question(
            id=str(uuid.uuid4()),
            category=ConversationState.FUNCTIONALITY.value,
            text=self.QUESTION_TEMPLATES[ConversationState.FUNCTIONALITY][0],
            context=[],
            is_followup=False,
            timestamp=datetime.utcnow()
        )
        
        logger.info(
            "initial_question_generated",
            question_id=question.id,
            source="template"
        )
        
        return question
    
    async def process_answer(
        self,
        session_id: str,
        answer_text: str
    ) -> Optional[Question]:
        """
        Process a user's answer and generate the next question.
        
        Args:
            session_id: Session identifier
            answer_text: User's answer text
            
        Returns:
            Next question, or None if investigation is complete
            
        Raises:
            ValueError: If session not found
        """
        # Validate session exists
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        logger.info(
            "processing_answer",
            session_id=session_id,
            answer_length=len(answer_text),
            current_state=session.state.value
        )
        
        # Add user message to history
        self._add_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=answer_text,
            metadata={"state": session.state.value}
        )
        
        # Update session timestamp
        session.last_updated = datetime.utcnow()
        
        # Get the current question (last assistant message)
        current_question = None
        for msg in reversed(self.messages[session_id]):
            if msg.role == MessageRole.ASSISTANT or msg.role == MessageRole.SYSTEM:
                current_question = msg.content
                break
        
        # Persist interaction to RAG if available
        if self.rag and current_question:
            try:
                await self.rag.persist_interaction(
                    session_id=session_id,
                    question=current_question,
                    answer=answer_text
                )
                logger.info(
                    "interaction_persisted_to_rag",
                    session_id=session_id
                )
            except Exception as e:
                logger.error(
                    "rag_persistence_error",
                    error=str(e),
                    session_id=session_id
                )
        
        # Retrieve RAG context for next question generation
        context_chunks = []
        if self.rag:
            try:
                context_chunks = self.rag.retrieve_context(
                    query=answer_text,
                    session_id=session_id,
                    top_k=5
                )
                logger.info(
                    "rag_context_retrieved",
                    session_id=session_id,
                    chunks_count=len(context_chunks)
                )
            except Exception as e:
                logger.error(
                    "rag_retrieval_error",
                    error=str(e),
                    session_id=session_id
                )
        
        # Use QuestionGenerator if available, otherwise fallback to legacy method
        if self.question_gen:
            next_question = await self.question_gen.generate_next_question(
                session=session,
                latest_answer=answer_text,
                context=context_chunks if context_chunks else None
            )
            
            # Check if investigation is complete
            if next_question is None:
                session.state = ConversationState.COMPLETE
                session.status = "complete"
                logger.info("investigation_complete", session_id=session_id)
                return None
            
            # Update session state based on question
            # QuestionGenerator manages state progression internally
            
        else:
            # Legacy question generation (fallback)
            # Determine if we need a follow-up or should move to next category
            needs_followup = self._needs_followup(answer_text)
            
            if needs_followup:
                # Generate follow-up question
                next_question = await self._generate_followup_question(
                    session=session,
                    latest_answer=answer_text
                )
            else:
                # Move to next state
                next_state = self._get_next_state(session.state)
                
                if next_state == ConversationState.COMPLETE:
                    # Investigation complete
                    session.state = ConversationState.COMPLETE
                    session.status = "complete"
                    logger.info("investigation_complete", session_id=session_id)
                    return None
                
                # Update session state
                session.state = next_state
                
                # Update progress
                if next_state.value not in session.investigation_progress:
                    session.investigation_progress[next_state.value] = 0.0
                
                # Generate next category question
                next_question = self._generate_category_question(next_state)
        
        # Add assistant message to history
        self._add_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=next_question.text,
            metadata={
                "question_id": next_question.id,
                "category": next_question.category,
                "is_followup": next_question.is_followup
            }
        )
        
        logger.info(
            "next_question_generated",
            session_id=session_id,
            question_id=next_question.id,
            category=next_question.category,
            is_followup=next_question.is_followup
        )
        
        # Auto-save session if enabled
        await self._auto_save_session(session_id)
        
        return next_question
    
    def get_conversation_history(self, session_id: str) -> List[Message]:
        """
        Get the full conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of messages in chronological order
            
        Raises:
            ValueError: If session not found
        """
        if session_id not in self.messages:
            raise ValueError(f"Session {session_id} not found")
        
        return self.messages[session_id]
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session metadata.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object or None if not found
        """
        return self.sessions.get(session_id)
    
    def is_investigation_complete(self, session_id: str) -> bool:
        """
        Check if an investigation is complete.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if complete, False otherwise
        """
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        return session.state == ConversationState.COMPLETE
    
    def _add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add a message to the conversation history.
        
        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata
        """
        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        if session_id not in self.messages:
            self.messages[session_id] = []
        
        self.messages[session_id].append(message)
    
    def _needs_followup(self, answer: str) -> bool:
        """
        Determine if a follow-up question is needed.
        
        Uses simple heuristic: short answers need follow-up.
        
        Args:
            answer: User's answer text
            
        Returns:
            True if follow-up needed, False otherwise
        """
        word_count = len(answer.split())
        
        # Threshold: answers with fewer than 15 words need follow-up
        return word_count < 15
    
    async def _generate_followup_question(
        self,
        session: Session,
        latest_answer: str
    ) -> Question:
        """
        Generate a follow-up question using LLM.
        
        Args:
            session: Current session
            latest_answer: User's latest answer
            
        Returns:
            Follow-up question
        """
        # Get recent context
        recent_messages = self.messages.get(session.id, [])[-4:]  # Last 2 Q&A pairs
        context_str = "\n".join([
            f"{msg.role.value.upper()}: {msg.content}"
            for msg in recent_messages
        ])
        
        system_prompt = """You are an expert product investigator helping to gather comprehensive information about a product idea.

Generate a thoughtful follow-up question based on the user's latest answer. The question should:
- Dig deeper into their product idea
- Be specific and relevant to their answer
- Help clarify or expand on what they've said
- Be concise (one clear question)
- Be professional and encouraging

Return ONLY the question text, nothing else."""
        
        user_prompt = f"""Recent conversation:
{context_str}

The user's latest answer was brief. Generate a follow-up question to help them elaborate and provide more detail about their product."""
        
        logger.info("generating_followup_question", session_id=session.id)
        
        try:
            question_text = await self.llm.generate_response(
                system_prompt=system_prompt,
                user_message=user_prompt
            )
            
            # Clean up the response
            question_text = question_text.strip().strip('"').strip("'")
            
        except Exception as e:
            logger.error(
                "followup_generation_error",
                error=str(e),
                session_id=session.id
            )
            # Fallback to template-based question
            question_text = "Could you tell me more about that?"
        
        return Question(
            id=str(uuid.uuid4()),
            category=session.state.value,
            text=question_text,
            context=[latest_answer],
            is_followup=True,
            timestamp=datetime.utcnow()
        )
    
    def _generate_category_question(self, state: ConversationState) -> Question:
        """
        Generate a question for a specific category using templates.
        
        Args:
            state: Conversation state/category
            
        Returns:
            Category question
        """
        templates = self.QUESTION_TEMPLATES.get(state, [])
        
        if not templates:
            question_text = "Tell me more about your product."
        else:
            # For now, use the first template (can be randomized or rotated)
            question_text = templates[0]
        
        return Question(
            id=str(uuid.uuid4()),
            category=state.value,
            text=question_text,
            context=[],
            is_followup=False,
            timestamp=datetime.utcnow()
        )
    
    def _get_next_state(self, current_state: ConversationState) -> ConversationState:
        """
        Get the next state in the conversation flow.
        
        Args:
            current_state: Current conversation state
            
        Returns:
            Next conversation state
        """
        try:
            current_idx = self.STATE_ORDER.index(current_state)
            if current_idx + 1 < len(self.STATE_ORDER):
                return self.STATE_ORDER[current_idx + 1]
        except ValueError:
            logger.warning(
                "invalid_state",
                current_state=current_state.value
            )
        
        return ConversationState.COMPLETE
    
    async def skip_current_question(self, session_id: str) -> Optional[Question]:
        """
        Skip the current question and move to the next category.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Next question, or None if investigation is complete
            
        Raises:
            ValueError: If session not found
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        # Get current question ID from last message
        current_question_id = None
        for msg in reversed(self.messages[session_id]):
            if msg.role in (MessageRole.ASSISTANT, MessageRole.SYSTEM):
                current_question_id = msg.metadata.get('question_id')
                break
        
        # Track skipped question
        if current_question_id:
            session.skipped_questions.append(current_question_id)
        
        logger.info(
            "question_skipped",
            session_id=session_id,
            question_id=current_question_id,
            current_state=session.state.value
        )
        
        # Move to next state
        next_state = self._get_next_state(session.state)
        
        if next_state == ConversationState.COMPLETE:
            session.state = ConversationState.COMPLETE
            session.status = "complete"
            logger.info("investigation_complete_after_skip", session_id=session_id)
            return None
        
        # Update session state
        session.state = next_state
        session.last_updated = datetime.utcnow()
        
        # Generate next category question
        if self.question_gen:
            # Use question generator
            next_question = await self.question_gen.generate_next_question(
                session=session,
                latest_answer="[SKIPPED]",
                context=[]
            )
            
            # Check if investigation is complete
            if next_question is None:
                session.state = ConversationState.COMPLETE
                session.status = "complete"
                logger.info("investigation_complete_from_question_gen", session_id=session_id)
                return None
        else:
            # Fallback to template-based question
            next_question = self._generate_category_question(next_state)
        
        # Add message to history
        self._add_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=next_question.text,
            metadata={
                "question_id": next_question.id,
                "category": next_question.category,
                "is_followup": next_question.is_followup,
                "previous_skipped": True
            }
        )
        
        logger.info(
            "next_question_after_skip",
            session_id=session_id,
            question_id=next_question.id,
            new_state=session.state.value
        )
        
        return next_question
    
    async def edit_previous_answer(
        self,
        session_id: str,
        message_id: str,
        new_answer: str
    ) -> bool:
        """
        Edit a previous answer and update RAG context.
        
        Note: This updates the RAG context but does not regenerate subsequent questions.
        For full conversation regeneration, that would require additional logic.
        
        Args:
            session_id: Session identifier
            message_id: Message ID of the answer to edit
            new_answer: New answer text
            
        Returns:
            True if edit successful, False if message not found
            
        Raises:
            ValueError: If session not found
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        messages = self.messages.get(session_id, [])
        
        # Find the message to edit
        message_found = False
        old_answer = None
        corresponding_question = None
        
        for i, msg in enumerate(messages):
            if msg.id == message_id and msg.role == MessageRole.USER:
                old_answer = msg.content
                msg.content = new_answer
                msg.metadata['edited'] = True
                msg.metadata['edited_at'] = datetime.utcnow().isoformat()
                message_found = True
                
                # Find the corresponding question (previous assistant/system message)
                for j in range(i - 1, -1, -1):
                    if messages[j].role in (MessageRole.ASSISTANT, MessageRole.SYSTEM):
                        corresponding_question = messages[j].content
                        break
                
                break
        
        if not message_found:
            logger.warning(
                "message_not_found_for_edit",
                session_id=session_id,
                message_id=message_id
            )
            return False
        
        # Update RAG context if available
        if self.rag and corresponding_question and old_answer:
            try:
                success = await self.rag.update_interaction(
                    session_id=session_id,
                    question=corresponding_question,
                    old_answer=old_answer,
                    new_answer=new_answer,
                    metadata={"edited_message_id": message_id}
                )
                
                logger.info(
                    "answer_edited_rag_updated",
                    session_id=session_id,
                    message_id=message_id,
                    rag_updated=success
                )
            except Exception as e:
                logger.error(
                    "rag_update_error_during_edit",
                    error=str(e),
                    session_id=session_id,
                    message_id=message_id
                )
        else:
            logger.info(
                "answer_edited_no_rag",
                session_id=session_id,
                message_id=message_id,
                rag_available=self.rag is not None,
                question_found=corresponding_question is not None
            )
        
        # Update session timestamp
        session.last_updated = datetime.utcnow()
        
        return True
    
    async def _auto_save_session(self, session_id: str):
        """
        Auto-save session if threshold reached.
        
        Saves session every 5 Q&A interactions automatically.
        
        Args:
            session_id: Session identifier
        """
        if not self.session_svc:
            # Session service not enabled
            return
        
        # Calculate interaction count (user messages only, since each user message is an answer)
        messages = self.messages.get(session_id, [])
        user_message_count = len([msg for msg in messages if msg.role == MessageRole.USER])
        
        # Get last save count for this session
        last_save_count = self.last_save_counts.get(session_id, 0)
        
        # Check if auto-save should trigger
        if self.session_svc.should_auto_save(user_message_count, last_save_count, auto_save_interval=5):
            session = self.sessions.get(session_id)
            if session:
                success = await self.session_svc.save_session(session, messages)
                if success:
                    self.last_save_counts[session_id] = user_message_count
                    logger.info(
                        "session_auto_saved",
                        session_id=session_id,
                        interaction_count=user_message_count
                    )
    
    async def manual_save_session(self, session_id: str) -> bool:
        """
        Manually save session.
        
        Allows user to explicitly save their session at any point.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if saved successfully, False otherwise
            
        Raises:
            ValueError: If session not found
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        if not self.session_svc:
            logger.warning(
                "manual_save_failed_no_service",
                session_id=session_id
            )
            return False
        
        session = self.sessions[session_id]
        messages = self.messages.get(session_id, [])
        
        success = await self.session_svc.save_session(session, messages)
        
        if success:
            # Update last save count
            user_message_count = len([msg for msg in messages if msg.role == MessageRole.USER])
            self.last_save_counts[session_id] = user_message_count
            
            logger.info(
                "session_manually_saved",
                session_id=session_id
            )
        
        return success
    
    async def load_saved_session(self, session_id: str) -> bool:
        """
        Load a previously saved session.
        
        Restores full conversation context from saved session file.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.session_svc:
            logger.warning("load_session_failed_no_service", session_id=session_id)
            return False
        
        result = await self.session_svc.load_session(session_id)
        
        if result is None:
            logger.warning("session_not_found_for_load", session_id=session_id)
            return False
        
        session, messages = result
        
        # Restore session and messages to in-memory storage
        self.sessions[session_id] = session
        self.messages[session_id] = messages
        
        # Set last save count
        user_message_count = len([msg for msg in messages if msg.role == MessageRole.USER])
        self.last_save_counts[session_id] = user_message_count
        
        logger.info(
            "session_loaded",
            session_id=session_id,
            message_count=len(messages),
            interaction_count=user_message_count,
            state=session.state.value
        )
        
        return True


# Singleton instance
_conversation_service_instance: Optional[ConversationService] = None


# Dependency injection helper
def get_conversation_service() -> ConversationService:
    """
    Dependency injection helper for FastAPI routes.
    Returns a singleton instance to persist sessions in memory.
    
    Returns:
        ConversationService singleton instance
    """
    global _conversation_service_instance
    
    if _conversation_service_instance is None:
        from services.llm_service import get_llm_service
        from services.rag_service import get_rag_service
        from services.question_generator import get_question_generator
        from storage.conversation_storage import ConversationStorage
        
        llm_service = get_llm_service()
        
        # Initialize storage for RAG
        storage = ConversationStorage(base_dir="./data/conversations")
        rag_service = get_rag_service(storage=storage)
        
        question_generator = get_question_generator(llm_service=llm_service)
        
        # Initialize session service
        session_service = SessionService(base_dir="./data/sessions")
        
        _conversation_service_instance = ConversationService(
            llm_service=llm_service,
            rag_service=rag_service,
            question_generator=question_generator,
            session_service=session_service
        )
        logger.info("conversation_service_singleton_created")
    
    return _conversation_service_instance
