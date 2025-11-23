# Unit Test Plan - Product Investigator Chatbot

## Overview
This document outlines the unit testing strategy for all components of the Product Investigator Chatbot system. Tests are organized by epic and component, covering both technical implementations and business rules.

---

## Testing Framework & Tools
- **Framework:** pytest
- **Async Support:** pytest-asyncio
- **Mocking:** pytest-mock, unittest.mock
- **HTTP Testing:** httpx (async client)
- **Coverage:** pytest-cov (target: >80%)
- **Fixtures:** pytest fixtures for common test data

---

## Epic 1: LLM Provider Configuration

### Component: Configuration Service (`services/config_service.py`)

#### Test Suite: `test_config_service.py`

**Business Rule Tests:**

1. **test_validate_groq_token_format()**
   - Valid token format accepted
   - Invalid format rejected with clear error
   - Empty token rejected
   - Token with special characters handled

2. **test_validate_openai_token_format()**
   - Valid OpenAI key format (sk-...)
   - Invalid format rejected
   - Legacy key format handled

3. **test_token_storage_encryption()**
   - Token encrypted before storage
   - Encrypted token can be decrypted
   - Original token matches after decrypt

4. **test_switch_provider()**
   - Switch from Groq to OpenAI
   - Switch from OpenAI to Groq
   - Previous token cleared on switch
   - New token validation triggered

**Technical Implementation Tests:**

5. **test_config_persistence()**
   - Config saved to .env file
   - Config loaded from .env file
   - Missing file handled gracefully

6. **test_concurrent_config_updates()**
   - Multiple update requests handled safely
   - No race conditions in token storage

---

### Component: Model Checker Service (`services/model_checker.py`)

#### Test Suite: `test_model_checker.py`

**Business Rule Tests:**

1. **test_fetch_groq_models()**
   - Returns list of available models
   - Empty list handled if no models
   - Models include required metadata

2. **test_fetch_openai_models()**
   - Returns OpenAI model list
   - Includes GPT-3.5 and GPT-4 variants
   - Model capabilities included

3. **test_invalid_token_error_handling()**
   - 401 Unauthorized handled
   - Clear error message returned
   - No crash on invalid token

4. **test_model_selection_validation()**
   - Valid model from list accepted
   - Invalid model rejected
   - Model ID stored correctly

**Technical Implementation Tests:**

5. **test_api_retry_logic()**
   - Retries on network failure (3 attempts)
   - Exponential backoff applied
   - Final failure returns error

6. **test_api_timeout_handling()**
   - Request times out after 10s
   - Timeout error propagated correctly

7. **test_model_caching()**
   - Model list cached for 5 minutes
   - Cache invalidated on token change
   - Fresh fetch after cache expiry

---

### Component: API Routes (`routes/config_routes.py`)

#### Test Suite: `test_config_routes.py`

**Business Rule Tests:**

1. **test_post_token_endpoint()**
   - POST /api/config/token accepts valid token
   - Returns 200 on success
   - Returns 400 on invalid format

2. **test_get_models_endpoint()**
   - GET /api/config/models returns JSON list
   - Returns 401 if token not set
   - Returns 200 with valid token

3. **test_select_model_endpoint()**
   - POST /api/config/model/select accepts model ID
   - Returns 400 if model not in available list
   - Returns 200 on successful selection

**Technical Implementation Tests:**

4. **test_cors_headers()**
   - CORS headers present in response
   - OPTIONS request handled

5. **test_rate_limiting()**
   - Rate limit enforced (100 req/min)
   - 429 returned when exceeded

---

## Epic 2: Product Investigation Conversation

### Component: Conversation Service (`services/conversation_service.py`)

#### Test Suite: `test_conversation_service.py`

**Business Rule Tests:**

1. **test_start_investigation_initial_question()**
   - First question about product functionality
   - Welcome message included
   - Session ID generated

2. **test_question_categories_coverage()**
   - All categories asked: functionality, users, demographics, design, market, technical
   - No category repeated unnecessarily

3. **test_contextual_followup_generation()**
   - Follow-up references previous answer
   - No redundant questions
   - Context maintained from RAG

4. **test_investigation_completion_criteria()**
   - Complete when all categories covered
   - Minimum 10 questions asked
   - User can force completion

5. **test_skip_question_handling()**
   - Skipped question not counted as answered
   - Alternative question generated
   - Progress tracking updated

6. **test_edit_previous_response()**
   - Previous answer can be updated
   - Subsequent questions re-evaluated
   - Context updated in RAG

**Technical Implementation Tests:**

