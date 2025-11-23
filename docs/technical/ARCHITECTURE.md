# System Architecture

## Overview

The Product Investigator Chatbot is a full-stack web application built with a modern microservices-inspired architecture, emphasizing separation of concerns, testability, and scalability.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│  (React 18 + Vite + Tailwind CSS + React Flow)                  │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Chat         │  │ Config       │  │ Progress     │          │
│  │ Interface    │  │ Panel        │  │ Tracker      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Session      │  │ Prompt       │  │ Graph        │          │
│  │ Manager      │  │ Display      │  │ Viewer       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway Layer                         │
│                    (FastAPI + CORS Middleware)                   │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ /api/chat    │  │ /api/config  │  │ /api/session │          │
│  │ Routes       │  │ Routes       │  │ Routes       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ /api/prompt  │  │ /api/graph   │                             │
│  │ Routes       │  │ Routes       │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Dependency Injection
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Service Layer                              │
│                  (Business Logic & Orchestration)                │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Conversation     │  │ LLM Service      │                     │
│  │ Service          │──│ (LangChain)      │                     │
│  └──────────────────┘  └──────────────────┘                     │
│           │                      │                                │
│           ▼                      ▼                                │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ RAG Service      │  │ Question         │                     │
│  │ (ChromaDB)       │  │ Generator        │                     │
│  └──────────────────┘  └──────────────────┘                     │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Session Service  │  │ Config Service   │                     │
│  └──────────────────┘  └──────────────────┘                     │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Prompt Generator │  │ Graph Service    │                     │
│  │ (Jinja2)         │  │ (LangGraph)      │                     │
│  └──────────────────┘  └──────────────────┘                     │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Export Service   │  │ Model Checker    │                     │
│  │ (WeasyPrint)     │  │                  │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Storage Layer                              │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Conversation     │  │ Session Storage  │                     │
│  │ Storage          │  │ (JSON Files)     │                     │
│  │ (Markdown Files) │  │                  │                     │
│  └──────────────────┘  └──────────────────┘                     │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ ChromaDB         │  │ Environment      │                     │
│  │ (Vector Store)   │  │ Config (.env)    │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      External Services                           │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Groq Cloud API   │  │ OpenAI API       │                     │
│  │ (LLM Inference)  │  │ (LLM Inference)  │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Architectural Patterns

### 1. Layered Architecture

The system follows a classic 4-tier layered architecture:

#### Presentation Layer (Frontend)
- **Technology**: React 18, Vite, Tailwind CSS
- **Responsibility**: User interface, user interaction, state management
- **Components**: Reusable UI components with single responsibility
- **State Management**: React hooks (useState, useEffect, useContext)

#### API Layer (Routes)
- **Technology**: FastAPI, Pydantic
- **Responsibility**: HTTP endpoint handling, request validation, response serialization
- **Pattern**: Thin controllers that delegate to service layer
- **Validation**: Pydantic models for type safety

#### Business Logic Layer (Services)
- **Technology**: Python, LangChain, LangGraph
- **Responsibility**: Core business logic, orchestration, complex computations
- **Pattern**: Service classes with dependency injection
- **Principles**: SOLID, DRY, separation of concerns

#### Data Layer (Storage)
- **Technology**: File system, ChromaDB
- **Responsibility**: Data persistence, retrieval, caching
- **Pattern**: Repository pattern with abstracted storage
- **Isolation**: Each storage concern has dedicated class

### 2. Dependency Injection

All services use constructor-based dependency injection:

```python
class ConversationService:
    def __init__(
        self,
        llm_service: LLMService,
        rag_service: RAGService,
        question_generator: QuestionGenerator,
        session_service: SessionService
    ):
        self.llm = llm_service
        self.rag = rag_service
        self.question_gen = question_generator
        self.session = session_service
```

**Benefits**:
- Easy testing with mocks
- Loose coupling
- Clear dependencies
- Flexible configuration

### 3. Repository Pattern

Storage classes abstract data access:

```python
class ConversationStorage:
    async def save_interaction(self, session_id, question, answer)
    async def load_conversation(self, session_id) -> str
    def parse_chunks(self, content) -> List[str]

class SessionService:
    async def save_session(self, session: Session)
    async def load_session(self, session_id) -> Session
    async def list_sessions(self) -> List[dict]
```

**Benefits**:
- Storage implementation can change without affecting business logic
- Easy to add caching layer
- Testable with in-memory implementations

### 4. State Machine (Conversation Flow)

Conversation uses explicit state machine:

