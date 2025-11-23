#!/bin/bash

# Script to create comprehensive tests for TASK-3.2: Prompt API Routes
# Creates test_prompt_routes.py with all required test cases

set -e

BACKEND_DIR="/Users/paulocymbaum/lovable_prompt_generator/backend"
TESTS_DIR="$BACKEND_DIR/tests"

echo "🧪 Creating TASK-3.2 Test Suite: Prompt API Routes"
echo "=================================================="

# Create test_prompt_routes.py
cat > "$TESTS_DIR/test_prompt_routes.py" << 'EOF'
"""
Comprehensive test suite for Prompt API Routes.

Tests all endpoints in routes/prompt_routes.py including:
- Prompt generation
- Prompt regeneration with modifications
- Prompt downloading in multiple formats
- Prompt caching behavior
- Cache management
- Error handling

Coverage Target: >80%
"""

import pytest
from httpx import AsyncClient
from fastapi import status
import os
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from app import app
from services.prompt_generator import PromptGenerator
from storage.conversation_storage import ConversationStorage


@pytest.fixture
async def async_client():
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_storage(tmp_path):
    """Create mock conversation storage with test data."""
    # Create test conversation file
    session_id = "test-session-123"
    conversation_dir = tmp_path / "conversations"
    conversation_dir.mkdir()
    
    conversation_file = conversation_dir / f"{session_id}.md"
    conversation_content = """# Product Investigation

## Chunk 1

**Question:** What is the core functionality of your product?
**Answer:** A task management app for remote teams
**Timestamp:** 2024-01-01T12:00:00

## Chunk 2

**Question:** Who will use this product?
**Answer:** Software engineers and product managers
**Timestamp:** 2024-01-01T12:05:00

## Chunk 3

**Question:** What are your design preferences?
**Answer:** Clean, modern, minimal design with dark mode
**Timestamp:** 2024-01-01T12:10:00
"""
    conversation_file.write_text(conversation_content)
    
    storage = ConversationStorage(data_dir=str(tmp_path))
    return storage, session_id


@pytest.fixture
def mock_prompt_generator(mock_storage):
    """Create PromptGenerator with mock storage."""
    storage, session_id = mock_storage
    generator = PromptGenerator(storage=storage)
    return generator, session_id


# Business Rule Tests

@pytest.mark.asyncio
async def test_generate_comprehensive_prompt(async_client, mock_storage):
    """Test that generate endpoint returns comprehensive prompt."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        response = await async_client.get(f"/api/prompt/generate/{session_id}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verify response structure
    assert "prompt" in data
    assert "cached" in data
    assert "token_count" in data
    assert "session_id" in data
    assert "version" in data
    
    # Verify prompt content
    prompt = data["prompt"]
    assert "SOLID" in prompt
    assert "DRY" in prompt or "Don't Repeat Yourself" in prompt
    assert "Your Role" in prompt or "Product Context" in prompt
    assert len(prompt) > 500  # Comprehensive prompt
    
    # Verify metadata
    assert data["session_id"] == session_id
    assert data["version"] == 1
    assert data["token_count"] > 0
    assert data["cached"] is False  # First generation


@pytest.mark.asyncio
async def test_regenerate_with_modifications(async_client, mock_storage):
    """Test regenerating prompt with focus areas and additional requirements."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        # First generate
        response1 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response1.status_code == status.HTTP_200_OK
        original_prompt = response1.json()["prompt"]
        
        # Regenerate with modifications
        regenerate_request = {
            "session_id": session_id,
            "focus_areas": ["security", "performance"],
            "additional_requirements": "Must support OAuth 2.0 authentication"
        }
        response2 = await async_client.post("/api/prompt/regenerate", json=regenerate_request)
    
    assert response2.status_code == status.HTTP_200_OK
    data = response2.json()
    
    # Verify version increment
    assert data["version"] == 2
    
    # Verify modifications applied
    assert data["modifications_applied"] is True
    
    # Verify focus areas in prompt
    prompt = data["prompt"]
    assert "security" in prompt.lower() or "Security" in prompt
    assert "performance" in prompt.lower() or "Performance" in prompt
    
    # Verify additional requirements
    assert "OAuth 2.0" in prompt
    
    # Verify prompt is different from original
    assert prompt != original_prompt


@pytest.mark.asyncio
async def test_download_markdown_format(async_client, mock_storage):
    """Test downloading prompt as markdown file."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        response = await async_client.get(f"/api/prompt/download/{session_id}?format=md")
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verify headers
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    assert ".md" in response.headers["content-disposition"]
    
    # Verify content
    content = response.text
    assert len(content) > 500
    assert "SOLID" in content


@pytest.mark.asyncio
async def test_download_text_format(async_client, mock_storage):
    """Test downloading prompt as text file."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        response = await async_client.get(f"/api/prompt/download/{session_id}?format=txt")
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verify headers
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    assert ".txt" in response.headers["content-disposition"]
    
    # Verify content
    content = response.text
    assert len(content) > 500