7. **test_state_machine_transitions()**
   - START → FUNCTIONALITY → USERS → ...
   - Invalid transitions prevented
   - State persisted correctly

8. **test_async_question_generation()**
   - Questions generated asynchronously
   - No blocking during LLM call
   - Timeout after 30s

9. **test_conversation_session_isolation()**
   - Multiple sessions don't interfere
   - Session data properly separated

---

### Component: Question Generator (`services/question_generator.py`)

#### Test Suite: `test_question_generator.py`

**Business Rule Tests:**

1. **test_initial_question_template()**
   - Correct template for functionality
   - Professional tone maintained

2. **test_adapt_question_based_on_answers()**
   - Technical product → technical questions
   - B2C product → user experience questions
   - B2B product → business questions

3. **test_question_depth_progression()**
   - Early questions broad
   - Later questions more specific
   - Depth adapts to answer quality

**Technical Implementation Tests:**

4. **test_llm_prompt_construction()**
   - Prompt includes conversation context
   - System message properly formatted
   - Token limit respected

5. **test_question_validation()**
   - Generated question is valid string
   - Not empty or nonsensical
   - Grammar check passed

---

### Component: API Routes (`routes/chat_routes.py`)

#### Test Suite: `test_chat_routes.py`

**Business Rule Tests:**

1. **test_start_investigation_endpoint()**
   - POST /api/chat/start creates session
   - Returns first question
   - Session ID in response

2. **test_send_message_endpoint()**
   - POST /api/chat/message accepts answer
   - Returns next question
   - Updates conversation history

3. **test_get_history_endpoint()**
   - GET /api/chat/history/:sessionId returns full history
   - Returns 404 for invalid session
   - History in chronological order

**Technical Implementation Tests:**

4. **test_websocket_connection()**
   - WebSocket upgrades successfully
   - Streaming responses work
   - Connection closes cleanly

5. **test_concurrent_messages()**
   - Multiple messages handled in order
   - No race conditions

---

## Epic 3: Conversation Memory & RAG System

### Component: RAG Service (`services/rag_service.py`)

#### Test Suite: `test_rag_service.py`

**Business Rule Tests:**

1. **test_persist_conversation_to_markdown()**
   - Each Q&A written to file
   - "-----" delimiter between chunks
   - Timestamps included
   - Human-readable format

2. **test_chunk_separation()**
   - Chunks split on "-----"
   - Each chunk contains one Q&A
   - No empty chunks created

3. **test_retrieve_relevant_chunks()**
   - Returns 2-5 most relevant chunks
   - Semantic similarity calculated
   - Recent chunks weighted higher

4. **test_context_window_limit()**
   - Retrieved chunks fit in 4000 tokens
   - Truncates oldest chunks first
   - Critical context preserved

5. **test_no_redundant_context()**
   - Duplicate chunks not retrieved
   - Similar chunks deduplicated

**Technical Implementation Tests:**

6. **test_markdown_file_creation()**
   - File created per session
   - File naming convention followed
   - Directory created if missing

7. **test_embedding_generation()**
   - Embeddings created for each chunk
   - Vector dimensions correct (384 or 768)
   - Embeddings normalized

8. **test_vector_store_operations()**
   - Add chunk to vector store
   - Update existing chunk
   - Delete chunk
   - Search by similarity

9. **test_async_file_operations()**
   - File writes are non-blocking
   - No file corruption on concurrent writes

10. **test_large_conversation_handling()**
    - Handles 10,000+ tokens
    - Performance acceptable (<500ms retrieval)
    - Memory usage reasonable

---

### Component: Conversation Storage (`storage/conversation_storage.py`)

#### Test Suite: `test_conversation_storage.py`

**Business Rule Tests:**

1. **test_save_conversation_chunk()**
   - Chunk appended to file
   - Delimiter added
   - Metadata included

2. **test_load_conversation_history()**
   - Full history loaded from file
   - Chunks parsed correctly
   - Order preserved

**Technical Implementation Tests:**

3. **test_file_locking()**
   - Concurrent writes handled safely
   - No data loss

4. **test_file_rotation()**
   - Large files split at 10MB
   - Continuation file created
   - References maintained

---

## Epic 4: Prompt Generation

### Component: Prompt Generator Service (`services/prompt_generator.py`)

#### Test Suite: `test_prompt_generator.py`

**Business Rule Tests:**

1. **test_generate_comprehensive_prompt()**
   - All investigation answers included
   - Structured format (role, context, instructions, output)
   - SOLID principles mentioned
   - DRY principle emphasized

2. **test_prompt_engineering_best_practices()**
   - Clear instructions present
   - Examples included where needed
   - Constraints specified
   - Output format defined