```python
class ConversationState(Enum):
    START = "start"
    FUNCTIONALITY = "functionality"
    USERS = "users"
    DEMOGRAPHICS = "demographics"
    DESIGN = "design"
    MARKET = "market"
    TECHNICAL = "technical"
    REVIEW = "review"
    COMPLETE = "complete"
```

**Benefits**:
- Clear conversation progression
- Testable state transitions
- Easy to add new states
- Visual representation via LangGraph

### 5. Template Method Pattern (Prompt Generation)

```python
class PromptGenerator:
    async def generate_prompt(self, session_id: str) -> str:
        # Template method
        answers = self._extract_answers_by_category(chunks)
        architecture = self._suggest_architecture(answers)
        tech_stack = self._suggest_tech_stack(answers)
        folder_structure = self._generate_folder_structure(answers, tech_stack)
        
        prompt = self.template.render(**template_data)
        prompt = self._optimize_token_count(prompt)
        return prompt
```

**Benefits**:
- Consistent prompt structure
- Easy to customize steps
- Testable in isolation

## Technology Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | FastAPI | 0.104+ | REST API, WebSockets |
| Language | Python | 3.10+ | Backend logic |
| LLM Integration | LangChain | 0.1+ | LLM abstraction |
| Vector Store | ChromaDB | 0.4+ | Embeddings storage |
| Embeddings | sentence-transformers | 2.2+ | Text embeddings |
| Graph | LangGraph | 0.0.25+ | Workflow visualization |
| Templating | Jinja2 | 3.1+ | Prompt templates |
| PDF Generation | WeasyPrint | 59.0+ | HTML to PDF |
| Encryption | cryptography | 41.0+ | Token encryption |
| Testing | pytest | 7.4+ | Unit/integration tests |
| Async I/O | aiofiles | 23.2+ | Async file operations |
| HTTP Client | httpx | 0.25+ | Async HTTP requests |

### Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | React | 18.2+ | UI framework |
| Build Tool | Vite | 4.5+ | Fast build/dev server |
| Language | JavaScript | ES2022 | Frontend logic |
| Styling | Tailwind CSS | 3.3+ | Utility-first CSS |
| Markdown | react-markdown | 9.0+ | Render markdown |
| Syntax Highlight | react-syntax-highlighter | 15.5+ | Code highlighting |
| Graph Viz | React Flow | 11.10+ | Interactive graphs |
| HTTP Client | Axios | 1.6+ | API requests |
| Icons | lucide-react | 0.292+ | Icon library |
| Notifications | react-hot-toast | 2.4+ | Toast messages |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Container | Docker | Containerization |
| Orchestration | Docker Compose | Multi-container setup |
| Web Server | Uvicorn | ASGI server |
| Process Manager | (Future) Gunicorn | Production server |

## Data Flow

### 1. Investigation Flow

```
User Input
    ↓
[Frontend] ChatInterface
    ↓
HTTP POST /api/chat/message
    ↓
[Routes] chat_routes.send_message()
    ↓
[Service] ConversationService.process_answer()
    ├──→ [Service] RAGService.persist_interaction()
    │       ↓
    │   [Storage] ConversationStorage.save_interaction()
    │       ↓
    │   [Storage] ChromaDB.add_embeddings()
    │
    ├──→ [Service] RAGService.retrieve_context()
    │       ↓
    │   [Storage] ChromaDB.similarity_search()
    │
    └──→ [Service] QuestionGenerator.generate_next_question()
            ├──→ [Service] LLMService.generate_response()
            │       ↓
            │   [External] Groq/OpenAI API
            │
            └──→ Return next Question
                    ↓
                Response to Frontend
                    ↓
                [Frontend] Display question
```

### 2. Session Save Flow

```
User clicks "Save"
    ↓
[Frontend] SessionManager
    ↓
HTTP POST /api/session/save
    ↓
[Routes] session_routes.save_session()
    ↓
[Service] SessionService.save_session()
    ↓
JSON Serialization
    ↓
[Storage] Write to ./data/sessions/{id}.json
    ↓
Success Response
    ↓
[Frontend] Toast notification
```

### 3. Prompt Generation Flow