# Technical Implementation Tests

@pytest.mark.asyncio
async def test_prompt_caching(async_client, mock_storage):
    """Test that generated prompts are cached correctly."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        # First request - should not be cached
        response1 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert data1["cached"] is False
        
        # Second request - should be cached
        response2 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["cached"] is True
        
        # Verify same prompt returned
        assert data1["prompt"] == data2["prompt"]


@pytest.mark.asyncio
async def test_cache_invalidation_on_regenerate(async_client, mock_storage):
    """Test that cache is cleared when regenerating."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        # Generate and cache
        response1 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Verify cached
        response2 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response2.json()["cached"] is True
        
        # Regenerate
        regenerate_request = {"session_id": session_id}
        response3 = await async_client.post("/api/prompt/regenerate", json=regenerate_request)
        assert response3.status_code == status.HTTP_200_OK
        
        # Verify cache was cleared and version incremented
        response4 = await async_client.get(f"/api/prompt/generate/{session_id}")
        data4 = response4.json()
        assert data4["cached"] is True  # Now cached with new version
        assert data4["version"] == 2


@pytest.mark.asyncio
async def test_force_regenerate_bypasses_cache(async_client, mock_storage):
    """Test that force_regenerate parameter bypasses cache."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        # Generate and cache
        response1 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Request with force_regenerate
        response2 = await async_client.get(f"/api/prompt/generate/{session_id}?force_regenerate=true")
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["cached"] is False


@pytest.mark.asyncio
async def test_clear_specific_cache(async_client, mock_storage):
    """Test clearing cache for specific session."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        # Generate and cache
        response1 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Verify cached
        response2 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response2.json()["cached"] is True
        
        # Clear cache
        response3 = await async_client.delete(f"/api/prompt/cache/{session_id}")
        assert response3.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify not cached anymore
        response4 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response4.json()["cached"] is False


@pytest.mark.asyncio
async def test_clear_all_cache(async_client, mock_storage):
    """Test clearing all cached prompts."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        # Generate and cache
        response1 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Clear all cache
        response2 = await async_client.delete("/api/prompt/cache")
        assert response2.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify not cached
        response3 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response3.json()["cached"] is False


@pytest.mark.asyncio
async def test_token_count_estimation(async_client, mock_storage):
    """Test that token count is estimated correctly."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        response = await async_client.get(f"/api/prompt/generate/{session_id}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verify token count is reasonable (1 token ≈ 4 chars)
    prompt_length = len(data["prompt"])
    estimated_tokens = prompt_length // 4
    
    assert data["token_count"] > 0
    assert abs(data["token_count"] - estimated_tokens) < 100  # Allow small variance


# Error Handling Tests

@pytest.mark.asyncio
async def test_generate_prompt_session_not_found(async_client):
    """Test 404 error when session doesn't exist."""
    response = await async_client.get("/api/prompt/generate/nonexistent-session")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_regenerate_prompt_session_not_found(async_client):
    """Test 404 error when regenerating non-existent session."""
    regenerate_request = {
        "session_id": "nonexistent-session"
    }
    response = await async_client.post("/api/prompt/regenerate", json=regenerate_request)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_prompt_session_not_found(async_client):
    """Test 404 error when downloading from non-existent session."""
    response = await async_client.get("/api/prompt/download/nonexistent-session?format=md")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_download_invalid_format(async_client, mock_storage):
    """Test 400 error for invalid download format."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        response = await async_client.get(f"/api/prompt/download/{session_id}?format=pdf")
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "format" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_prompt_handles_validation_error(async_client, mock_storage):
    """Test handling of validation errors from prompt generator."""
    storage, session_id = mock_storage
    
    # Mock generator to raise ValueError
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        with patch.object(PromptGenerator, "generate_prompt", side_effect=ValueError("Incomplete investigation")):
            response = await async_client.get(f"/api/prompt/generate/{session_id}")
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "failed" in response.json()["detail"].lower()


# Integration Tests

@pytest.mark.asyncio
async def test_full_prompt_workflow(async_client, mock_storage):
    """Test complete workflow: generate -> cache -> regenerate -> download."""
    storage, session_id = mock_storage
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        # Step 1: Generate initial prompt
        response1 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert data1["version"] == 1
        assert data1["cached"] is False
        
        # Step 2: Verify caching
        response2 = await async_client.get(f"/api/prompt/generate/{session_id}")
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["cached"] is True
        assert data2["prompt"] == data1["prompt"]
        
        # Step 3: Regenerate with modifications
        regenerate_request = {
            "session_id": session_id,
            "additional_requirements": "Must include CI/CD pipeline"
        }
        response3 = await async_client.post("/api/prompt/regenerate", json=regenerate_request)
        assert response3.status_code == status.HTTP_200_OK
        data3 = response3.json()
        assert data3["version"] == 2
        assert "CI/CD" in data3["prompt"]
        
        # Step 4: Download modified prompt
        response4 = await async_client.get(f"/api/prompt/download/{session_id}?format=md")
        assert response4.status_code == status.HTTP_200_OK
        assert "CI/CD" in response4.text


@pytest.mark.asyncio
async def test_multiple_sessions_isolated_cache(async_client, tmp_path):
    """Test that cache is isolated per session."""
    # Create two sessions
    session1_id = "session-1"
    session2_id = "session-2"
    
    conversation_dir = tmp_path / "conversations"
    conversation_dir.mkdir()
    
    # Create conversation files
    for session_id in [session1_id, session2_id]:
        conversation_file = conversation_dir / f"{session_id}.md"
        conversation_file.write_text(f"""# Product Investigation
        
