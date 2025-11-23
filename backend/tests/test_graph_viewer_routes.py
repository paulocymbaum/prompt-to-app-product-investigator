"""
Tests for Graph Viewer API Routes - LangGraph integration endpoints
Tests cover all 5 API endpoints with comprehensive error handling and state synchronization
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from app import app
from services.graph_viewer_service import GraphViewerService
from storage.conversation_storage import ConversationStorage


@pytest.fixture
def mock_storage():
    """Mock ConversationStorage"""
    storage = Mock(spec=ConversationStorage)
    return storage


@pytest.fixture
def mock_viewer_service():
    """Mock GraphViewerService"""
    service = Mock(spec=GraphViewerService)
    return service


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def sample_state():
    """Sample LangGraph state"""
    return {
        "session_id": "test-session-123",
        "raw_graph_data": {
            "nodes": [
                {"id": "q1", "type": "question", "category": "initial_context", "content": "What is your project?", "timestamp": "2024-01-15T10:00:00"},
                {"id": "a1", "type": "answer", "category": "initial_context", "content": "A web app", "timestamp": "2024-01-15T10:01:00"},
                {"id": "q2", "type": "question", "category": "features", "content": "What features?", "timestamp": "2024-01-15T10:02:00"},
                {"id": "a2", "type": "answer", "category": "features", "content": "User auth", "timestamp": "2024-01-15T10:03:00"}
            ],
            "edges": [
                {"source": "q1", "target": "a1", "type": "answer"},
                {"source": "a1", "target": "q2", "type": "follow_up"},
                {"source": "q2", "target": "a2", "type": "answer"}
            ],
            "metadata": {
                "total_interactions": 2,
                "duration_minutes": 3,
                "categories": ["initial_context", "features"]
            }
        },
        "visible_nodes": [],
        "visible_edges": [],
        "selected_node_id": None,
        "selected_node_data": None,
        "active_categories": [],
        "search_query": "",
        "zoom_level": 1.0,
        "viewport_center": {"x": 0, "y": 0},
        "export_format": None,
        "export_data": None,
        "loading": False,
        "error": None,
        "metadata": {}
    }


class TestInitializeEndpoint:
    """Test GET /api/graph/viewer/initialize/{session_id}"""
    
    def test_initialize_success(self, client, mock_viewer_service, sample_state):
        """Test successful initialization"""
        session_id = "test-session-123"
        
        # Configure mock
        sample_state["visible_nodes"] = sample_state["raw_graph_data"]["nodes"]
        sample_state["visible_edges"] = sample_state["raw_graph_data"]["edges"]
        sample_state["metadata"] = sample_state["raw_graph_data"]["metadata"]
        mock_viewer_service.get_initial_state.return_value = sample_state
        
        # Override dependency
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.get(f"/api/graph/viewer/initialize/{session_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            assert "state" in data
            assert "nodes" in data
            assert "edges" in data
            assert "metadata" in data
            assert "filters" in data
            assert len(data["nodes"]) == 4
            assert len(data["edges"]) == 3
            
            # Verify service was called
            mock_viewer_service.get_initial_state.assert_called_once_with(session_id)
        finally:
            app.dependency_overrides.clear()
    
    def test_initialize_session_not_found(self, client, mock_viewer_service):
        """Test initialization with non-existent session"""
        session_id = "nonexistent-session"
        
        # Configure mock to return error
        error_state = {
            "session_id": session_id,
            "error": "Session not found",
            "loading": False,
            "raw_graph_data": None,
            "visible_nodes": [],
            "visible_edges": [],
            "metadata": {}
        }
        mock_viewer_service.get_initial_state.return_value = error_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.get(f"/api/graph/viewer/initialize/{session_id}")
            
            assert response.status_code == 404
            data = response.json()
            assert "error" in data
            assert "not found" in data["error"].lower()
        finally:
            app.dependency_overrides.clear()
    
    def test_initialize_empty_conversation(self, client, mock_viewer_service):
        """Test initialization with empty conversation"""
        session_id = "empty-session"
        
        empty_state = {
            "session_id": session_id,
            "raw_graph_data": {"nodes": [], "edges": [], "metadata": {"total_interactions": 0}},
            "visible_nodes": [],
            "visible_edges": [],
            "metadata": {"total_interactions": 0},
            "loading": False,
            "error": None
        }
        mock_viewer_service.get_initial_state.return_value = empty_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.get(f"/api/graph/viewer/initialize/{session_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["nodes"]) == 0
            assert len(data["edges"]) == 0
            assert data["metadata"]["total_interactions"] == 0
        finally:
            app.dependency_overrides.clear()
    
    def test_initialize_service_exception(self, client, mock_viewer_service):
        """Test initialization with service exception"""
        session_id = "error-session"
        
        mock_viewer_service.get_initial_state.side_effect = Exception("Database error")
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.get(f"/api/graph/viewer/initialize/{session_id}")
            
            assert response.status_code == 500
            data = response.json()
            assert "error" in data
        finally:
            app.dependency_overrides.clear()


class TestFilterEndpoint:
    """Test POST /api/graph/viewer/filter/{session_id}"""
    
    def test_filter_by_categories_success(self, client, mock_viewer_service, sample_state):
        """Test filtering by categories"""
        session_id = "test-session-123"
        filter_request = {
            "active_categories": ["features"],
            "search_query": ""
        }
        
        # Configure mock - only return "features" nodes
        filtered_state = sample_state.copy()
        filtered_state["visible_nodes"] = [
            {"id": "q2", "type": "question", "category": "features", "content": "What features?"},
            {"id": "a2", "type": "answer", "category": "features", "content": "User auth"}
        ]
        filtered_state["visible_edges"] = [
            {"source": "q2", "target": "a2", "type": "answer"}
        ]
        filtered_state["active_categories"] = ["features"]
        mock_viewer_service.update_filters.return_value = filtered_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/filter/{session_id}",
                json=filter_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["nodes"]) == 2
            assert all(node["category"] == "features" for node in data["nodes"])
            assert data["state"]["active_categories"] == ["features"]
        finally:
            app.dependency_overrides.clear()
    
    def test_filter_by_search_query(self, client, mock_viewer_service, sample_state):
        """Test filtering by search text"""
        session_id = "test-session-123"
        filter_request = {
            "active_categories": [],
            "search_query": "auth"
        }
        
        filtered_state = sample_state.copy()
        filtered_state["visible_nodes"] = [
            {"id": "a2", "type": "answer", "category": "features", "content": "User auth"}
        ]
        filtered_state["visible_edges"] = []
        filtered_state["search_query"] = "auth"
        mock_viewer_service.update_filters.return_value = filtered_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/filter/{session_id}",
                json=filter_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["nodes"]) == 1
            assert "auth" in data["nodes"][0]["content"].lower()
        finally:
            app.dependency_overrides.clear()
    
    def test_filter_combined_category_and_search(self, client, mock_viewer_service, sample_state):
        """Test combined filtering"""
        session_id = "test-session-123"
        filter_request = {
            "active_categories": ["features"],
            "search_query": "auth"
        }
        
        filtered_state = sample_state.copy()
        filtered_state["visible_nodes"] = [
            {"id": "a2", "type": "answer", "category": "features", "content": "User auth"}
        ]
        filtered_state["active_categories"] = ["features"]
        filtered_state["search_query"] = "auth"
        mock_viewer_service.update_filters.return_value = filtered_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/filter/{session_id}",
                json=filter_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["nodes"]) == 1
            assert data["nodes"][0]["category"] == "features"
            assert "auth" in data["nodes"][0]["content"].lower()
        finally:
            app.dependency_overrides.clear()
    
    def test_filter_session_not_found(self, client, mock_viewer_service):
        """Test filter with non-existent session"""
        session_id = "nonexistent"
        filter_request = {"active_categories": [], "search_query": ""}
        
        error_state = {"error": "Session not found", "visible_nodes": [], "visible_edges": []}
        mock_viewer_service.update_filters.return_value = error_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/filter/{session_id}",
                json=filter_request
            )
            
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestSelectNodeEndpoint:
    """Test POST /api/graph/viewer/select/{session_id}"""
    
    def test_select_node_success(self, client, mock_viewer_service, sample_state):
        """Test successful node selection"""
        session_id = "test-session-123"
        select_request = {"node_id": "q1"}
        
        selected_state = sample_state.copy()
        selected_state["selected_node_id"] = "q1"
        selected_state["selected_node_data"] = {
            "id": "q1",
            "type": "question",
            "category": "initial_context",
            "content": "What is your project?",
            "timestamp": "2024-01-15T10:00:00"
        }
        mock_viewer_service.select_node.return_value = selected_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/select/{session_id}",
                json=select_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["selected_node"]["id"] == "q1"
            assert data["selected_node"]["content"] == "What is your project?"
            assert data["state"]["selected_node_id"] == "q1"
        finally:
            app.dependency_overrides.clear()
    
    def test_select_node_not_found(self, client, mock_viewer_service, sample_state):
        """Test selecting non-existent node"""
        session_id = "test-session-123"
        select_request = {"node_id": "nonexistent"}
        
        error_state = sample_state.copy()
        error_state["error"] = "Node not found"
        error_state["selected_node_data"] = None
        mock_viewer_service.select_node.return_value = error_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/select/{session_id}",
                json=select_request
            )
            
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["error"].lower()
        finally:
            app.dependency_overrides.clear()
    
    def test_select_node_missing_node_id(self, client, mock_viewer_service):
        """Test select without node_id"""
        session_id = "test-session-123"
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/select/{session_id}",
                json={}
            )
            
            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()


class TestExportEndpoint:
    """Test POST /api/graph/viewer/export/{session_id}"""
    
    def test_export_json_format(self, client, mock_viewer_service, sample_state):
        """Test JSON export"""
        session_id = "test-session-123"
        export_request = {"format": "json"}
        
        export_state = sample_state.copy()
        export_state["export_format"] = "json"
        export_state["export_data"] = {
            "format": "json",
            "data": {
                "nodes": sample_state["raw_graph_data"]["nodes"],
                "edges": sample_state["raw_graph_data"]["edges"],
                "metadata": sample_state["raw_graph_data"]["metadata"]
            }
        }
        mock_viewer_service.export_graph.return_value = export_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/export/{session_id}",
                json=export_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["export_data"]["format"] == "json"
            assert "nodes" in data["export_data"]["data"]
            assert "edges" in data["export_data"]["data"]
        finally:
            app.dependency_overrides.clear()
    
    def test_export_mermaid_format(self, client, mock_viewer_service, sample_state):
        """Test Mermaid diagram export"""
        session_id = "test-session-123"
        export_request = {"format": "mermaid"}
        
        export_state = sample_state.copy()
        export_state["export_format"] = "mermaid"
        export_state["export_data"] = {
            "format": "mermaid",
            "data": "graph TD\n    q1[What is your project?]\n    a1[A web app]\n    q1 --> a1"
        }
        mock_viewer_service.export_graph.return_value = export_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/export/{session_id}",
                json=export_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["export_data"]["format"] == "mermaid"
            assert "graph TD" in data["export_data"]["data"]
        finally:
            app.dependency_overrides.clear()
    
    def test_export_statistics_format(self, client, mock_viewer_service, sample_state):
        """Test statistics export"""
        session_id = "test-session-123"
        export_request = {"format": "statistics"}
        
        export_state = sample_state.copy()
        export_state["export_format"] = "statistics"
        export_state["export_data"] = {
            "format": "statistics",
            "data": {
                "total_nodes": 4,
                "total_edges": 3,
                "categories": {"initial_context": 2, "features": 2},
                "node_types": {"question": 2, "answer": 2}
            }
        }
        mock_viewer_service.export_graph.return_value = export_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/export/{session_id}",
                json=export_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["export_data"]["format"] == "statistics"
            assert "total_nodes" in data["export_data"]["data"]
            assert "categories" in data["export_data"]["data"]
        finally:
            app.dependency_overrides.clear()
    
    def test_export_invalid_format(self, client, mock_viewer_service, sample_state):
        """Test export with invalid format"""
        session_id = "test-session-123"
        export_request = {"format": "invalid_format"}
        
        error_state = sample_state.copy()
        error_state["error"] = "Invalid export format"
        mock_viewer_service.export_graph.return_value = error_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/export/{session_id}",
                json=export_request
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "format" in data["error"].lower()
        finally:
            app.dependency_overrides.clear()


class TestViewportEndpoint:
    """Test POST /api/graph/viewer/viewport/{session_id}"""
    
    def test_update_zoom_level(self, client, mock_viewer_service, sample_state):
        """Test updating zoom level"""
        session_id = "test-session-123"
        viewport_request = {
            "zoom_level": 1.5,
            "viewport_center": None
        }
        
        viewport_state = sample_state.copy()
        viewport_state["zoom_level"] = 1.5
        mock_viewer_service.update_viewport.return_value = viewport_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/viewport/{session_id}",
                json=viewport_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["viewport"]["zoom_level"] == 1.5
        finally:
            app.dependency_overrides.clear()
    
    def test_update_viewport_center(self, client, mock_viewer_service, sample_state):
        """Test updating viewport center"""
        session_id = "test-session-123"
        viewport_request = {
            "zoom_level": None,
            "viewport_center": {"x": 100, "y": 200}
        }
        
        viewport_state = sample_state.copy()
        viewport_state["viewport_center"] = {"x": 100, "y": 200}
        mock_viewer_service.update_viewport.return_value = viewport_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/viewport/{session_id}",
                json=viewport_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["viewport"]["viewport_center"]["x"] == 100
            assert data["viewport"]["viewport_center"]["y"] == 200
        finally:
            app.dependency_overrides.clear()
    
    def test_update_viewport_both(self, client, mock_viewer_service, sample_state):
        """Test updating both zoom and center"""
        session_id = "test-session-123"
        viewport_request = {
            "zoom_level": 2.0,
            "viewport_center": {"x": 50, "y": 75}
        }
        
        viewport_state = sample_state.copy()
        viewport_state["zoom_level"] = 2.0
        viewport_state["viewport_center"] = {"x": 50, "y": 75}
        mock_viewer_service.update_viewport.return_value = viewport_state
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            response = client.post(
                f"/api/graph/viewer/viewport/{session_id}",
                json=viewport_request
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["viewport"]["zoom_level"] == 2.0
            assert data["viewport"]["viewport_center"]["x"] == 50
        finally:
            app.dependency_overrides.clear()


class TestStateSynchronization:
    """Test state synchronization across endpoints"""
    
    def test_state_persistence_across_operations(self, client, mock_viewer_service, sample_state):
        """Test that state persists across multiple operations"""
        session_id = "test-session-123"
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            # Initialize
            initial_state = sample_state.copy()
            initial_state["visible_nodes"] = sample_state["raw_graph_data"]["nodes"]
            initial_state["visible_edges"] = sample_state["raw_graph_data"]["edges"]
            mock_viewer_service.get_initial_state.return_value = initial_state
            
            init_response = client.get(f"/api/graph/viewer/initialize/{session_id}")
            assert init_response.status_code == 200
            
            # Filter
            filtered_state = initial_state.copy()
            filtered_state["active_categories"] = ["features"]
            filtered_state["visible_nodes"] = [n for n in initial_state["visible_nodes"] if n["category"] == "features"]
            mock_viewer_service.update_filters.return_value = filtered_state
            
            filter_response = client.post(
                f"/api/graph/viewer/filter/{session_id}",
                json={"active_categories": ["features"], "search_query": ""}
            )
            assert filter_response.status_code == 200
            assert filter_response.json()["state"]["active_categories"] == ["features"]
            
            # Verify state was maintained
            mock_viewer_service.update_filters.assert_called_once()
        finally:
            app.dependency_overrides.clear()
    
    def test_error_handling_preserves_state(self, client, mock_viewer_service, sample_state):
        """Test that errors don't corrupt state"""
        session_id = "test-session-123"
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            # Valid operation
            mock_viewer_service.get_initial_state.return_value = sample_state
            init_response = client.get(f"/api/graph/viewer/initialize/{session_id}")
            assert init_response.status_code == 200
            
            # Error operation
            error_state = sample_state.copy()
            error_state["error"] = "Node not found"
            mock_viewer_service.select_node.return_value = error_state
            
            error_response = client.post(
                f"/api/graph/viewer/select/{session_id}",
                json={"node_id": "nonexistent"}
            )
            assert error_response.status_code == 404
            
            # State should still be accessible
            mock_viewer_service.get_initial_state.return_value = sample_state
            recovery_response = client.get(f"/api/graph/viewer/initialize/{session_id}")
            assert recovery_response.status_code == 200
        finally:
            app.dependency_overrides.clear()


class TestConcurrency:
    """Test concurrent requests handling"""
    
    def test_concurrent_filter_requests(self, client, mock_viewer_service, sample_state):
        """Test multiple filter requests don't interfere"""
        session_id = "test-session-123"
        
        from routes.graph_viewer_routes import get_graph_viewer_service
        app.dependency_overrides[get_graph_viewer_service] = lambda: mock_viewer_service
        
        try:
            filtered_state = sample_state.copy()
            filtered_state["active_categories"] = ["features"]
            mock_viewer_service.update_filters.return_value = filtered_state
            
            # Make multiple requests
            response1 = client.post(
                f"/api/graph/viewer/filter/{session_id}",
                json={"active_categories": ["features"], "search_query": ""}
            )
            response2 = client.post(
                f"/api/graph/viewer/filter/{session_id}",
                json={"active_categories": ["features"], "search_query": ""}
            )
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            assert response1.json()["state"]["active_categories"] == ["features"]
            assert response2.json()["state"]["active_categories"] == ["features"]
        finally:
            app.dependency_overrides.clear()
