"""
Tests for GraphViewerService - LangGraph StateGraph implementation
Tests cover state graph structure, all nodes, routing logic, and public API methods
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from services.graph_viewer_service import GraphViewerService, GraphViewerState
from services.graph_service import GraphService
from storage.conversation_storage import ConversationStorage


@pytest.fixture
def mock_storage():
    """Mock ConversationStorage"""
    storage = Mock(spec=ConversationStorage)
    return storage


@pytest.fixture
def mock_graph_service():
    """Mock GraphService"""
    service = Mock(spec=GraphService)
    return service


@pytest.fixture
def viewer_service(mock_storage):
    """GraphViewerService instance with mocked dependencies"""
    with patch('services.graph_viewer_service.GraphService') as mock_gs:
        with patch('services.graph_viewer_service.ConversationStorage') as mock_cs:
            mock_cs.return_value = mock_storage
            service = GraphViewerService(storage=mock_storage)
            return service


@pytest.fixture
def sample_graph_data():
    """Sample graph data from GraphService"""
    return {
        "nodes": [
            {
                "id": "q1",
                "type": "question",
                "category": "initial_context",
                "content": "What is your project about?",
                "timestamp": "2024-01-15T10:00:00"
            },
            {
                "id": "a1",
                "type": "answer",
                "category": "initial_context",
                "content": "A web application",
                "timestamp": "2024-01-15T10:01:00"
            },
            {
                "id": "q2",
                "type": "question",
                "category": "features",
                "content": "What features do you need?",
                "timestamp": "2024-01-15T10:02:00"
            },
            {
                "id": "a2",
                "type": "answer",
                "category": "features",
                "content": "User authentication and dashboard",
                "timestamp": "2024-01-15T10:03:00"
            }
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
    }


class TestStateGraphStructure:
    """Test StateGraph structure and initialization"""
    
    def test_build_state_graph_has_correct_nodes(self, viewer_service):
        """Test that StateGraph has all 5 required nodes"""
        state_graph = viewer_service.state_graph
        
        # Verify nodes exist in the graph
        # Note: LangGraph doesn't expose nodes directly, but we can test by invoking
        assert state_graph is not None
        assert hasattr(viewer_service, '_fetch_graph_node')
        assert hasattr(viewer_service, '_filter_nodes_node')
        assert hasattr(viewer_service, '_select_node_node')
        assert hasattr(viewer_service, '_export_graph_node')
        assert hasattr(viewer_service, '_update_viewport_node')
    
    def test_state_graph_routing_function_exists(self, viewer_service):
        """Test that routing function is defined"""
        assert hasattr(viewer_service, '_route_after_filter')
    
    def test_service_has_required_dependencies(self, viewer_service, mock_storage):
        """Test service has required dependencies injected"""
        assert viewer_service.storage == mock_storage
        assert hasattr(viewer_service, 'graph_service')


class TestFetchGraphNode:
    """Test _fetch_graph_node - entry point for loading graph data"""
    
    def test_fetch_graph_success(self, viewer_service, sample_graph_data):
        """Test successful graph fetch"""
        session_id = "test-session-123"
        
        # Mock GraphService.generate_conversation_graph
        with patch.object(viewer_service.graph_service, 'generate_conversation_graph', return_value=sample_graph_data):
            state: GraphViewerState = {
                "session_id": session_id,
                "raw_graph_data": None,
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
                "loading": True,
                "error": None,
                "metadata": {}
            }
            
            result = viewer_service._fetch_graph_node(state)
            
            assert result["raw_graph_data"] == sample_graph_data
            assert result["visible_nodes"] == sample_graph_data["nodes"]
            assert result["visible_edges"] == sample_graph_data["edges"]
            assert result["metadata"] == sample_graph_data["metadata"]
            assert result["loading"] is False
            assert result["error"] is None
    
    def test_fetch_graph_session_not_found(self, viewer_service):
        """Test fetch when session doesn't exist"""
        session_id = "nonexistent-session"
        
        # Mock GraphService to raise error
        with patch.object(viewer_service.graph_service, 'generate_conversation_graph', side_effect=ValueError("Session not found")):
            state: GraphViewerState = {
                "session_id": session_id,
                "raw_graph_data": None,
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
                "loading": True,
                "error": None,
                "metadata": {}
            }
            
            result = viewer_service._fetch_graph_node(state)
            
            assert result["error"] is not None
            assert "Session not found" in result["error"]
            assert result["loading"] is False
    
    def test_fetch_graph_empty_conversation(self, viewer_service):
        """Test fetch with empty conversation (no interactions)"""
        session_id = "empty-session"
        empty_graph = {
            "nodes": [],
            "edges": [],
            "metadata": {"total_interactions": 0, "duration_minutes": 0, "categories": []}
        }
        
        with patch.object(viewer_service.graph_service, 'generate_conversation_graph', return_value=empty_graph):
            state: GraphViewerState = {
                "session_id": session_id,
                "raw_graph_data": None,
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
                "loading": True,
                "error": None,
                "metadata": {}
            }
            
            result = viewer_service._fetch_graph_node(state)
            
            assert result["visible_nodes"] == []
            assert result["visible_edges"] == []
            assert result["metadata"]["total_interactions"] == 0


