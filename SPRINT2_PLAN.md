# Sprint 2 Implementation Plan

**Date:** November 16, 2025  
**Sprint Goal:** Implement conversation memory with RAG, complete investigation flow, and session persistence  
**Duration:** 2 weeks

---

## 📋 Sprint 2 Overview

**Based on:** tasks2.md  
**Previous Sprint:** Sprint 1 ✅ COMPLETED (November 16, 2025)

### Sprint Objectives
1. Implement RAG (Retrieval-Augmented Generation) system for conversation memory
2. Enhance conversation flow with context-aware questions
3. Add session persistence and management
4. Build UI components for progress tracking and session management

---

## 🎯 Tasks Breakdown (9 Tasks)

### Epic 3: Conversation Memory & RAG System

#### ⬜ TASK-2.1: Implement Markdown Storage
**Priority:** P0 - Critical | **Story Points:** 5

**Deliverables:**
- `storage/conversation_storage.py` - ConversationStorage class
- Async file operations with aiofiles
- Markdown format with "-----" delimiters
- Thread-safe file operations
- 5 unit tests

**Dependencies:** None

---

#### ⬜ TASK-2.2: Implement RAG Service with Embeddings
**Priority:** P0 - Critical | **Story Points:** 8

**Deliverables:**
- `services/rag_service.py` - RAGService class
- sentence-transformers integration (all-MiniLM-L6-v2)
- FAISS vector store for similarity search
- Context retrieval with recency weighting
- Chunk deduplication
- 8 unit tests

**Dependencies:** 
- TASK-2.1 (Markdown Storage)
- New Python packages: `sentence-transformers`, `faiss-cpu`

**Key Features:**
- Embed conversation chunks as vectors
- Retrieve 2-5 most relevant chunks
- Context window management (4000 tokens)
- Recent chunks weighted higher

---

#### ⬜ TASK-2.3: Integrate RAG with Conversation Service
**Priority:** P0 - Critical | **Story Points:** 5

**Deliverables:**
- Updated `services/conversation_service.py`
- RAG context retrieval before question generation
- Persist all interactions to RAG
- 2 integration tests

**Dependencies:**
- TASK-2.2 (RAG Service)
- TASK-2.4 (Question Generator)

---

### Epic 2 (Continued): Advanced Conversation Flow

#### ⬜ TASK-2.4: Implement Question Generator
**Priority:** P0 - Critical | **Story Points:** 8

**Deliverables:**
- `services/question_generator.py` - QuestionGenerator class
- Category-based question templates
- LLM-based follow-up generation
- Question depth progression logic
- 6 unit tests

**Dependencies:**
- Existing LLMService from Sprint 1

**Key Features:**
- 6 conversation categories with templates
- Adapt questions based on product type
- Determine when follow-up vs new category needed
- Context-aware question generation

---

#### ⬜ TASK-2.5: Add Skip and Edit Functionality
**Priority:** P1 - High | **Story Points:** 5

**Deliverables:**
- Updated `routes/chat_routes.py`
- Updated `services/conversation_service.py`
- POST /api/chat/skip endpoint
- PUT /api/chat/edit endpoint
- 2 unit tests

**Dependencies:**
- TASK-2.3 (RAG Integration) for context updates

**Key Features:**
- Skip current question → move to next category
- Edit previous answer → update RAG context
- Track skipped questions in session

---

### Epic 7: Session Management

#### ⬜ TASK-2.6: Implement Session Service
**Priority:** P0 - Critical | **Story Points:** 8

**Deliverables:**
- `services/session_service.py` - SessionService class
- Session serialization to JSON
- Session deserialization with full restoration
- List/delete session operations
- Auto-save logic (every 5 interactions)
- 8 unit tests

**Dependencies:** None

**Storage Format:**
```
./sessions/
  └── <session_id>.json (session state, messages, metadata)
```

---

#### ⬜ TASK-2.7: Create Session API Routes
**Priority:** P1 - High | **Story Points:** 5

**Deliverables:**
- `routes/session_routes.py` - Session router
- POST /api/session/save
- GET /api/session/load/:sessionId
- GET /api/session/list (paginated)
- DELETE /api/session/:sessionId
- 5 unit tests

**Dependencies:**
- TASK-2.6 (Session Service)

---

### Frontend Components

#### ⬜ TASK-2.8: Build Progress Tracker UI
**Priority:** P1 - High | **Story Points:** 5

**Deliverables:**
- `frontend/src/components/ProgressTracker.jsx`
- Progress bar with percentage
- Category checklist with visual indicators
- Question counter
- 3 component tests

**Dependencies:** None (can start in parallel)

**UI Elements:**
- Progress bar (0-100%)
- 6 categories with checkmarks
- Current category highlight
- Question count display

---

#### ⬜ TASK-2.9: Add Session Management UI
**Priority:** P2 - Medium | **Story Points:** 5