3. **test_architecture_pattern_inclusion()**
   - MVC/MVVM suggested for web apps
   - Microservices for scalable systems
   - Patterns match product requirements

4. **test_technical_requirements_specification()**
   - Tech stack from investigation
   - Performance requirements
   - Security considerations

**Technical Implementation Tests:**

5. **test_prompt_template_rendering()**
   - Jinja2 template rendered correctly
   - Variables substituted
   - No template errors

6. **test_token_count_optimization()**
   - Generated prompt under 8000 tokens
   - Unnecessary content removed
   - Critical info preserved

7. **test_prompt_validation()**
   - Valid markdown output
   - No broken formatting
   - Code blocks properly escaped

---

### Component: API Routes (`routes/prompt_routes.py`)

#### Test Suite: `test_prompt_routes.py`

**Business Rule Tests:**

1. **test_generate_prompt_endpoint()**
   - GET /api/prompt/generate returns prompt
   - Returns 400 if investigation incomplete
   - Returns 200 with valid prompt

2. **test_regenerate_prompt_endpoint()**
   - POST /api/prompt/regenerate with modifications
   - Maintains core information
   - Adjusts focus areas

**Technical Implementation Tests:**

3. **test_prompt_caching()**
   - Generated prompt cached
   - Cache invalidated on regeneration
   - Cache key includes session ID

4. **test_download_prompt_endpoint()**
   - Download as .txt or .md
   - Correct content-type header
   - Filename includes timestamp

---

## Epic 5: LangGraph Visualization

### Component: Graph Service (`services/graph_service.py`)

#### Test Suite: `test_graph_service.py`

**Business Rule Tests:**

1. **test_build_conversation_graph()**
   - Node for each Q&A
   - Edges show progression
   - Graph is acyclic (DAG)

2. **test_decision_point_identification()**
   - Branch points highlighted
   - Alternative paths visible
   - Triggers documented

3. **test_topic_categorization()**
   - Nodes color-coded by category
   - Categories: functionality, users, design, market, technical

4. **test_graph_metadata()**
   - Timestamps on nodes
   - Total questions count
   - Investigation duration

**Technical Implementation Tests:**

5. **test_langgraph_integration()**
   - LangGraph StateGraph created
   - Nodes added correctly
   - Edges defined properly

6. **test_graph_serialization()**
   - Graph serialized to JSON
   - Deserializes correctly
   - No data loss

7. **test_mermaid_diagram_generation()**
   - Mermaid syntax valid
   - Renders in frontend
   - Handles special characters

8. **test_large_graph_performance()**
   - 100+ node graph builds in <2s
   - Memory efficient

---

### Component: API Routes (`routes/graph_routes.py`)

#### Test Suite: `test_graph_routes.py`

**Business Rule Tests:**

1. **test_get_visualization_endpoint()**
   - GET /api/graph/visualization returns graph data
   - Returns 404 for invalid session
   - Includes all required fields

2. **test_export_graph_endpoint()**
   - Export as PNG, SVG, HTML
   - Correct content-type
   - High resolution for PNG

**Technical Implementation Tests:**

3. **test_real_time_updates()**
   - Graph updates during conversation
   - WebSocket push on new node

---

## Epic 6: Frontend Interface

### Component: Chat UI Component (`frontend/ChatInterface.tsx`)

#### Test Suite: `test_chat_interface.test.tsx`

**Business Rule Tests:**

1. **test_display_user_message()**
   - User message displayed right-aligned
   - Avatar/icon shown
   - Timestamp visible

2. **test_display_system_message()**
   - System message left-aligned
   - Different styling from user
   - Markdown rendered

3. **test_loading_indicator()**
   - Shows while waiting for response
   - Animated dots or spinner
   - Clears when response arrives

**Technical Implementation Tests:**

4. **test_message_list_scrolling()**
   - Auto-scrolls to latest message
   - User can scroll up
   - Smooth scroll animation

5. **test_input_validation()**
   - Empty messages not sent
   - Max length enforced (2000 chars)
   - Special characters escaped

---

### Component: Settings Panel (`frontend/SettingsPanel.tsx`)

#### Test Suite: `test_settings_panel.test.tsx`

**Business Rule Tests:**

1. **test_api_token_input()**
   - Masked input for security
   - Validation on blur
   - Error message for invalid format

2. **test_provider_selection()**
   - Radio buttons for Groq/OpenAI
   - Token field updates on change
   - Models refetched on switch

3. **test_model_dropdown()**
   - Populated after models fetched
   - Disabled if no token
   - Selection persisted