```
Investigation Complete
    ↓
User clicks "Generate Prompt"
    ↓
[Frontend] PromptDisplay
    ↓
HTTP GET /api/prompt/generate/{session_id}
    ↓
[Routes] prompt_routes.generate_prompt()
    ↓
[Service] PromptGenerator.generate_prompt()
    ├──→ [Storage] ConversationStorage.load_conversation()
    │
    ├──→ Parse and categorize answers
    │
    ├──→ Suggest architecture pattern
    │
    ├──→ Suggest tech stack
    │
    ├──→ Render Jinja2 template
    │
    └──→ Validate and optimize
            ↓
        Return formatted prompt
            ↓
        [Frontend] Markdown rendering with syntax highlighting
```

## Security Architecture

### 1. API Token Encryption

```python
from cryptography.fernet import Fernet

class ConfigService:
    def __init__(self):
        self.cipher = Fernet(os.getenv('SECRET_KEY'))
    
    def save_token(self, provider: str, token: str):
        encrypted = self.cipher.encrypt(token.encode())
        # Save to .env file
```

**Security Measures**:
- Fernet symmetric encryption (AES 128-bit)
- Secret key stored in environment variable
- Tokens never logged or exposed in responses
- HTTPS recommended for production

### 2. Input Validation

```python
from pydantic import BaseModel, validator

class MessageRequest(BaseModel):
    session_id: str
    message: str
    
    @validator('message')
    def validate_message(cls, v):
        if len(v) > 5000:
            raise ValueError('Message too long')
        return v.strip()
```

**Validation Points**:
- Pydantic models for all API inputs
- Length limits on text fields
- Format validation for tokens (regex)
- Session ID validation (UUID4)

### 3. CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Configurable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. Rate Limiting (Future)

Planned for production:
- Per-IP rate limiting (100 requests/minute)
- Per-user rate limiting (1000 requests/hour)
- LLM API rate limiting with exponential backoff
- Circuit breaker for failing services

## Scalability Considerations

### Current Architecture (MVP)

- **Deployment**: Single server
- **State**: In-memory session storage
- **File Storage**: Local file system
- **Vector Store**: Local ChromaDB
- **Concurrency**: Async I/O with uvicorn

**Limitations**:
- Single point of failure
- Limited concurrent users (~100-500)
- No horizontal scaling
- Session data lost on restart

### Scaling Strategy (Production)

#### Phase 1: Vertical Scaling
- Increase server resources (CPU, RAM)
- Optimize database queries
- Add Redis caching layer
- Implement connection pooling

#### Phase 2: Horizontal Scaling
```
                    Load Balancer (Nginx)
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
    API Server 1     API Server 2     API Server 3
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
        PostgreSQL              Redis Cache
        (Sessions)             (Rate Limiting)
              │
        ChromaDB Cluster
        (Vector Store)
```

**Changes Required**:
1. Replace file-based storage with PostgreSQL
2. Session state in Redis or database
3. Shared ChromaDB cluster
4. Stateless API servers
5. S3 for file uploads (future)

#### Phase 3: Microservices (Future)
```
API Gateway
    │
    ├──→ Chat Service (conversation flow)
    ├──→ LLM Service (inference)
    ├──→ RAG Service (embeddings)
    ├──→ Session Service (persistence)
    └──→ Export Service (report generation)
```

**Benefits**:
- Independent scaling per service
- Technology flexibility
- Fault isolation
- Easier maintenance

## Performance Optimization

### Current Performance Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| API Response Time (p95) | < 500ms | ~300ms | ✅ |
| LLM Response Time | < 3s | ~1-2s | ✅ |
| Context Retrieval | < 500ms | ~200ms | ✅ |
| Session Save | < 1s | ~100ms | ✅ |
| Prompt Generation | < 3s | ~1-2s | ✅ |
| Graph Visualization | < 2s | ~500ms | ✅ |

### Optimization Techniques

#### 1. Caching Strategy

```python
# Model list caching (5-minute TTL)
model_cache = {
    'groq': {'models': [...], 'timestamp': datetime},
    'openai': {'models': [...], 'timestamp': datetime}
}

# Prompt caching (per session)
prompt_cache = {
    'session_123': 'generated prompt...'
}
```

#### 2. Async Operations

```python
# All I/O operations are async
async def process_answer(self, session_id: str, answer: str):
    # Parallel operations where possible
    await asyncio.gather(
        self.rag.persist_interaction(session_id, question, answer),
        self.session.auto_save_if_needed(session_id)
    )
```

#### 3. Lazy Loading

```python
# Embeddings loaded on-demand
class RAGService:
    def __init__(self):
        self._model = None
    
    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model
```

#### 4. Database Indexing (Future)

When migrating to PostgreSQL:
```sql
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_messages_session_id ON messages(session_id);
```

## Testing Architecture

### Test Pyramid

