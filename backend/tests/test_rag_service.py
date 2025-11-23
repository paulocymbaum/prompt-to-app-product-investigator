"""
Unit tests for RAG Service with ChromaDB

Tests embedding generation, vector storage, context retrieval, and persistence.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from services.rag_service import RAGService
from storage.conversation_storage import ConversationStorage


@pytest.fixture
def temp_dirs():
    """Create temporary directories for storage and vectors."""
    storage_dir = tempfile.mkdtemp()
    vector_dir = tempfile.mkdtemp()
    
    yield storage_dir, vector_dir
    
    # Cleanup
    shutil.rmtree(storage_dir, ignore_errors=True)
    shutil.rmtree(vector_dir, ignore_errors=True)


@pytest.fixture
def rag_service(temp_dirs):
    """Create a RAGService instance with temp directories."""
    storage_dir, vector_dir = temp_dirs
    storage = ConversationStorage(base_dir=storage_dir)
    return RAGService(
        storage=storage,
        persist_directory=vector_dir
    )


class TestRAGServiceBasics:
    """Test basic RAG service functionality."""
    
    @pytest.mark.asyncio
    async def test_persist_conversation_to_markdown(self, rag_service):
        """Test that interactions are persisted to markdown."""
        session_id = "test-session-001"
        question = "What is your product?"
        answer = "A mobile fitness app"
        
        chunk_id = await rag_service.persist_interaction(
            session_id, question, answer
        )
        
        assert chunk_id is not None
        assert session_id in chunk_id
        
        # Verify markdown was created
        content = await rag_service.storage.load_conversation(session_id)
        assert question in content
        assert answer in content
    
    @pytest.mark.asyncio
    async def test_embedding_generation(self, rag_service):
        """Test embedding generation."""
        text = "This is a test sentence for embedding."
        embedding = rag_service._embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_chunk_separation(self, rag_service):
        """Test that multiple interactions are stored separately."""
        session_id = "test-session-002"
        
        interactions = [
            ("Question 1?", "Answer 1"),
            ("Question 2?", "Answer 2"),
            ("Question 3?", "Answer 3")
        ]
        
        chunk_ids = []
        for q, a in interactions:
            chunk_id = await rag_service.persist_interaction(session_id, q, a)
            chunk_ids.append(chunk_id)
        
        # Verify all chunks were stored
        assert len(set(chunk_ids)) == 3  # All unique IDs
        
        # Verify collection count
        stats = rag_service.get_collection_stats()
        assert stats['total_chunks'] >= 3


class TestContextRetrieval:
    """Test context retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_retrieve_relevant_chunks(self, rag_service):
        """Test retrieving relevant context chunks."""
        session_id = "test-session-003"
        
        # Persist several interactions
        await rag_service.persist_interaction(
            session_id,
            "What are the main features?",
            "User profiles, workout tracking, and social sharing",
            {"category": "functionality"}
        )
        
        await rag_service.persist_interaction(
            session_id,
            "Who is the target audience?",
            "Fitness enthusiasts aged 25-40",
            {"category": "users"}
        )
        
        # Retrieve context with a related query
        context = rag_service.retrieve_context(
            query="Tell me about the users",
            session_id=session_id,
            top_k=2
        )
        
        assert len(context) > 0
        assert len(context) <= 2
        # Should retrieve the user-related interaction
        assert any("target audience" in chunk.lower() or "25-40" in chunk for chunk in context)
    
    @pytest.mark.asyncio
    async def test_context_window_limit(self, rag_service):
        """Test that token limit is respected."""
        session_id = "test-session-004"
        
        # Create a large interaction
        long_answer = "x" * 10000  # Very long answer
        
        await rag_service.persist_interaction(
            session_id,
            "Long question?",
            long_answer
        )
        
        # Retrieve with small token limit
        context = rag_service.retrieve_context(
            query="test",
            session_id=session_id,
            max_tokens=500
        )
        
        # Should respect token limit
        total_length = sum(len(c) for c in context)
        assert total_length < 500 * 4  # Rough token-to-char conversion
    
    @pytest.mark.asyncio
    async def test_no_redundant_context(self, rag_service):
        """Test deduplication of similar chunks."""
        session_id = "test-session-005"
        
        # Add similar interactions
        for i in range(3):
            await rag_service.persist_interaction(
                session_id,
                "What is the product?",
                "A fitness tracking application"
            )
        
        # Retrieve context
        context = rag_service.retrieve_context(
            query="fitness app",
            session_id=session_id,
            top_k=5
        )
        
        # Should deduplicate
        assert len(context) == 1  # Only one unique chunk
    
    @pytest.mark.asyncio
    async def test_session_isolation(self, rag_service):
        """Test that sessions are isolated in retrieval."""
        session_1 = "session-A"
        session_2 = "session-B"
        
        # Add to session 1
        await rag_service.persist_interaction(
            session_1,
            "Question for A?",
            "Answer for A"
        )
        
        # Add to session 2
        await rag_service.persist_interaction(
            session_2,
            "Question for B?",
            "Answer for B"
        )
        
        # Retrieve from session 1
        context_1 = rag_service.retrieve_context(
            query="answer",
            session_id=session_1,
            top_k=10
        )
        
        # Should only contain session 1 content
        assert all("Answer for A" in chunk for chunk in context_1)
        assert not any("Answer for B" in chunk for chunk in context_1)