**Technical Implementation Tests:**

4. **test_form_submission()**
   - Saves settings on submit
   - API call made
   - Success/error feedback shown

5. **test_cancel_resets_form()**
   - Form resets to previous values
   - No API call made

---

### Component: Progress Tracker (`frontend/ProgressTracker.tsx`)

#### Test Suite: `test_progress_tracker.test.tsx`

**Business Rule Tests:**

1. **test_progress_bar_updates()**
   - Percentage increases with each answer
   - Shows 0-100%
   - Visual indicator moves

2. **test_covered_topics_list()**
   - Checked items for answered categories
   - Unchecked for remaining
   - Tooltips on hover

**Technical Implementation Tests:**

3. **test_progress_calculation()**
   - Correct percentage: (answered / total) * 100
   - Rounds to whole number

---

## Epic 7: Session Management

### Component: Session Service (`services/session_service.py`)

#### Test Suite: `test_session_service.py`

**Business Rule Tests:**

1. **test_auto_save_every_n_interactions()**
   - Auto-save after 5 interactions
   - No save if less than threshold
   - Manual save overrides auto-save

2. **test_generate_session_id()**
   - UUID format
   - Unique for each session
   - Collision-free

3. **test_session_metadata()**
   - Created timestamp
   - Last modified timestamp
   - Product name (if provided)
   - Question count

4. **test_load_session()**
   - Session loaded with full context
   - RAG context restored
   - Current state restored

5. **test_list_sessions()**
   - Returns all user sessions
   - Sorted by last modified (descending)
   - Includes metadata preview

**Technical Implementation Tests:**

6. **test_session_serialization()**
   - Session serialized to JSON
   - All fields included
   - Deserializes correctly

7. **test_session_storage_location()**
   - Stored in ./sessions/ directory
   - Filename: {session_id}.json
   - Directory created if missing

8. **test_concurrent_session_handling()**
   - Multiple sessions don't conflict
   - Thread-safe operations

9. **test_session_file_corruption_recovery()**
   - Corrupted file detected
   - Backup restored if available
   - Error logged

---

### Component: Export Service (`services/export_service.py`)

#### Test Suite: `test_export_service.py`

**Business Rule Tests:**

1. **test_export_to_pdf()**
   - Full Q&A history included
   - Generated prompt included
   - Graph visualization embedded
   - Professional formatting

2. **test_export_to_markdown()**
   - Proper markdown syntax
   - Code blocks for prompt
   - Metadata header

3. **test_export_to_html()**
   - Valid HTML5
   - Styled with CSS
   - Interactive graph (if applicable)

**Technical Implementation Tests:**

4. **test_pdf_generation_library()**
   - Uses ReportLab or WeasyPrint
   - Handles Unicode characters
   - Embedded images work

5. **test_large_export_handling()**
   - Exports with 100+ Q&As
   - Performance acceptable (<10s)
   - File size reasonable

---

### Component: API Routes (`routes/session_routes.py`)

#### Test Suite: `test_session_routes.py`

**Business Rule Tests:**

1. **test_save_session_endpoint()**
   - POST /api/session/save creates/updates session
   - Returns session ID
   - Returns 200 on success

2. **test_load_session_endpoint()**
   - GET /api/session/load/:sessionId returns session data
   - Returns 404 if not found
   - Returns 200 with valid session

3. **test_list_sessions_endpoint()**
   - GET /api/session/list returns array of sessions
   - Includes metadata only (not full content)
   - Paginated (20 per page)

4. **test_delete_session_endpoint()**
   - DELETE /api/session/:sessionId removes session
   - Returns 204 on success
   - Returns 404 if not found

**Technical Implementation Tests:**

5. **test_session_id_validation()**
   - Invalid UUID rejected (400)
   - SQL injection prevented

---

## Integration Tests

### Test Suite: `test_integration.py`

1. **test_end_to_end_investigation()**
   - Start investigation → Answer questions → Generate prompt
   - All components work together
   - Session saved and loadable

2. **test_rag_context_flow()**
   - Conversation persisted to markdown
   - Context retrieved for questions
   - Relevant chunks used in prompts

3. **test_llm_provider_switch_mid_investigation()**
   - Start with Groq
   - Switch to OpenAI
   - Conversation continues seamlessly

4. **test_session_export_integration()**
   - Complete investigation
   - Export to PDF/Markdown/HTML
   - All data present in export

---

## Non-Functional Requirement Tests

### Performance Tests (`test_performance.py`)

1. **test_response_time_under_3_seconds()**
   - Typical query responds in <3s
   - Measured with time.perf_counter()

