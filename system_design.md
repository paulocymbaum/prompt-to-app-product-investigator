# Product Investigator Chatbot - System Design Document

## 1. Executive Summary

This document outlines the system design for a conversational AI chatbot that investigates product ideas through intelligent questioning and generates comprehensive development prompts. The system uses LangChain for LLM orchestration, implements RAG for conversation memory, and provides LangGraph visualization for conversation flow analysis.

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Chat UI      │  │ Config Panel │  │ Graph Viewer │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API / WebSocket
┌────────────────────────┴────────────────────────────────────┐
│                      Backend Layer                           │
│  ┌──────────────────────────────────────────────────┐       │
│  │              API Gateway / Routes                 │       │
│  └───────┬──────────────────────────────────┬───────┘       │
│          │                                   │               │
│  ┌───────▼────────┐                 ┌───────▼────────┐      │
│  │ Conversation    │                 │ Configuration  │      │
│  │ Service         │                 │ Service        │      │
│  └───────┬────────┘                 └───────┬────────┘      │
│          │                                   │               │
│  ┌───────▼────────┐  ┌──────────┐  ┌───────▼────────┐      │
│  │ RAG Service    │  │ Prompt   │  │ Model Checker  │      │
│  │ (Memory)       │  │Generator │  │ Service        │      │
│  └───────┬────────┘  └─────┬────┘  └───────┬────────┘      │
│          │                  │                │               │
│  ┌───────▼──────────────────▼────────────────▼────────┐     │
│  │           LangChain Integration Layer              │     │
│  └───────┬────────────────────────────────────────────┘     │
│          │                                                   │
│  ┌───────▼────────┐                                         │
│  │ LangGraph      │                                         │
│  │ Visualization  │                                         │
│  └────────────────┘                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                   External Services                          │
│  ┌──────────────┐              ┌──────────────┐             │
│  │ Groq Cloud   │              │ OpenAI API   │             │
│  │ API          │              │              │             │
│  └──────────────┘              └──────────────┘             │
└─────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                    Storage Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Conversation │  │ Config       │  │ Session      │      │
│  │ Markdown     │  │ Storage      │  │ State        │      │
│  │ Files        │  │ (.env)       │  │ (JSON)       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Component Design

### 3.1 Backend Components

#### 3.1.1 API Gateway (`app.py`)
**Purpose:** Central entry point for all API requests

**Responsibilities:**
- Route requests to appropriate services
- Handle CORS and security headers
- Implement rate limiting
- WebSocket management for real-time chat
- Error handling and logging

**Technology Stack:**
- FastAPI for REST endpoints
- WebSocket support for streaming responses
- Pydantic for request/response validation

**Key Endpoints:**
```
POST   /api/chat/start                 # Start new investigation
POST   /api/chat/message               # Send user message
GET    /api/chat/history/:sessionId    # Get conversation history
POST   /api/config/token               # Set API token
GET    /api/config/models              # List available models
POST   /api/config/model/select        # Select model
GET    /api/prompt/generate            # Generate final prompt
GET    /api/graph/visualization        # Get LangGraph data
POST   /api/session/save               # Save session
GET    /api/session/load/:sessionId    # Load session
```

---

#### 3.1.2 LLM Service (`services/llm_service.py`)
**Purpose:** Manage LLM provider interactions

**Responsibilities:**
- Initialize LangChain LLM instances
- Route requests to Groq or OpenAI
- Handle streaming responses
- Manage token counting and limits
- Implement retry logic for failed calls

**Key Classes:**
```python
class LLMService:
    - initialize_provider(provider: str, api_key: str)
    - get_available_models() -> List[Model]
    - generate_response(prompt: str, context: List[str]) -> str
    - stream_response(prompt: str, context: List[str]) -> Iterator[str]
    - count_tokens(text: str) -> int
```

**LangChain Integration:**
- Use `ChatGroq` for Groq Cloud
- Use `ChatOpenAI` for OpenAI
- Implement `BaseChatModel` interface
- Configure temperature, max_tokens, etc.

---

#### 3.1.3 Conversation Service (`services/conversation_service.py`)
**Purpose:** Orchestrate the investigation conversation flow

**Responsibilities:**
- Manage conversation state machine
- Generate contextual questions
- Determine when investigation is complete
- Coordinate between LLM and RAG services
- Track question categories (functionality, users, design, market, technical)

**Key Classes:**
```python
class ConversationService:
    - start_investigation(session_id: str) -> Question
    - process_answer(answer: str, session_id: str) -> Question
    - is_investigation_complete(session_id: str) -> bool
    - get_conversation_summary(session_id: str) -> Summary
    
class QuestionGenerator:
    - generate_initial_question() -> Question
    - generate_followup(context: List[Chunk], category: str) -> Question
    - adapt_question_based_on_answers(answers: List[Answer]) -> Question
```