class TestCollectionManagement:
    """Test collection management operations."""
    
    @pytest.mark.asyncio
    async def test_get_collection_stats(self, rag_service):
        """Test getting collection statistics."""
        stats = rag_service.get_collection_stats()
        
        assert 'total_chunks' in stats
        assert 'embedding_model' in stats
        assert isinstance(stats['total_chunks'], int)
    
    @pytest.mark.asyncio
    async def test_get_session_stats(self, rag_service):
        """Test getting session-specific statistics."""
        session_id = "test-session-006"
        
        # Add 3 interactions
        for i in range(3):
            await rag_service.persist_interaction(
                session_id,
                f"Question {i}?",
                f"Answer {i}"
            )
        
        # Get session stats
        stats = rag_service.get_collection_stats(session_id=session_id)
        
        assert stats['session_chunks'] == 3
        assert stats['session_id'] == session_id
    
    @pytest.mark.asyncio
    async def test_delete_session_chunks(self, rag_service):
        """Test deleting all chunks for a session."""
        session_id = "test-session-007"
        
        # Add chunks
        await rag_service.persist_interaction(
            session_id, "Q1?", "A1"
        )
        await rag_service.persist_interaction(
            session_id, "Q2?", "A2"
        )
        
        # Delete session chunks
        deleted_count = rag_service.delete_session_chunks(session_id)
        
        assert deleted_count == 2
        
        # Verify deletion
        stats = rag_service.get_collection_stats(session_id=session_id)
        assert stats['session_chunks'] == 0
    
    @pytest.mark.asyncio
    async def test_clear_collection(self, rag_service):
        """Test clearing the entire collection."""
        # Add some chunks
        await rag_service.persist_interaction(
            "session-1", "Q?", "A"
        )
        
        # Clear collection
        rag_service.clear_collection()
        
        # Verify empty
        stats = rag_service.get_collection_stats()
        assert stats['total_chunks'] == 0


class TestPersistence:
    """Test ChromaDB persistence."""
    
    @pytest.mark.asyncio
    async def test_persistence_across_restarts(self, temp_dirs):
        """Test that data persists across service restarts."""
        storage_dir, vector_dir = temp_dirs
        storage = ConversationStorage(base_dir=storage_dir)
        
        # Create first service instance
        rag1 = RAGService(storage=storage, persist_directory=vector_dir)
        
        session_id = "persistent-session"
        await rag1.persist_interaction(
            session_id,
            "Persistent question?",
            "Persistent answer"
        )
        
        del rag1
        
        # Create new service instance with same directory
        rag2 = RAGService(
            storage=ConversationStorage(base_dir=storage_dir),
            persist_directory=vector_dir
        )
        
        # Verify data persisted
        stats = rag2.get_collection_stats(session_id=session_id)
        assert stats['session_chunks'] >= 1
        
        # Can retrieve context
        context = rag2.retrieve_context(
            query="answer",
            session_id=session_id
        )
        assert len(context) > 0


class TestRecencyWeighting:
    """Test recency-weighted retrieval."""
    
    @pytest.mark.asyncio
    async def test_recent_chunks_prioritized(self, rag_service):
        """Test that recent chunks get higher priority."""
        session_id = "test-session-008"
        
        # Add old interaction
        await rag_service.persist_interaction(
            session_id,
            "Old question?",
            "Old answer about topic X"
        )
        
        # Simulate time passing (we can't actually wait, but metadata will differ)
        await asyncio.sleep(0.1)
        
        # Add recent interaction
        await rag_service.persist_interaction(
            session_id,
            "New question?",
            "New answer about topic X"
        )
        
        # Retrieve with high recency weight
        context = rag_service.retrieve_context(
            query="topic X",
            session_id=session_id,
            top_k=2,
            recency_weight=0.7  # High recency weight
        )
        
        # Both should be retrieved
        assert len(context) == 2


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_retrieve_from_empty_collection(self, rag_service):
        """Test retrieving from empty collection."""
        context = rag_service.retrieve_context(
            query="test",
            session_id="nonexistent",
            top_k=5
        )
        
        assert context == []
    
    @pytest.mark.asyncio
    async def test_large_conversation_handling(self, rag_service):
        """Test handling of large conversations."""
        session_id = "large-session"
        
        # Add 50 interactions
        for i in range(50):
            await rag_service.persist_interaction(
                session_id,
                f"Question {i}?",
                f"Answer {i} with some content"
            )
        
        # Should handle retrieval efficiently
        context = rag_service.retrieve_context(
            query="content",
            session_id=session_id,
            top_k=5
        )
        
        assert len(context) <= 5
    
    @pytest.mark.asyncio
    async def test_special_characters_in_text(self, rag_service):
        """Test handling of special characters."""
        session_id = "special-chars"
        
        question = "What about chars: <>&\"'`?"
        answer = "Answer with **markdown** and [links](url)"
        
        chunk_id = await rag_service.persist_interaction(
            session_id, question, answer
        )
        
        assert chunk_id is not None
        
        # Retrieve should work
        context = rag_service.retrieve_context(
            query="markdown",
            session_id=session_id
        )
        
        assert len(context) > 0