2. **test_rag_retrieval_under_500ms()**
   - Context fetch completes in <500ms
   - Vector search optimized

3. **test_concurrent_user_load()**
   - 10 concurrent users
   - No degradation in response time

4. **test_large_conversation_memory_usage()**
   - 10,000 token conversation
   - Memory usage <500MB

### Security Tests (`test_security.py`)

1. **test_token_encryption_at_rest()**
   - Token stored encrypted in .env
   - Decryption requires key

2. **test_sql_injection_prevention()**
   - Malicious input sanitized
   - No database commands executed

3. **test_xss_prevention()**
   - Script tags escaped in markdown
   - HTML sanitized in frontend

4. **test_rate_limiting_enforcement()**
   - 100 req/min limit
   - 429 returned when exceeded

### Reliability Tests (`test_reliability.py`)

1. **test_llm_api_failure_retry()**
   - Retries 3 times on failure
   - Exponential backoff
   - Graceful degradation

2. **test_data_persistence_on_crash()**
   - Conversation saved before crash
   - No data loss
   - Recovery on restart

3. **test_error_logging()**
   - Errors logged to file
   - Stack traces included
   - Sensitive data redacted

---

## Test Data & Fixtures

### Fixtures (`conftest.py`)

```python
@pytest.fixture
def mock_groq_client():
    """Mock Groq API client"""
    pass

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI API client"""
    pass

@pytest.fixture
def sample_conversation():
    """Sample Q&A conversation data"""
    pass

@pytest.fixture
def sample_session():
    """Sample session with metadata"""
    pass

@pytest.fixture
def mock_rag_service():
    """Mock RAG service with predefined context"""
    pass

@pytest.fixture
def test_markdown_file(tmp_path):
    """Temporary markdown file for testing"""
    pass
```

### Test Data (`tests/data/`)

- `sample_conversations.json` - Various conversation examples
- `sample_prompts.md` - Expected prompt outputs
- `invalid_tokens.txt` - Invalid token formats for validation tests
- `large_conversation.md` - 10,000+ token conversation for performance tests

---

## Coverage Goals

- **Overall Code Coverage:** >80%
- **Critical Paths:** 100% (LLM calls, RAG retrieval, prompt generation)
- **Business Logic:** >90%
- **API Routes:** >85%
- **Services:** >80%
- **Utilities:** >75%

---

## Continuous Integration

### CI Pipeline (`test_ci.yml`)

1. **Lint:** Run flake8, black, isort
2. **Unit Tests:** Run all unit tests with pytest
3. **Coverage Report:** Generate and publish coverage
4. **Integration Tests:** Run end-to-end tests
5. **Security Scan:** Run bandit for security issues

### Pre-commit Hooks

- Run unit tests for changed files
- Enforce code formatting
- Check for sensitive data in commits

---

## Test Execution Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_conversation_service.py

# Run with coverage
pytest --cov=services --cov-report=html

# Run only fast tests (exclude integration)
pytest -m "not integration"

# Run with verbose output
pytest -v

# Run failed tests only
pytest --lf

# Run tests matching pattern
pytest -k "test_rag"

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

---

## Test Maintenance

- **Review:** Tests reviewed in every PR
- **Update:** Tests updated with feature changes
- **Refactor:** Eliminate duplicate test code
- **Document:** Complex tests documented with comments
- **Monitor:** Track flaky tests and fix root causes

---

## Mock Strategies

### LLM API Mocking

- Use `responses` library for HTTP mocking
- Create fixtures for common LLM responses
- Mock streaming responses with async generators

### Database/Storage Mocking

- Use `tmp_path` fixture for file operations
- Mock vector store with in-memory implementation
- Use `freezegun` for timestamp testing

### External Service Mocking

- Mock Groq/OpenAI APIs completely
- No real API calls in unit tests
- Integration tests use sandbox environments

---

## Documentation

Each test file should include:

- Docstring describing test suite purpose
- Comments for complex test logic
- Links to requirements being tested
- Expected behavior documentation

Example:
```python
def test_generate_followup_question():
    """
    Test that follow-up questions reference previous answers.
    
    Business Rule: US-2.3 - Receive Contextual Follow-ups
    
    Given a conversation with previous answers about a mobile app
    When generating the next question
    Then the question should reference "mobile app" context
    And should not repeat already-asked questions
    """
    # Test implementation
```

---

## Success Criteria

- All tests pass in CI/CD pipeline
- Coverage goals met (>80% overall)
- Zero critical security vulnerabilities
- Performance benchmarks achieved
- Integration tests complete end-to-end flows
- Tests are maintainable and well-documented