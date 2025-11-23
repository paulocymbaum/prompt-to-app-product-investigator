"""
Unit tests for ConversationStorage

Tests markdown file operations, async functionality, and error handling.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from storage.conversation_storage import ConversationStorage


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for test storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def storage(temp_storage_dir):
    """Create a ConversationStorage instance with temp directory."""
    return ConversationStorage(base_dir=temp_storage_dir)


class TestConversationStorage:
    """Test suite for ConversationStorage class."""
    
    @pytest.mark.asyncio
    async def test_save_conversation_chunk(self, storage):
        """Test saving a single Q&A interaction."""
        session_id = "test-session-001"
        question = "What is your product idea?"
        answer = "A mobile app for tracking fitness goals"
        
        await storage.save_interaction(session_id, question, answer)
        
        # Verify file was created
        filepath = storage.get_filepath(session_id)
        assert filepath.exists()
        
        # Verify content
        content = await storage.load_conversation(session_id)
        assert question in content
        assert answer in content
        assert "-----" in content
    
    @pytest.mark.asyncio
    async def test_load_conversation_history(self, storage):
        """Test loading full conversation history."""
        session_id = "test-session-002"
        
        # Save multiple interactions
        interactions = [
            ("Question 1?", "Answer 1"),
            ("Question 2?", "Answer 2"),
            ("Question 3?", "Answer 3")
        ]
        
        for q, a in interactions:
            await storage.save_interaction(session_id, q, a)
        
        # Load full history
        content = await storage.load_conversation(session_id)
        
        # Verify all interactions are present
        for q, a in interactions:
            assert q in content
            assert a in content
        
        # Verify delimiter count
        assert content.count("-----") == 3
    
    @pytest.mark.asyncio
    async def test_markdown_file_creation(self, storage):
        """Test that markdown files are created with correct format."""
        session_id = "test-session-003"
        question = "Tell me about your target users"
        answer = "Software developers aged 25-40"
        metadata = {'category': 'users'}
        
        await storage.save_interaction(session_id, question, answer, metadata)
        
        content = await storage.load_conversation(session_id)
        
        # Verify markdown formatting
        assert "### Interaction (users)" in content
        assert "**Question:**" in content
        assert "**Answer:**" in content
        assert "**Timestamp:**" in content
    
    @pytest.mark.asyncio
    async def test_parse_chunks(self, storage):
        """Test parsing conversation into chunks."""
        session_id = "test-session-004"
        
        # Save 3 interactions
        for i in range(3):
            await storage.save_interaction(
                session_id,
                f"Question {i+1}?",
                f"Answer {i+1}"
            )
        
        content = await storage.load_conversation(session_id)
        chunks = storage.parse_chunks(content)
        
        assert len(chunks) == 3
        assert "Question 1" in chunks[0]
        assert "Answer 2" in chunks[1]
        assert "Question 3" in chunks[2]
    
    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, storage):
        """Test thread-safe concurrent writes."""
        session_id = "test-session-005"
        
        # Simulate concurrent writes
        async def write_interaction(i):
            await storage.save_interaction(
                session_id,
                f"Concurrent question {i}?",
                f"Concurrent answer {i}"
            )
        
        # Execute 10 concurrent writes
        await asyncio.gather(*[write_interaction(i) for i in range(10)])
        
        # Verify all writes succeeded
        content = await storage.load_conversation(session_id)
        chunks = storage.parse_chunks(content)
        
        assert len(chunks) == 10
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_conversation(self, storage):
        """Test loading a conversation that doesn't exist."""
        session_id = "nonexistent-session"
        
        content = await storage.load_conversation(session_id)
        
        assert content == ""
    
    @pytest.mark.asyncio
    async def test_get_interaction_count(self, storage):
        """Test counting interactions in a session."""
        session_id = "test-session-006"
        
        # Save 5 interactions
        for i in range(5):
            await storage.save_interaction(
                session_id,
                f"Question {i+1}?",
                f"Answer {i+1}"
            )
        
        count = await storage.get_interaction_count(session_id)
        assert count == 5
    
    @pytest.mark.asyncio
    async def test_delete_conversation(self, storage):
        """Test deleting a conversation file."""
        session_id = "test-session-007"
        
        # Create a conversation
        await storage.save_interaction(session_id, "Q?", "A")
        
        # Verify it exists
        filepath = storage.get_filepath(session_id)
        assert filepath.exists()
        
        # Delete it
        result = await storage.delete_conversation(session_id)
        assert result is True
        assert not filepath.exists()
        
        # Try deleting again (should return False)
        result = await storage.delete_conversation(session_id)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_conversations(self, storage):
        """Test listing all conversation files."""
        # Create multiple conversations
        session_ids = ["session-1", "session-2", "session-3"]
        
        for sid in session_ids:
            await storage.save_interaction(sid, "Question?", "Answer")
        
        # List conversations
        conversations = await storage.list_conversations()
        
        assert len(conversations) == 3
        
        # Verify structure
        for conv in conversations:
            assert 'session_id' in conv
            assert 'created_at' in conv
            assert 'modified_at' in conv
            assert 'size_bytes' in conv
            assert conv['session_id'] in session_ids
    
    @pytest.mark.asyncio
    async def test_metadata_preservation(self, storage):
        """Test that metadata is preserved in markdown."""
        session_id = "test-session-008"
        question = "What's your design preference?"
        answer = "Modern and minimalist"
        metadata = {
            'category': 'design',
            'user_id': '12345',
            'session_type': 'full'
        }
        
        await storage.save_interaction(session_id, question, answer, metadata)
        
        content = await storage.load_conversation(session_id)
        
        # Verify metadata category is in content
        assert "Interaction (design)" in content
    
    @pytest.mark.asyncio
    async def test_empty_chunks_handling(self, storage):
        """Test handling of empty or whitespace-only chunks."""
        session_id = "test-session-009"
        
        # Create content with empty chunks
        await storage.save_interaction(session_id, "Q1?", "A1")
        await storage.save_interaction(session_id, "Q2?", "A2")
        
        content = await storage.load_conversation(session_id)
        chunks = storage.parse_chunks(content)
        
        # Should only return non-empty chunks
        assert len(chunks) == 2
        for chunk in chunks:
            assert chunk.strip() != ""
    
    @pytest.mark.asyncio
    async def test_large_conversation_handling(self, storage):
        """Test handling of large conversations."""
        session_id = "test-session-010"
        
        # Create a large conversation (100 interactions)
        for i in range(100):
            question = f"Question {i+1}: " + "x" * 100  # 100 chars
            answer = f"Answer {i+1}: " + "y" * 200  # 200 chars
            await storage.save_interaction(session_id, question, answer)
        
        # Load and verify
        content = await storage.load_conversation(session_id)
        chunks = storage.parse_chunks(content)
        
        assert len(chunks) == 100
        assert len(content) > 30000  # Should be quite large
    
    @pytest.mark.asyncio
    async def test_special_characters_in_content(self, storage):
        """Test handling of special characters in questions/answers."""
        session_id = "test-session-011"
        
        question = "What about special chars: <>&\"'`?"
        answer = "Answer with markdown: **bold** _italic_ [link](url)"
        
        await storage.save_interaction(session_id, question, answer)
        
        content = await storage.load_conversation(session_id)
        
        # Verify special characters are preserved
        assert question in content
        assert answer in content
    
    @pytest.mark.asyncio
    async def test_multiline_content(self, storage):
        """Test handling of multiline questions and answers."""
        session_id = "test-session-012"
        
        question = "Multi-line question:\nLine 1\nLine 2\nLine 3"
        answer = """Multi-line answer:
        - Point 1
        - Point 2
        - Point 3"""
        
        await storage.save_interaction(session_id, question, answer)
        
        content = await storage.load_conversation(session_id)
        chunks = storage.parse_chunks(content)
        
        assert len(chunks) == 1
        assert "Line 1" in chunks[0]
        assert "Point 2" in chunks[0]


class TestConversationStorageEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_session_id_characters(self, storage):
        """Test handling of session IDs with special characters."""
        # Valid session IDs should work
        session_id = "session-with-dashes-123"
        await storage.save_interaction(session_id, "Q?", "A")
        
        filepath = storage.get_filepath(session_id)
        assert filepath.exists()
    
    @pytest.mark.asyncio
    async def test_directory_creation(self, temp_storage_dir):
        """Test that storage creates directory if it doesn't exist."""
        nested_dir = f"{temp_storage_dir}/nested/path"
        storage = ConversationStorage(base_dir=nested_dir)
        
        assert Path(nested_dir).exists()
    
    def test_get_filepath(self, storage):
        """Test filepath generation."""
        session_id = "test-session"
        filepath = storage.get_filepath(session_id)
        
        assert filepath.name == "test-session.md"
        assert filepath.parent == storage.base_dir