class TestFilterNodesNode:
    """Test _filter_nodes_node - category and search filtering"""
    
    def test_filter_by_category_only(self, viewer_service, sample_graph_data):
        """Test filtering by single category"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": ["features"],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": None,
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._filter_nodes_node(state)
        
        # Should only include nodes with category "features"
        filtered_nodes = result["visible_nodes"]
        assert len(filtered_nodes) == 2
        assert all(node["category"] == "features" for node in filtered_nodes)
    
    def test_filter_by_multiple_categories(self, viewer_service, sample_graph_data):
        """Test filtering by multiple categories"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": ["initial_context", "features"],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": None,
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._filter_nodes_node(state)
        
        # Should include all nodes
        filtered_nodes = result["visible_nodes"]
        assert len(filtered_nodes) == 4
    
    def test_filter_by_search_query(self, viewer_service, sample_graph_data):
        """Test filtering by search text"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "authentication",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": None,
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._filter_nodes_node(state)
        
        # Should only include nodes with "authentication" in content
        filtered_nodes = result["visible_nodes"]
        assert len(filtered_nodes) == 1
        assert "authentication" in filtered_nodes[0]["content"].lower()
    
    def test_filter_by_category_and_search(self, viewer_service, sample_graph_data):
        """Test combined category and search filtering"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": ["features"],
            "search_query": "features",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": None,
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._filter_nodes_node(state)
        
        # Should match nodes in "features" category AND containing "features" text
        filtered_nodes = result["visible_nodes"]
        assert len(filtered_nodes) == 1
        assert filtered_nodes[0]["id"] == "q2"
    
    def test_filter_updates_edges(self, viewer_service, sample_graph_data):
        """Test that edges are filtered to only connect visible nodes"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": ["features"],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": None,
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._filter_nodes_node(state)
        
        # Should only include edge between q2 and a2 (both in "features")
        filtered_edges = result["visible_edges"]
        visible_node_ids = {node["id"] for node in result["visible_nodes"]}
        
        for edge in filtered_edges:
            assert edge["source"] in visible_node_ids
            assert edge["target"] in visible_node_ids


class TestSelectNodeNode:
    """Test _select_node_node - load full node details"""
    
    def test_select_node_success(self, viewer_service, sample_graph_data):
        """Test successful node selection"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": "q1",
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": None,
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._select_node_node(state)
        
        assert result["selected_node_data"] is not None
        assert result["selected_node_data"]["id"] == "q1"
        assert result["selected_node_data"]["content"] == "What is your project about?"
    
    def test_select_node_not_found(self, viewer_service, sample_graph_data):
        """Test selecting non-existent node"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": "nonexistent",
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": None,
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._select_node_node(state)
        
        assert result["error"] is not None
        assert "not found" in result["error"].lower()


class TestExportGraphNode:
    """Test _export_graph_node - export in various formats"""
    
    def test_export_json_format(self, viewer_service, sample_graph_data):
        """Test JSON export"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": "json",
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._export_graph_node(state)
        
        assert result["export_data"] is not None
        export_data = result["export_data"]
        assert export_data["format"] == "json"
        assert "nodes" in export_data["data"]
        assert "edges" in export_data["data"]
    
    def test_export_mermaid_format(self, viewer_service, sample_graph_data):
        """Test Mermaid diagram export"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": "mermaid",
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._export_graph_node(state)
        
        assert result["export_data"] is not None
        export_data = result["export_data"]
        assert export_data["format"] == "mermaid"
        assert "graph TD" in export_data["data"] or "flowchart TD" in export_data["data"]
    
    def test_export_statistics_format(self, viewer_service, sample_graph_data):
        """Test statistics export"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": "statistics",
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._export_graph_node(state)
        
        assert result["export_data"] is not None
        export_data = result["export_data"]
        assert export_data["format"] == "statistics"
        assert "total_nodes" in export_data["data"]
        assert "total_edges" in export_data["data"]
        assert "categories" in export_data["data"]
    
    def test_export_invalid_format(self, viewer_service, sample_graph_data):
        """Test export with invalid format"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": "invalid_format",
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._export_graph_node(state)
        
        assert result["error"] is not None
        assert "format" in result["error"].lower()


class TestUpdateViewportNode:
    """Test _update_viewport_node - zoom and pan state"""
    
    def test_update_zoom_level(self, viewer_service, sample_graph_data):
        """Test updating zoom level"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "",
            "zoom_level": 1.5,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": None,
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._update_viewport_node(state)
        
        assert result["zoom_level"] == 1.5
    
    def test_update_viewport_center(self, viewer_service, sample_graph_data):
        """Test updating viewport center position"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 100, "y": 200},
            "export_format": None,
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        result = viewer_service._update_viewport_node(state)
        
        assert result["viewport_center"]["x"] == 100
        assert result["viewport_center"]["y"] == 200


class TestRouting:
    """Test _route_after_filter - conditional routing logic"""
    
    def test_route_to_select_node(self, viewer_service, sample_graph_data):
        """Test routing to select_node when node is selected"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": "q1",
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": None,
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        next_node = viewer_service._route_after_filter(state)
        assert next_node == "select_node"
    
    def test_route_to_export_graph(self, viewer_service, sample_graph_data):
        """Test routing to export_graph when export format is set"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "",
            "zoom_level": 1.0,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": "json",
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        next_node = viewer_service._route_after_filter(state)
        assert next_node == "export_graph"
    
    def test_route_to_update_viewport(self, viewer_service, sample_graph_data):
        """Test routing to update_viewport when zoom changes"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
            "selected_node_id": None,
            "selected_node_data": None,
            "active_categories": [],
            "search_query": "",
            "zoom_level": 1.5,
            "viewport_center": {"x": 0, "y": 0},
            "export_format": None,
            "export_data": None,
            "loading": False,
            "error": None,
            "metadata": sample_graph_data["metadata"]
        }
        
        next_node = viewer_service._route_after_filter(state)
        # Should route to update_viewport if zoom != 1.0
        assert next_node == "update_viewport"
    
    def test_route_to_end(self, viewer_service, sample_graph_data):
        """Test routing to END when no actions pending"""
        state: GraphViewerState = {
            "session_id": "test",
            "raw_graph_data": sample_graph_data,
            "visible_nodes": sample_graph_data["nodes"],
            "visible_edges": sample_graph_data["edges"],
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
            "metadata": sample_graph_data["metadata"]
        }
        
        next_node = viewer_service._route_after_filter(state)
        assert next_node == "END"