**State Machine:**
```
START → FUNCTIONALITY → USERS → DEMOGRAPHICS → 
DESIGN → MARKET → TECHNICAL → REVIEW → COMPLETE
```

---

#### 3.1.4 RAG Service (`services/rag_service.py`)
**Purpose:** Implement conversation memory using RAG

**Responsibilities:**
- Persist conversations to markdown
- Chunk conversations using "-----" delimiter
- Embed chunks using sentence transformers
- Retrieve 2-5 most relevant chunks
- Maintain vector store for fast retrieval

**Key Classes:**
```python
class RAGService:
    - save_interaction(question: str, answer: str, session_id: str)
    - retrieve_context(query: str, session_id: str, k: int = 5) -> List[Chunk]
    - get_recent_chunks(session_id: str, n: int = 3) -> List[Chunk]
    - embed_text(text: str) -> List[float]
    
class MarkdownHandler:
    - write_interaction(filepath: str, question: str, answer: str)
    - read_conversation(filepath: str) -> List[Chunk]
    - parse_chunks(content: str) -> List[Chunk]
```

**Storage Format:**
```markdown
## Session: {session_id}
Started: {timestamp}

### Interaction 1
**Question:** {question text}
**Answer:** {answer text}
**Timestamp:** {timestamp}

-----

### Interaction 2
...
```

**Vector Store:**
- Use FAISS for local vector storage (MVP)
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- Similarity metric: Cosine similarity
- Cache embeddings for performance

---

#### 3.1.5 Prompt Generator Service (`services/prompt_generator.py`)
**Purpose:** Generate comprehensive development prompts

**Responsibilities:**
- Aggregate all investigation answers
- Structure prompt using best practices
- Include SOLID and DRY requirements
- Format for clarity and usability
- Validate prompt completeness

**Key Classes:**
```python
class PromptGenerator:
    - generate_prompt(session_id: str) -> Prompt
    - structure_prompt(answers: Dict) -> str
    - add_engineering_principles(prompt: str) -> str
    - validate_prompt(prompt: str) -> bool
    
class PromptTemplate:
    - system_role: str
    - context_template: str
    - requirements_template: str
    - constraints_template: str
    - output_format_template: str
```

**Prompt Structure:**
```
# Product Development Prompt

## Role
You are an expert software architect and developer...

## Product Context
[Aggregated product information]

## Functional Requirements
[Derived from conversation]

## Technical Requirements
- Follow SOLID principles:
  - Single Responsibility Principle
  - Open/Closed Principle
  - ...
- Apply DRY (Don't Repeat Yourself)
- Prioritize maintainability
- Organize code into clear modules

## Architecture Guidelines
[Based on product complexity]

## User Requirements
[Target audience, demographics]

## Design Requirements
[UI/UX preferences]

## Output Format
[Expected deliverables]
```

---

#### 3.1.6 Model Checker Service (`utils/model_checker.py`)
**Purpose:** Verify and list available LLM models

**Responsibilities:**
- Call provider API to list models
- Test model availability
- Cache model lists
- Provide model metadata

**Key Functions:**
```python
async def check_groq_models(api_key: str) -> List[Model]
async def check_openai_models(api_key: str) -> List[Model]
def get_model_info(model_id: str, provider: str) -> ModelInfo
```

---

#### 3.1.7 LangGraph Builder (`langraph/graph_builder.py`)
**Purpose:** Create visual representation of conversation flow

**Responsibilities:**
- Build conversation graph from history
- Identify decision points and branches
- Export graph in LangGraph format
- Generate visualization data

**Key Classes:**
```python
class GraphBuilder:
    - build_graph(session_id: str) -> Graph
    - add_node(interaction: Interaction) -> Node
    - add_edge(from_node: Node, to_node: Node, label: str)
    - export_graph(format: str) -> str
    
class GraphNode:
    id: str
    type: str  # question, answer, decision
    content: str
    metadata: Dict
    
class GraphEdge:
    source: str
    target: str
    label: str
    weight: float
```

**LangGraph Integration:**
- Use `StateGraph` from LangGraph
- Define conversation states
- Implement conditional edges for branching
- Export to Mermaid diagram format

---

### 3.2 Frontend Components

#### 3.2.1 Chat Interface (`frontend/src/components/ChatInterface.jsx`)
**Features:**
- Message display (user/system)
- Input field with submit button
- Typing indicators
- Streaming response display
- Markdown rendering for formatted text
- Scroll to latest message
- Edit previous responses