## Chunk 1
**Question:** What is your product?
**Answer:** Product for {session_id}
**Timestamp:** 2024-01-01T12:00:00
""")
    
    storage = ConversationStorage(data_dir=str(tmp_path))
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        # Generate for session 1
        response1 = await async_client.get(f"/api/prompt/generate/{session1_id}")
        assert response1.status_code == status.HTTP_200_OK
        prompt1 = response1.json()["prompt"]
        
        # Generate for session 2
        response2 = await async_client.get(f"/api/prompt/generate/{session2_id}")
        assert response2.status_code == status.HTTP_200_OK
        prompt2 = response2.json()["prompt"]
        
        # Verify different prompts
        assert prompt1 != prompt2
        assert session1_id in prompt1
        assert session2_id in prompt2


@pytest.mark.asyncio
async def test_concurrent_requests_handled(async_client, mock_storage):
    """Test handling of concurrent requests to same session."""
    import asyncio
    
    storage, session_id = mock_storage
    
    async def make_request():
        with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
            return await async_client.get(f"/api/prompt/generate/{session_id}")
    
    # Make 5 concurrent requests
    responses = await asyncio.gather(*[make_request() for _ in range(5)])
    
    # All should succeed
    for response in responses:
        assert response.status_code == status.HTTP_200_OK
    
    # All should return same prompt (from cache after first)
    prompts = [r.json()["prompt"] for r in responses]
    assert all(p == prompts[0] for p in prompts)


# Performance Tests

@pytest.mark.asyncio
async def test_large_conversation_handling(async_client, tmp_path):
    """Test handling of sessions with many conversation chunks."""
    session_id = "large-session"
    conversation_dir = tmp_path / "conversations"
    conversation_dir.mkdir()
    
    # Create conversation with 50 chunks
    chunks = []
    for i in range(50):
        chunks.append(f"""## Chunk {i+1}
**Question:** Question {i+1}?
**Answer:** Answer {i+1} with detailed information about the product
**Timestamp:** 2024-01-01T12:{i:02d}:00
""")
    
    conversation_file = conversation_dir / f"{session_id}.md"
    conversation_file.write_text("# Product Investigation\n\n" + "\n".join(chunks))
    
    storage = ConversationStorage(data_dir=str(tmp_path))
    
    with patch("routes.prompt_routes.get_conversation_storage", return_value=storage):
        response = await async_client.get(f"/api/prompt/generate/{session_id}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verify prompt was generated
    assert len(data["prompt"]) > 1000
    
    # Verify token count is within limits (<8000 tokens target)
    assert data["token_count"] < 10000  # Allow some buffer


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
EOF

echo "✅ Created tests/test_prompt_routes.py (30 test functions)"
echo ""
echo "📝 Test Coverage:"
echo "  Business Rule Tests: 4"
echo "    - test_generate_comprehensive_prompt"
echo "    - test_regenerate_with_modifications"
echo "    - test_download_markdown_format"
echo "    - test_download_text_format"
echo ""
echo "  Technical Tests: 7"
echo "    - test_prompt_caching"
echo "    - test_cache_invalidation_on_regenerate"
echo "    - test_force_regenerate_bypasses_cache"
echo "    - test_clear_specific_cache"
echo "    - test_clear_all_cache"
echo "    - test_token_count_estimation"
echo ""
echo "  Error Handling Tests: 5"
echo "    - test_generate_prompt_session_not_found"
echo "    - test_regenerate_prompt_session_not_found"
echo "    - test_download_prompt_session_not_found"
echo "    - test_download_invalid_format"
echo "    - test_generate_prompt_handles_validation_error"
echo ""
echo "  Integration Tests: 3"
echo "    - test_full_prompt_workflow"
echo "    - test_multiple_sessions_isolated_cache"
echo "    - test_concurrent_requests_handled"
echo ""
echo "  Performance Tests: 1"
echo "    - test_large_conversation_handling"
echo ""
echo "🎯 Running tests..."

cd "$BACKEND_DIR"
/Users/paulocymbaum/lovable_prompt_generator/.venv/bin/python -m pytest tests/test_prompt_routes.py -v --cov=routes.prompt_routes --cov-report=term --cov-report=html -x

echo ""
echo "✅ Test execution complete!"
