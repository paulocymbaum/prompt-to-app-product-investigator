"""
Comprehensive test suite for Session API Routes.

Tests cover:
- POST /api/session/save endpoint
- GET /api/session/load/:id endpoint
- GET /api/session/list endpoint
- DELETE /api/session/:id endpoint
- Request/response validation
- Error handling
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime

from routes.session_routes import router, get_conversation_service
from services.conversation_service import ConversationService
from models.conversation import (
    Session,
    Message,
    MessageRole,
    ConversationState
)


@pytest.fixture
def test_app():
    """Create FastAPI test app with session routes."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    """Create FastAPI test client."""
    with TestClient(test_app) as c:
        yield c


@pytest.fixture
def sample_session_id():
    """Return a sample session ID."""
    return "test-session-routes-001"


@pytest.fixture
def populated_conversation_service(sample_session_id):
    """Create a ConversationService with a pre-populated session."""
    conversation = get_conversation_service()
    
    # Create a sample session
    session = Session(
        id=sample_session_id,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        last_updated=datetime(2024, 1, 1, 12, 30, 0),
        status="active",
        state=ConversationState.FUNCTIONALITY,
        investigation_progress={"functionality": 0.5},
        metadata={"product_name": "TestProduct"},
        provider="groq",
        model_id="llama2-70b-4096",
        skipped_questions=[]
    )
    
    # Create sample messages
    messages = [
        Message(
            id="msg-001",
            session_id=sample_session_id,
            role=MessageRole.SYSTEM,
            content="Welcome message",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            metadata={}
        ),
        Message(
            id="msg-002",
            session_id=sample_session_id,
            role=MessageRole.ASSISTANT,
            content="What is your product?",
            timestamp=datetime(2024, 1, 1, 12, 1, 0),
            metadata={"question_id": "q-001"}
        ),
        Message(
            id="msg-003",
            session_id=sample_session_id,
            role=MessageRole.USER,
            content="A task management app",
            timestamp=datetime(2024, 1, 1, 12, 2, 0),
            metadata={}
        )
    ]
    
    # Add to conversation service
    conversation.sessions[sample_session_id] = session
    conversation.messages[sample_session_id] = messages
    
    yield conversation
    
    # Cleanup
    if sample_session_id in conversation.sessions:
        del conversation.sessions[sample_session_id]
    if sample_session_id in conversation.messages:
        del conversation.messages[sample_session_id]
    if sample_session_id in conversation.last_save_counts:
        del conversation.last_save_counts[sample_session_id]


class TestSaveSessionEndpoint:
    """Test POST /api/session/save endpoint."""
    
    def test_save_session_success(self, client, populated_conversation_service, sample_session_id):
        """Test successful session save."""
        response = client.post(
            "/api/session/save",
            json={"session_id": sample_session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["session_id"] == sample_session_id
        assert "message" in data
        assert "successfully" in data["message"].lower()
    
    def test_save_session_not_found(self, client):
        """Test saving non-existent session returns 404."""
        response = client.post(
            "/api/session/save",
            json={"session_id": "nonexistent-session"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_save_session_validation_error(self, client):
        """Test request validation with missing session_id."""
        response = client.post(
            "/api/session/save",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_save_session_response_structure(self, client, populated_conversation_service, sample_session_id):
        """Test response has correct structure."""
        response = client.post(
            "/api/session/save",
            json={"session_id": sample_session_id}
        )
        
        data = response.json()
        
        # Check all required fields
        assert "success" in data
        assert "session_id" in data
        assert "message" in data
        
        # Check types
        assert isinstance(data["success"], bool)
        assert isinstance(data["session_id"], str)
        assert isinstance(data["message"], str)


class TestLoadSessionEndpoint:
    """Test GET /api/session/load/:id endpoint."""
    
    @pytest.mark.asyncio
    async def test_load_session_success(self, client, populated_conversation_service, sample_session_id):
        """Test successful session load."""
        # First save the session
        await populated_conversation_service.manual_save_session(sample_session_id)
        
        # Remove from memory to test loading
        del populated_conversation_service.sessions[sample_session_id]
        del populated_conversation_service.messages[sample_session_id]
        
        # Load session via API
        response = client.get(f"/api/session/load/{sample_session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["session_id"] == sample_session_id
        assert data["message_count"] == 3
        assert data["state"] == "functionality"
        assert "message" in data
    
    def test_load_session_not_found(self, client):
        """Test loading non-existent session returns 404."""
        response = client.get("/api/session/load/nonexistent-session")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_load_session_restores_to_memory(self, client, populated_conversation_service, sample_session_id):
        """Test that loaded session is accessible in conversation service."""
        # Save session
        await populated_conversation_service.manual_save_session(sample_session_id)
        
        # Remove from memory
        del populated_conversation_service.sessions[sample_session_id]
        del populated_conversation_service.messages[sample_session_id]
        
        # Load via API
        response = client.get(f"/api/session/load/{sample_session_id}")
        assert response.status_code == 200
        
        # Verify session is back in memory
        assert sample_session_id in populated_conversation_service.sessions
        assert sample_session_id in populated_conversation_service.messages
        
        # Verify content
        session = populated_conversation_service.get_session(sample_session_id)
        assert session is not None
        assert session.state == ConversationState.FUNCTIONALITY
    
    @pytest.mark.asyncio
    async def test_load_session_response_structure(self, client, populated_conversation_service, sample_session_id):
        """Test response has correct structure."""
        # Save first
        await populated_conversation_service.manual_save_session(sample_session_id)
        
        response = client.get(f"/api/session/load/{sample_session_id}")
        data = response.json()
        
        # Check all required fields
        assert "success" in data
        assert "session_id" in data
        assert "message_count" in data
        assert "state" in data
        assert "message" in data
        
        # Check types
        assert isinstance(data["success"], bool)
        assert isinstance(data["session_id"], str)
        assert isinstance(data["message_count"], int)
        assert isinstance(data["state"], str)
        assert isinstance(data["message"], str)


class TestListSessionsEndpoint:
    """Test GET /api/session/list endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, client, populated_conversation_service):
        """Test listing sessions when none exist."""
        # Ensure no sessions saved
        conversation = populated_conversation_service
        if conversation.session_svc:
            # Clear any existing sessions
            sessions = await conversation.session_svc.list_sessions()
            for session in sessions:
                await conversation.session_svc.delete_session(session['id'])
        
        response = client.get("/api/session/list")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sessions" in data
        assert "total" in data
        assert data["total"] == 0
        assert len(data["sessions"]) == 0
    
    @pytest.mark.asyncio
    async def test_list_sessions_with_sessions(self, client, populated_conversation_service, sample_session_id):
        """Test listing sessions when some exist."""
        # Save a session
        await populated_conversation_service.manual_save_session(sample_session_id)
        
        response = client.get("/api/session/list")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        assert len(data["sessions"]) >= 1
        
        # Check first session structure
        session = data["sessions"][0]
        assert "id" in session
        assert "started_at" in session
        assert "last_updated" in session
        assert "status" in session
        assert "state" in session
        assert "question_count" in session
        assert "message_count" in session
    
    @pytest.mark.asyncio
    async def test_list_sessions_pagination_limit(self, client, populated_conversation_service):
        """Test pagination with limit parameter."""
        # Save multiple sessions
        for i in range(5):
            session_id = f"pagination-test-{i}"
            session = Session(id=session_id)
            conversation = populated_conversation_service
            conversation.sessions[session_id] = session
            conversation.messages[session_id] = []
            await conversation.manual_save_session(session_id)
        
        # Request with limit
        response = client.get("/api/session/list?limit=3")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["sessions"]) <= 3
        assert data["limit"] == 3
    
    @pytest.mark.asyncio
    async def test_list_sessions_pagination_offset(self, client, populated_conversation_service):
        """Test pagination with offset parameter."""
        # Save sessions first
        for i in range(3):
            session_id = f"offset-test-{i}"
            session = Session(id=session_id)
            conversation = populated_conversation_service
            conversation.sessions[session_id] = session
            conversation.messages[session_id] = []
            await conversation.manual_save_session(session_id)
        
        # Request with offset
        response = client.get("/api/session/list?offset=1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["offset"] == 1
    
    def test_list_sessions_response_structure(self, client):
        """Test response has correct structure."""
        response = client.get("/api/session/list")
        
        data = response.json()
        
        # Check all required fields
        assert "sessions" in data
        assert "total" in data
        assert "limit" in data or data.get("limit") is None
        assert "offset" in data
        
        # Check types
        assert isinstance(data["sessions"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["offset"], int)


class TestDeleteSessionEndpoint:
    """Test DELETE /api/session/:id endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_session_success(self, client, populated_conversation_service, sample_session_id):
        """Test successful session deletion."""
        # Save session first
        await populated_conversation_service.manual_save_session(sample_session_id)
        
        # Delete via API
        response = client.delete(f"/api/session/{sample_session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["session_id"] == sample_session_id
        assert "message" in data
    
    def test_delete_session_not_found(self, client):
        """Test deleting non-existent session returns 404."""
        response = client.delete("/api/session/nonexistent-session")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_delete_session_removes_from_memory(self, client, populated_conversation_service, sample_session_id):
        """Test that deleted session is removed from memory."""
        # Save session
        await populated_conversation_service.manual_save_session(sample_session_id)
        
        # Verify in memory
        assert sample_session_id in populated_conversation_service.sessions
        
        # Delete via API
        response = client.delete(f"/api/session/{sample_session_id}")
        assert response.status_code == 200
        
        # Verify removed from memory
        assert sample_session_id not in populated_conversation_service.sessions
        assert sample_session_id not in populated_conversation_service.messages
    
    @pytest.mark.asyncio
    async def test_delete_session_removes_file(self, client, populated_conversation_service, sample_session_id):
        """Test that session file is removed from storage."""
        # Save session
        await populated_conversation_service.manual_save_session(sample_session_id)
        
        # Verify file exists
        conversation = populated_conversation_service
        if conversation.session_svc:
            filepath = conversation.session_svc.base_dir / f"{sample_session_id}.json"
            assert filepath.exists()
            
            # Delete via API
            response = client.delete(f"/api/session/{sample_session_id}")
            assert response.status_code == 200
            
            # Verify file removed
            assert not filepath.exists()
    
    @pytest.mark.asyncio
    async def test_delete_session_response_structure(self, client, populated_conversation_service, sample_session_id):
        """Test response has correct structure."""
        # Save first
        await populated_conversation_service.manual_save_session(sample_session_id)
        
        response = client.delete(f"/api/session/{sample_session_id}")
        data = response.json()
        
        # Check all required fields
        assert "success" in data
        assert "session_id" in data
        assert "message" in data
        
        # Check types
        assert isinstance(data["success"], bool)
        assert isinstance(data["session_id"], str)
        assert isinstance(data["message"], str)


class TestErrorHandling:
    """Test error handling across all endpoints."""
    
    def test_save_invalid_json(self, client):
        """Test saving with invalid JSON."""
        response = client.post(
            "/api/session/save",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_list_invalid_limit(self, client):
        """Test listing with invalid limit parameter."""
        response = client.get("/api/session/list?limit=0")
        
        assert response.status_code == 422  # Validation error
    
    def test_list_invalid_offset(self, client):
        """Test listing with invalid offset parameter."""
        response = client.get("/api/session/list?offset=-1")
        
        assert response.status_code == 422  # Validation error
    
    def test_list_limit_too_large(self, client):
        """Test listing with limit exceeding maximum."""
        response = client.get("/api/session/list?limit=101")
        
        assert response.status_code == 422  # Validation error