**State Management:**
- Current conversation
- Message history
- Loading states
- WebSocket connection status

---

#### 3.2.2 Configuration Panel (`frontend/src/components/ConfigPanel.jsx`)
**Features:**
- API token input (masked)
- Provider selection (Groq/OpenAI)
- Model list display
- Model selection dropdown
- Test connection button
- Save configuration

**Validation:**
- Token format validation
- Real-time connection testing
- Error display for failed configurations

---

#### 3.2.3 Prompt Display (`frontend/src/components/PromptDisplay.jsx`)
**Features:**
- Generated prompt display
- Syntax highlighting
- Copy to clipboard button
- Download as file
- Regeneration request
- Version comparison

---

#### 3.2.4 Graph Viewer
**Features:**
- Interactive graph visualization
- Zoom and pan controls
- Node click for details
- Edge hover for labels
- Export graph as image/HTML
- Filter by category

**Library:** React Flow or D3.js

---

## 4. Data Models

### 4.1 Core Models

```python
# models/conversation.py

class Message:
    id: str
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Dict

class Question:
    id: str
    category: str
    text: str
    context: List[str]
    is_followup: bool

class Answer:
    question_id: str
    text: str
    timestamp: datetime
    confidence: float

class Session:
    id: str
    started_at: datetime
    last_updated: datetime
    status: str  # "active", "complete", "paused"
    investigation_progress: Dict
    metadata: Dict

class Chunk:
    id: str
    content: str
    embedding: List[float]
    session_id: str
    timestamp: datetime
    category: str
```

```python
# models/provider.py

class Provider:
    name: str  # "groq" or "openai"
    api_key: str
    base_url: str

class Model:
    id: str
    name: str
    provider: str
    context_window: int
    capabilities: List[str]
    cost_per_token: float

class Prompt:
    id: str
    session_id: str
    content: str
    version: int
    generated_at: datetime
    metadata: Dict
```

---

## 5. Data Flow

### 5.1 Investigation Flow

```
1. User starts investigation
   → Frontend: POST /api/chat/start
   → Backend: ConversationService.start_investigation()
   → Response: Initial question

2. User submits answer
   → Frontend: POST /api/chat/message
   → Backend: ConversationService.process_answer()
   → RAGService.save_interaction() (persist to markdown)
   → RAGService.retrieve_context() (get relevant history)
   → LLMService.generate_response() (create follow-up)
   → Response: Next question + context

3. Repeat step 2 until complete

4. Investigation complete
   → Backend: PromptGenerator.generate_prompt()
   → Aggregate all answers
   → Structure with best practices
   → Response: Comprehensive prompt

5. User views graph
   → Frontend: GET /api/graph/visualization
   → Backend: GraphBuilder.build_graph()
   → Response: Graph data (nodes, edges)
```

### 5.2 Configuration Flow

```
1. User inputs API token
   → Frontend: POST /api/config/token
   → Backend: Validate and store (encrypted)
   → Response: Success/failure

2. Fetch available models
   → Frontend: GET /api/config/models
   → Backend: ModelChecker.check_models()
   → Call provider API
   → Response: List of models

3. User selects model
   → Frontend: POST /api/config/model/select
   → Backend: Update configuration
   → Initialize LLM with selected model
   → Response: Confirmation
```

---

## 6. Technology Stack

### 6.1 Backend
- **Language:** Python 3.9+
- **Framework:** FastAPI
- **LLM Orchestration:** LangChain
- **Graph Visualization:** LangGraph
- **Vector Store:** FAISS (MVP), Pinecone (future)
- **Embeddings:** sentence-transformers
- **Async:** asyncio, httpx
- **Testing:** pytest, pytest-asyncio

### 6.2 Frontend
- **Framework:** React 18+ with Vite
- **State Management:** React Context API or Zustand
- **HTTP Client:** Axios
- **WebSocket:** native WebSocket API
- **UI Components:** Tailwind CSS + shadcn/ui
- **Markdown:** react-markdown
- **Graph Visualization:** React Flow

### 6.3 DevOps
- **Container:** Docker + Docker Compose
- **Environment:** python-dotenv for config
- **Logging:** structlog
- **Monitoring:** Basic logging (future: Prometheus)

---

## 7. Security Considerations

### 7.1 API Token Security
- Store tokens encrypted using `cryptography` library
- Never log tokens
- Use environment variables for storage
- Implement token rotation capability

### 7.2 Input Validation
- Sanitize all user inputs
- Validate message lengths
- Prevent prompt injection attacks
- Rate limit API calls