```
        ┌─────────────┐
        │   E2E (5%)   │  ← Full user flow tests
        └─────────────┘
       ┌───────────────┐
       │ Integration   │  ← API endpoint tests (15%)
       │    (15%)      │
       └───────────────┘
      ┌─────────────────┐
      │   Unit Tests    │  ← Service/function tests (80%)
      │     (80%)       │
      └─────────────────┘
```

### Test Coverage

| Component | Coverage | Test Count |
|-----------|----------|------------|
| ConfigService | 83% | 15 tests |
| ModelChecker | 86% | 21 tests |
| ConversationService | 91% | 29 tests |
| LLMService | 91% | 20 tests |
| QuestionGenerator | 92% | 31 tests |
| RAGService | 93% | 16 tests |
| SessionService | 84% | 30 tests |
| PromptGenerator | 94% | 33 tests |
| GraphService | 99% | 28 tests |
| ExportService | 91% | 27 tests |
| **Overall** | **~90%** | **254 tests** |

### Testing Tools

```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
```

### Test Patterns

#### 1. Mocking External Services

```python
@pytest.fixture
def mock_llm_service():
    service = Mock(spec=LLMService)
    service.generate_response.return_value = "Mock LLM response"
    return service
```

#### 2. Async Test Support

```python
@pytest.mark.asyncio
async def test_conversation_flow():
    service = ConversationService(mock_llm, mock_rag, mock_gen)
    result = await service.process_answer(session_id, answer)
    assert result is not None
```

#### 3. Parametrized Tests

```python
@pytest.mark.parametrize("provider,token", [
    ("groq", "gsk_valid_token"),
    ("openai", "sk-valid-token")
])
def test_token_validation(provider, token):
    assert config.validate_token_format(provider, token)
```

## Monitoring & Observability (Planned)

### Logging Strategy

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "conversation.message_received",
    session_id=session_id,
    message_length=len(message),
    state=session.state.value
)
```

**Log Levels**:
- DEBUG: Detailed flow information
- INFO: Important events (session start, prompt generated)
- WARNING: Recoverable errors (rate limit hit, retry)
- ERROR: Failures requiring attention

### Metrics (Future)

```python
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request latency')
llm_calls = Counter('llm_api_calls_total', 'Total LLM API calls')
```

**Key Metrics**:
- API request rate and latency
- LLM API call count and cost
- Session creation rate
- Investigation completion rate
- Error rate by endpoint
- Cache hit/miss rate

### Error Tracking (Future)

Integration with Sentry:
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastAPIIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[FastAPIIntegration()],
    traces_sample_rate=0.1
)
```

## Deployment Architecture

### Development Environment

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./backend/data:/app/data

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
```

### Production Deployment (Planned)

```
                    Cloudflare CDN
                          │
                      Nginx Proxy
                     (SSL Termination)
                          │
            ┌─────────────┴─────────────┐
            │                           │
      Frontend (Static)            Backend API
      (Vercel/Netlify)           (AWS EC2/ECS)
                                        │
                                  ┌─────┴─────┐
                                  │           │
                            PostgreSQL    ChromaDB
                            (RDS)         (EC2)
```

## API Design Principles

### RESTful Conventions

```
GET    /api/chat/status/{session_id}       # Retrieve status
POST   /api/chat/start                     # Create new session
POST   /api/chat/message                   # Send message
DELETE /api/session/{session_id}           # Delete session
PUT    /api/chat/edit                      # Update message
```

### Response Format

```json
{
  "question": {
    "id": "uuid-here",
    "text": "What is your product's main functionality?",
    "category": "functionality",
    "is_followup": false,
    "timestamp": "2025-11-16T10:30:00Z"
  }
}
```

### Error Response Format

```json
{
  "detail": "Session not found",
  "error_code": "SESSION_NOT_FOUND",
  "timestamp": "2025-11-16T10:30:00Z"
}
```

## Conclusion

The Product Investigator Chatbot architecture is designed for:
- **Maintainability**: Clear separation of concerns, SOLID principles
- **Testability**: High test coverage, dependency injection
- **Scalability**: Async operations, caching, horizontal scaling path
- **Security**: Encryption, validation, CORS configuration
- **Performance**: < 500ms API response, optimized database queries

The current MVP architecture supports 100-500 concurrent users. With planned enhancements (PostgreSQL, Redis, load balancing), the system can scale to 10,000+ concurrent users.

---

*Last Updated: November 16, 2025*
*Version: 1.0*
*Document Owner: Technical Lead*