**Deliverables:**
- `frontend/src/components/SessionManager.jsx`
- Save/Load session buttons
- Session list modal
- Delete session confirmation
- Auto-save indicator
- 3 component tests

**Dependencies:**
- TASK-2.7 (Session API Routes)

---

## 📦 New Dependencies Required

### Backend Python Packages
```bash
pip install sentence-transformers faiss-cpu aiofiles
```

Update `requirements.txt`:
```
sentence-transformers==2.2.2
faiss-cpu==1.7.4
aiofiles==23.2.1
```

### Frontend Packages
```bash
npm install lucide-react  # Icons for UI
```

---

## 🗂️ New Directory Structure

```
backend/
  storage/
    __init__.py
    conversation_storage.py        # TASK-2.1
  data/
    conversations/                 # Markdown files
      <session_id>.md
    sessions/                      # JSON session files
      <session_id>.json
    vectors/                       # FAISS index (optional persistence)
      index.faiss

frontend/
  src/
    components/
      ProgressTracker.jsx          # TASK-2.8
      SessionManager.jsx           # TASK-2.9
```

---

## 🔄 Implementation Order (Recommended)

### Week 1: RAG System & Core Services
1. **Day 1-2:** TASK-2.1 (Markdown Storage) → TASK-2.2 (RAG Service)
2. **Day 3-4:** TASK-2.4 (Question Generator) → TASK-2.3 (RAG Integration)
3. **Day 5:** TASK-2.5 (Skip/Edit Functionality)

### Week 2: Session Management & UI
1. **Day 1-2:** TASK-2.6 (Session Service) → TASK-2.7 (Session API Routes)
2. **Day 3:** TASK-2.8 (Progress Tracker UI)
3. **Day 4:** TASK-2.9 (Session Manager UI)
4. **Day 5:** Integration testing & bug fixes

---

## ✅ Sprint 2 Definition of Done

- [ ] All P0 and P1 tasks completed (8 tasks)
- [ ] RAG system operational with vector search
- [ ] Full conversation flow with skip/edit functionality
- [ ] Session persistence working (save/load/list/delete)
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests for RAG flow
- [ ] Frontend components integrated
- [ ] Performance: Context retrieval < 500ms
- [ ] Sprint demo completed

---

## ⚠️ Risks & Mitigation Strategies

### Risk 1: FAISS Performance with Large Conversations
**Impact:** High  
**Probability:** Medium  
**Mitigation:**
- Implement chunk limit (e.g., max 1000 chunks)
- Test with 10,000+ tokens
- Consider FAISS index persistence
- Add pagination for very long conversations

### Risk 2: RAG Context Relevance Quality
**Impact:** High  
**Probability:** Medium  
**Mitigation:**
- Manual testing with diverse conversation types
- Tune retrieval parameters (top_k, similarity threshold)
- Implement A/B testing framework for question quality
- Add user feedback mechanism

### Risk 3: Session File Corruption
**Impact:** Medium  
**Probability:** Low  
**Mitigation:**
- Implement backup/recovery mechanism
- Validate JSON on load with try/catch
- Add schema validation with Pydantic
- Periodic backup to S3 or cloud storage

### Risk 4: Complex State Management in Frontend
**Impact:** Medium  
**Probability:** Medium  
**Mitigation:**
- Use React Context API early
- Consider Zustand or Redux if needed
- Keep session state in sync with backend
- Implement optimistic UI updates

---

## 📊 Success Metrics

### Technical Metrics
- **Test Coverage:** >80% for new code
- **API Response Time:** 
  - RAG context retrieval: <500ms
  - Session save/load: <200ms
- **Memory Usage:** <500MB for 1000 active sessions
- **Vector Store Size:** <100MB for 10,000 chunks

### Functional Metrics
- All 9 conversation categories covered
- Skip/edit functionality works correctly
- Sessions persist and restore without data loss
- Progress tracker updates in real-time

---

## 🚀 Getting Started

### Step 1: Install New Dependencies
```bash
# Backend
cd backend
source ../.venv/bin/activate
pip install sentence-transformers faiss-cpu aiofiles

# Frontend
cd ../frontend
npm install lucide-react
```

### Step 2: Create Directory Structure
```bash
cd backend
mkdir -p storage data/conversations data/sessions data/vectors
```

### Step 3: Start with TASK-2.1
Follow the implementation plan in tasks2.md, starting with Markdown Storage.

---

## 📝 Next Steps After Sprint 2

According to the project roadmap, Sprint 3 should focus on:
1. Prompt generation and refinement
2. Export functionality (Markdown, JSON, PDF)
3. Advanced analytics and insights
4. Performance optimization

---

**Generated:** November 16, 2025  
**Project:** Lovable Prompt Generator  
**Sprint:** Sprint 2 - RAG System, Advanced Conversation & Session Management  
**Status:** 🟡 READY TO START