### 7.3 Session Security
- Generate secure session IDs (UUID4)
- Implement session timeouts
- Isolate sessions (no cross-session data leakage)
- Clear sensitive data on logout

---

## 8. Scalability Strategy

### 8.1 MVP (File-based)
- Markdown files for conversations
- Local FAISS vector store
- Single-instance deployment
- Suitable for <100 concurrent users

### 8.2 Future Scale
- Replace file storage with PostgreSQL
- Use Pinecone/Weaviate for vector storage
- Implement Redis for caching
- Horizontal scaling with load balancer
- Microservices architecture

---

## 9. Error Handling

### 9.1 LLM API Failures
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def call_llm_with_retry(prompt: str) -> str:
    # Implementation with retry logic
```

### 9.2 RAG Retrieval Failures
- Fallback to recent interactions if vector search fails
- Graceful degradation without full context

### 9.3 Storage Failures
- Auto-save conversations every N interactions
- Local browser cache as backup
- User notification for save failures

---

## 10. Performance Optimization

### 10.1 Response Time
- Stream LLM responses for perceived speed
- Cache frequent queries
- Preload next question while user types
- Async processing where possible

### 10.2 RAG Optimization
- Index embeddings for fast retrieval
- Batch embed multiple chunks
- Cache embeddings for unchanged text
- Limit context window to most relevant chunks

### 10.3 Frontend Optimization
- Lazy load graph visualization
- Virtual scrolling for long conversations
- Debounce user inputs
- Code splitting for faster initial load

---

## 11. Testing Strategy

### 11.1 Unit Tests
- Test each service independently
- Mock external API calls
- Test prompt generation logic
- Test RAG chunking and retrieval

### 11.2 Integration Tests
- Test full conversation flow
- Test provider switching
- Test session persistence
- Test graph generation

### 11.3 End-to-End Tests
- Test complete user journey
- Test with real LLM APIs (staging keys)
- Test edge cases (very long conversations, special characters)

---

## 12. Deployment Plan

### 12.1 Development Environment
```bash
# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### 12.2 Production Deployment
```bash
# Docker Compose
docker-compose up -d

# Or separate containers
docker build -t chatbot-backend ./backend
docker build -t chatbot-frontend ./frontend
docker run -p 8000:8000 chatbot-backend
docker run -p 3000:3000 chatbot-frontend
```

### 12.3 Environment Variables
```
# .env
GROQ_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
SECRET_KEY=encryption-key
DATABASE_URL=file://./data/conversations
VECTOR_STORE_PATH=./data/vectors
LOG_LEVEL=INFO
```

---

## 13. Monitoring and Logging

### 13.1 Key Metrics
- API response times
- LLM token usage
- Error rates by endpoint
- Session completion rates
- Average investigation time

### 13.2 Logging
```python
import structlog

logger = structlog.get_logger()

logger.info("conversation_started", session_id=session_id)
logger.error("llm_call_failed", error=str(e), provider=provider)
```

---

## 14. Future Enhancements

### Phase 2 (Post-MVP)
- Database integration (PostgreSQL)
- User authentication and multi-tenancy
- Conversation templates for common product types
- Advanced RAG with hybrid search
- Prompt optimization using A/B testing

### Phase 3
- Multi-language support
- Voice input/output
- Collaborative investigations (team mode)
- Integration with project management tools
- AI-powered code generation from prompts

---

## 15. Success Criteria

### MVP Completion Checklist
- [ ] User can configure Groq or OpenAI tokens
- [ ] System lists and allows model selection
- [ ] User can complete full investigation (8-12 questions)
- [ ] Conversations persist to markdown with "-----" separators
- [ ] RAG retrieves 2-5 relevant chunks for context
- [ ] Generated prompts include SOLID/DRY requirements
- [ ] LangGraph visualization displays conversation flow
- [ ] Frontend provides clean chat interface
- [ ] Sessions can be saved and loaded
- [ ] End-to-end conversation completes in <15 minutes

---

## 16. Appendix

### 16.1 Sample Questions by Category

**Functionality:**
- What problem does your product solve?
- What are the core features?
- What actions can users perform?

**Users:**
- Who is your target audience?
- What user roles exist?
- What's the typical user journey?

**Demographics:**
- What age group are you targeting?
- Geographic considerations?
- Technical proficiency level?

**Design:**
- What design style do you envision?
- Any brand colors or guidelines?
- Desktop, mobile, or both?

**Market:**
- Who are your competitors?
- What's your unique value proposition?
- What's your business model?

**Technical:**
- Any specific technology preferences?
- Performance requirements?
- Integration needs?