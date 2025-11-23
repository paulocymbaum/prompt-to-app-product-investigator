"""
Tests for Graph API Routes

Comprehensive test suite for graph visualization endpoints.
"""

import pytest
from httpx import AsyncClient
from app import app
from storage.conversation_storage import ConversationStorage
from services.graph_service import GraphService
from routes.graph_routes import get_graph_service
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_storage_dir():
    """Create temporary directory for test storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
async def sample_session(temp_storage_dir):
    """Create a sample conversation session."""
    storage = ConversationStorage(base_dir=temp_storage_dir)
    session_id = "test_graph_session"
    
    # Create conversation with multiple interactions
    interactions = [
        {
            "question": "What is the main functionality?",
            "answer": "A task management app",
            "metadata": {"category": "functionality"}
        },
        {
            "question": "Who are the target users?",
            "answer": "Software engineers",
            "metadata": {"category": "users"}
        },
        {
            "question": "What technology stack?",
            "answer": "Python and React",
            "metadata": {"category": "technical"}
        }
    ]
    
    for interaction in interactions:
        await storage.save_interaction(
            session_id=session_id,
            question=interaction["question"],
            answer=interaction["answer"],
            metadata=interaction["metadata"]
        )
    
    # Override dependency for all tests
    def override_get_graph_service():
        return GraphService(storage=storage)
    
    app.dependency_overrides[get_graph_service] = override_get_graph_service
    
    yield session_id, storage
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_visualization_success(sample_session):
    """Test successful graph visualization retrieval."""
    session_id, storage = sample_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/graph/visualization/{session_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "metadata" in data
        
        # Should have 6 nodes (3 questions + 3 answers)
        assert len(data["nodes"]) == 6
        
        # Should have 5 edges (3 Q->A + 2 A->Q)
        assert len(data["edges"]) == 5
        
        # Check metadata
        assert data["metadata"]["session_id"] == session_id
        assert data["metadata"]["total_interactions"] == 3


@pytest.mark.asyncio
async def test_get_visualization_node_structure(sample_session):
    """Test that nodes have correct structure."""
    session_id, storage = sample_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/graph/visualization/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        for node in data["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "content" in node
            assert "category" in node
            assert "color" in node
            assert "timestamp" in node
            assert "shape" in node
            
            assert node["type"] in ["question", "answer"]
            assert node["color"].startswith("#")


@pytest.mark.asyncio
async def test_get_visualization_edge_structure(sample_session):
    """Test that edges have correct structure."""
    session_id, storage = sample_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/graph/visualization/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        for edge in data["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "label" in edge
            
            assert edge["label"] in ["answer", "next"]


@pytest.mark.asyncio
async def test_get_visualization_not_found():
    """Test 404 when session doesn't exist."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/graph/visualization/nonexistent_session")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "nonexistent_session" in data["detail"]


