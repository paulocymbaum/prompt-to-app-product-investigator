"""
Unit tests for Chat API Routes.

Tests cover:
- POST /api/chat/start endpoint
- POST /api/chat/message endpoint
- GET /api/chat/history/:sessionId endpoint
- GET /api/chat/status/:sessionId endpoint
- WebSocket /api/chat/ws/:sessionId endpoint
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from routes.chat_routes import router
from services.conversation_service import ConversationService
from models.conversation import Message, Question, MessageRole, ConversationState, Session
from datetime import datetime


@pytest.fixture
def mock_conversation_service():
    """Create mock ConversationService"""
    mock = Mock(spec=ConversationService)
    
    # Mock start_investigation
    mock_question = Question(
        id="q-123",
        category="functionality",
        text="What is the main functionality of your product?",
        context=[],
        is_followup=False,
        timestamp=datetime.utcnow()
    )
    mock.start_investigation.return_value = ("session-123", mock_question)
    
    # Mock process_answer
    next_question = Question(
        id="q-456",
        category="users",
        text="Who are your target users?",
        context=[],
        is_followup=False,
        timestamp=datetime.utcnow()
    )
    mock.process_answer = AsyncMock(return_value=next_question)
    
    # Mock get_conversation_history
    mock_messages = [
        Message(
            id="m-1",
            session_id="session-123",
            role=MessageRole.SYSTEM,
            content="What is your product?",
            timestamp=datetime.utcnow(),
            metadata={}
        ),
        Message(
            id="m-2",
            session_id="session-123",
            role=MessageRole.USER,
            content="A task management app",
            timestamp=datetime.utcnow(),
            metadata={}
        )
    ]
    mock.get_conversation_history.return_value = mock_messages
    
    # Mock get_session
    mock_session = Session(
        id="session-123",
        started_at=datetime.utcnow(),
        last_updated=datetime.utcnow(),
        status="active",
        state=ConversationState.FUNCTIONALITY,
        investigation_progress={},
        metadata={}
    )
    mock.get_session.return_value = mock_session
    
    # Mock is_investigation_complete
    mock.is_investigation_complete.return_value = False
    
    return mock


@pytest.fixture
def app(mock_conversation_service):
    """Create FastAPI test app with mocked dependencies"""
    from routes.chat_routes import get_conversation_service
    
    app = FastAPI()
    app.include_router(router)
    
    # Override dependency to return mock
    app.dependency_overrides[get_conversation_service] = lambda: mock_conversation_service
    
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestStartInvestigation:
    """Test suite for POST /api/chat/start endpoint"""
    
    def test_start_investigation_success(self, client, mock_conversation_service):
        """Test successful investigation start"""
        response = client.post("/api/chat/start", json={})
        
        assert response.status_code == 201
        data = response.json()
        
        assert "session_id" in data
        assert "question" in data
        assert "message" in data
        assert data["session_id"] == "session-123"
        assert data["question"]["id"] == "q-123"
        assert data["message"] == "Investigation started successfully"
        
        mock_conversation_service.start_investigation.assert_called_once()
    
    def test_start_investigation_with_provider(self, client, mock_conversation_service):
        """Test start investigation with specific provider"""
        response = client.post("/api/chat/start", json={
            "provider": "groq",
            "model_id": "llama2-70b-4096"
        })
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["session_id"] == "session-123"
        mock_conversation_service.start_investigation.assert_called_once_with(
            provider="groq",
            model_id="llama2-70b-4096"
        )
    
    def test_start_investigation_error(self, client, mock_conversation_service):
        """Test error handling on start investigation"""
        mock_conversation_service.start_investigation.side_effect = Exception("Service error")
        
        response = client.post("/api/chat/start", json={})
        
        assert response.status_code == 500
        assert "Failed to start investigation" in response.json()["detail"]


class TestSendMessage:
    """Test suite for POST /api/chat/message endpoint"""
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, client, mock_conversation_service):
        """Test successful message sending"""
        response = client.post("/api/chat/message", json={
            "session_id": "session-123",
            "message": "A task management app for remote teams"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "question" in data
        assert "complete" in data
        assert data["complete"] is False
        assert data["question"]["id"] == "q-456"
        assert data["message"] == "Message processed successfully"
        
        mock_conversation_service.process_answer.assert_called_once_with(
            session_id="session-123",
            answer_text="A task management app for remote teams"
        )
    
    @pytest.mark.asyncio
    async def test_send_message_investigation_complete(self, client, mock_conversation_service):
        """Test message when investigation is complete"""
        mock_conversation_service.process_answer = AsyncMock(return_value=None)
        
        response = client.post("/api/chat/message", json={
            "session_id": "session-123",
            "message": "Final answer"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["question"] is None
        assert data["complete"] is True
        assert "complete" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_send_message_session_not_found(self, client, mock_conversation_service):
        """Test error when session not found"""
        mock_conversation_service.process_answer = AsyncMock(
            side_effect=ValueError("Session not found")
        )
        
        response = client.post("/api/chat/message", json={
            "session_id": "invalid-session",
            "message": "Test message"
        })
        
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]
    
    def test_send_message_validation_error(self, client):
        """Test validation error for empty message"""
        response = client.post("/api/chat/message", json={
            "session_id": "session-123",
            "message": ""
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_send_message_missing_fields(self, client):
        """Test validation error for missing fields"""
        response = client.post("/api/chat/message", json={
            "session_id": "session-123"
        })
        
        assert response.status_code == 422


class TestGetHistory:
    """Test suite for GET /api/chat/history/:sessionId endpoint"""
    
    def test_get_history_success(self, client, mock_conversation_service):
        """Test successful history retrieval"""
        response = client.get("/api/chat/history/session-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert "messages" in data
        assert "total_messages" in data
        assert data["session_id"] == "session-123"
        assert data["total_messages"] == 2
        assert len(data["messages"]) == 2
        
        mock_conversation_service.get_conversation_history.assert_called_once_with("session-123")
    
    def test_get_history_session_not_found(self, client, mock_conversation_service):
        """Test error when session not found"""
        mock_conversation_service.get_conversation_history.side_effect = ValueError(
            "Session not found"
        )
        
        response = client.get("/api/chat/history/invalid-session")
        
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]


class TestGetSessionStatus:
    """Test suite for GET /api/chat/status/:sessionId endpoint"""
    
    def test_get_status_success(self, client, mock_conversation_service):
        """Test successful status retrieval"""
        response = client.get("/api/chat/status/session-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == "session-123"
        assert data["exists"] is True
        assert data["complete"] is False
        assert data["state"] == "functionality"
        assert data["message_count"] == 2
    
    def test_get_status_session_not_found(self, client, mock_conversation_service):
        """Test status when session doesn't exist"""
        mock_conversation_service.get_session.return_value = None
        
        response = client.get("/api/chat/status/invalid-session")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == "invalid-session"
        assert data["exists"] is False
        assert data["complete"] is False
        assert data["state"] is None
        assert data["message_count"] == 0
    
    def test_get_status_complete_investigation(self, client, mock_conversation_service):
        """Test status for completed investigation"""
        mock_conversation_service.is_investigation_complete.return_value = True
        
        response = client.get("/api/chat/status/session-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["complete"] is True


class TestWebSocket:
    """Test suite for WebSocket endpoint"""
    
    def test_websocket_connection(self, client, mock_conversation_service):
        """Test WebSocket connection"""
        # Patch get_conversation_service at module level for WebSocket
        with patch('routes.chat_routes.get_conversation_service', return_value=mock_conversation_service):
            with client.websocket_connect("/api/chat/ws/session-123") as websocket:
                # Receive welcome message
                data = websocket.receive_json()
                assert data["type"] == "connected"
                assert data["session_id"] == "session-123"
    
    def test_websocket_send_message(self, client, mock_conversation_service):
        """Test sending message via WebSocket"""
        with patch('routes.chat_routes.get_conversation_service', return_value=mock_conversation_service):
            with client.websocket_connect("/api/chat/ws/session-123") as websocket:
                # Skip welcome message
                websocket.receive_json()
                
                # Send message
                websocket.send_json({"message": "Test message"})
                
                # Receive response
                data = websocket.receive_json()
                assert data["type"] == "question"
                assert "question" in data
    
    def test_websocket_investigation_complete(self, client, mock_conversation_service):
        """Test WebSocket when investigation completes"""
        mock_conversation_service.process_answer = AsyncMock(return_value=None)
        
        with patch('routes.chat_routes.get_conversation_service', return_value=mock_conversation_service):
            with client.websocket_connect("/api/chat/ws/session-123") as websocket:
                # Skip welcome message
                websocket.receive_json()
                
                # Send message
                websocket.send_json({"message": "Final answer"})
                
                # Receive completion
                data = websocket.receive_json()
                assert data["type"] == "complete"
    
    def test_websocket_session_not_found(self, client, mock_conversation_service):
        """Test WebSocket error when session not found"""
        mock_conversation_service.get_session.return_value = None
        
        with patch('routes.chat_routes.get_conversation_service', return_value=mock_conversation_service):
            with client.websocket_connect("/api/chat/ws/invalid-session") as websocket:
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert "Session not found" in data["message"]
    
    def test_websocket_missing_message_field(self, client, mock_conversation_service):
        """Test WebSocket error for invalid message format"""
        with patch('routes.chat_routes.get_conversation_service', return_value=mock_conversation_service):
            with client.websocket_connect("/api/chat/ws/session-123") as websocket:
                # Skip welcome message
                websocket.receive_json()
                
                # Send invalid data
                websocket.send_json({"invalid": "data"})
                
                # Receive error
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert "Missing 'message' field" in data["message"]


class TestResponseModels:
    """Test suite for response model validation"""
    
    def test_start_response_structure(self, client):
        """Test StartInvestigationResponse structure"""
        response = client.post("/api/chat/start", json={})
        
        assert response.status_code == 201
        data = response.json()
        
        required_fields = ["session_id", "question", "message"]
        for field in required_fields:
            assert field in data
    
    def test_message_response_structure(self, client):
        """Test MessageResponse structure"""
        response = client.post("/api/chat/message", json={
            "session_id": "session-123",
            "message": "Test"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["question", "complete", "message"]
        for field in required_fields:
            assert field in data
    
    def test_history_response_structure(self, client):
        """Test HistoryResponse structure"""
        response = client.get("/api/chat/history/session-123")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["session_id", "messages", "total_messages"]
        for field in required_fields:
            assert field in data