class TestPublicAPI:
    """Test public API methods"""
    
    def test_get_initial_state(self, viewer_service, sample_graph_data):
        """Test get_initial_state initializes properly"""
        session_id = "test-session"
        
        with patch.object(viewer_service.graph_service, 'generate_conversation_graph', return_value=sample_graph_data):
            state = viewer_service.get_initial_state(session_id)
            
            assert state["session_id"] == session_id
            assert state["raw_graph_data"] == sample_graph_data
            assert len(state["visible_nodes"]) == 4
            assert state["loading"] is False
    
    def test_update_filters_integration(self, viewer_service, sample_graph_data):
        """Test update_filters full workflow"""
        session_id = "test-session"
        
        with patch.object(viewer_service.graph_service, 'generate_conversation_graph', return_value=sample_graph_data):
            # Initialize first
            initial_state = viewer_service.get_initial_state(session_id)
            
            # Update filters
            filtered_state = viewer_service.update_filters(
                session_id=session_id,
                active_categories=["features"],
                search_query="",
                current_state=initial_state
            )
            
            assert len(filtered_state["visible_nodes"]) == 2
            assert all(node["category"] == "features" for node in filtered_state["visible_nodes"])
    
    def test_select_node_integration(self, viewer_service, sample_graph_data):
        """Test select_node full workflow"""
        session_id = "test-session"
        
        with patch.object(viewer_service.graph_service, 'generate_conversation_graph', return_value=sample_graph_data):
            # Initialize first
            initial_state = viewer_service.get_initial_state(session_id)
            
            # Select node
            selected_state = viewer_service.select_node(
                session_id=session_id,
                node_id="q1",
                current_state=initial_state
            )
            
            assert selected_state["selected_node_id"] == "q1"
            assert selected_state["selected_node_data"] is not None
            assert selected_state["selected_node_data"]["id"] == "q1"
    
    def test_export_graph_integration(self, viewer_service, sample_graph_data):
        """Test export_graph full workflow"""
        session_id = "test-session"
        
        with patch.object(viewer_service.graph_service, 'generate_conversation_graph', return_value=sample_graph_data):
            # Initialize first
            initial_state = viewer_service.get_initial_state(session_id)
            
            # Export
            export_state = viewer_service.export_graph(
                session_id=session_id,
                export_format="json",
                current_state=initial_state
            )
            
            assert export_state["export_format"] == "json"
            assert export_state["export_data"] is not None
    
    def test_update_viewport_integration(self, viewer_service, sample_graph_data):
        """Test update_viewport full workflow"""
        session_id = "test-session"
        
        with patch.object(viewer_service.graph_service, 'generate_conversation_graph', return_value=sample_graph_data):
            # Initialize first
            initial_state = viewer_service.get_initial_state(session_id)
            
            # Update viewport
            viewport_state = viewer_service.update_viewport(
                session_id=session_id,
                zoom_level=1.5,
                viewport_center={"x": 100, "y": 200},
                current_state=initial_state
            )
            
            assert viewport_state["zoom_level"] == 1.5
            assert viewport_state["viewport_center"]["x"] == 100
            assert viewport_state["viewport_center"]["y"] == 200