@pytest.mark.asyncio
async def test_get_mermaid_success(sample_session):
    """Test successful Mermaid diagram generation."""
    session_id, storage = sample_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/graph/mermaid/{session_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "mermaid" in data
        assert "session_id" in data
        
        mermaid = data["mermaid"]
        assert mermaid.startswith("graph TD")
        assert "q0" in mermaid
        assert "a0" in mermaid
        assert "-->" in mermaid
        assert "style" in mermaid


@pytest.mark.asyncio
async def test_get_mermaid_format_validity(sample_session):
    """Test that Mermaid format is valid."""
    session_id, storage = sample_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/graph/mermaid/{session_id}")
        
        assert response.status_code == 200
        mermaid = response.json()["mermaid"]
        
        # Check for required Mermaid elements
        assert "graph TD" in mermaid  # Graph declaration
        assert "[" in mermaid or "(" in mermaid  # Node definitions
        assert "fill:" in mermaid  # Styling
        assert "|" in mermaid or "-->" in mermaid  # Edges


@pytest.mark.asyncio
async def test_get_mermaid_not_found():
    """Test 404 when session doesn't exist for Mermaid."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/graph/mermaid/nonexistent_session")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_get_statistics_success(sample_session):
    """Test successful statistics retrieval."""
    session_id, storage = sample_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/graph/statistics/{session_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "total_nodes" in data
        assert "total_edges" in data
        assert "question_count" in data
        assert "answer_count" in data
        assert "category_distribution" in data
        assert "metadata" in data
        
        assert data["total_nodes"] == 6
        assert data["total_edges"] == 5
        assert data["question_count"] == 3
        assert data["answer_count"] == 3


@pytest.mark.asyncio
async def test_get_statistics_category_distribution(sample_session):
    """Test that category distribution is calculated correctly."""
    session_id, storage = sample_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/graph/statistics/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        dist = data["category_distribution"]
        
        # Should have 3 categories (one of each)
        assert "functionality" in dist
        assert "users" in dist
        assert "technical" in dist
        
        # Each should have 1 question
        assert dist["functionality"] == 1
        assert dist["users"] == 1
        assert dist["technical"] == 1


@pytest.mark.asyncio
async def test_get_statistics_not_found():
    """Test 404 when session doesn't exist for statistics."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/graph/statistics/nonexistent_session")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_all_endpoints_return_same_session_id(sample_session):
    """Test that all endpoints return consistent session_id."""
    session_id, storage = sample_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Get visualization
        viz_response = await client.get(f"/api/graph/visualization/{session_id}")
        assert viz_response.json()["metadata"]["session_id"] == session_id
        
        # Get Mermaid
        mermaid_response = await client.get(f"/api/graph/mermaid/{session_id}")
        assert mermaid_response.json()["session_id"] == session_id
        
        # Get statistics
        stats_response = await client.get(f"/api/graph/statistics/{session_id}")
        assert stats_response.json()["metadata"]["session_id"] == session_id


@pytest.mark.asyncio
async def test_visualization_with_large_conversation(temp_storage_dir):
    """Test visualization endpoint with large conversation."""
    storage = ConversationStorage(base_dir=temp_storage_dir)
    session_id = "test_large_graph"
    
    # Create 20 interactions
    for i in range(20):
        await storage.save_interaction(
            session_id=session_id,
            question=f"Question {i}?",
            answer=f"Answer {i}",
            metadata={"category": "functionality"}
        )
    
    # Override dependency
    def override_get_graph_service():
        return GraphService(storage=storage)
    app.dependency_overrides[get_graph_service] = override_get_graph_service
    
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(f"/api/graph/visualization/{session_id}")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have 40 nodes (20 questions + 20 answers)
            assert len(data["nodes"]) == 40
            
            # Should have 39 edges (20 Q->A + 19 A->Q)
            assert len(data["edges"]) == 39
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_mermaid_with_special_characters(temp_storage_dir):
    """Test Mermaid export handles special characters."""
    storage = ConversationStorage(base_dir=temp_storage_dir)
    session_id = "test_special_chars"
    
    await storage.save_interaction(
        session_id=session_id,
        question='What about "quotes" and \n newlines?',
        answer='Testing "special" characters',
        metadata={"category": "functionality"}
    )
    
    # Override dependency
    def override_get_graph_service():
        return GraphService(storage=storage)
    app.dependency_overrides[get_graph_service] = override_get_graph_service
    
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(f"/api/graph/mermaid/{session_id}")
            
            assert response.status_code == 200
            mermaid = response.json()["mermaid"]
            
            # Should have escaped content
            assert "graph TD" in mermaid
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_concurrent_requests(sample_session):
    """Test that concurrent requests don't interfere."""
    import asyncio
    
    session_id, storage = sample_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make 5 concurrent requests
        tasks = [
            client.get(f"/api/graph/visualization/{session_id}")
            for _ in range(5)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert len(data["nodes"]) == 6


@pytest.mark.asyncio
async def test_endpoint_response_time(sample_session):
    """Test that endpoints respond quickly."""
    import time
    
    session_id, storage = sample_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        start = time.time()
        response = await client.get(f"/api/graph/visualization/{session_id}")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Should respond in less than 1 second
        assert elapsed < 1.0


@pytest.mark.asyncio
async def test_visualization_json_serializable(sample_session):
    """Test that visualization response is JSON serializable."""
    import json
    
    session_id, storage = sample_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/graph/visualization/{session_id}")
        
        assert response.status_code == 200
        
        # Should be able to serialize and deserialize
        data = response.json()
        json_str = json.dumps(data)
        restored = json.loads(json_str)
        
        assert restored["metadata"]["session_id"] == session_id


@pytest.mark.asyncio
async def test_error_handling_invalid_session_format():
    """Test error handling with invalid session format."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try with various invalid formats
        invalid_sessions = ["   ", "../../../etc/passwd"]
        
        for invalid in invalid_sessions:
            response = await client.get(f"/api/graph/visualization/{invalid}")
            # Should either be 404 or 500, but not crash
            assert response.status_code in [404, 500]
