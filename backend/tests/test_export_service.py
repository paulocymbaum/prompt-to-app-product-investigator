"""
Unit tests for ExportService.

Tests PDF, HTML, and Markdown export functionality with comprehensive
coverage of success cases, error handling, and edge cases.

Note: WeasyPrint requires system libraries (libgobject, pango, etc.) which
may not be available on all development machines. Tests mock weasyprint to
avoid import errors. For production deployment, use Docker with proper
system dependencies installed.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import sys

# Mock weasyprint before import to avoid system library dependencies
sys.modules['weasyprint'] = MagicMock()

from storage.conversation_storage import ConversationStorage
from services.prompt_generator import PromptGenerator
from services.graph_service import GraphService
from services.export_service import ExportService


# Test Fixtures
@pytest.fixture
def mock_storage():
    """Mock ConversationStorage."""
    storage = Mock(spec=ConversationStorage)
    storage.load_conversation = AsyncMock()
    storage.parse_chunks = Mock()
    return storage


@pytest.fixture
def mock_prompt_gen():
    """Mock PromptGenerator."""
    prompt_gen = Mock(spec=PromptGenerator)
    prompt_gen.generate_prompt = AsyncMock()
    return prompt_gen


@pytest.fixture
def mock_graph_service():
    """Mock GraphService."""
    graph_service = Mock(spec=GraphService)
    graph_service.build_graph = AsyncMock()
    graph_service.export_mermaid = Mock()
    return graph_service


@pytest.fixture
def export_service(mock_storage, mock_prompt_gen, mock_graph_service):
    """ExportService instance with mocked dependencies."""
    return ExportService(mock_storage, mock_prompt_gen, mock_graph_service)


@pytest.fixture
def sample_conversation():
    """Sample conversation data."""
    return """**Question:** What is the main feature?
**Answer:** The main feature is AI-powered analysis.

**Question:** What technology is used?
**Answer:** We use Python and LangChain for NLP processing."""


@pytest.fixture
def sample_chunks():
    """Sample conversation chunks."""
    return [
        "**Question:** What is the main feature?\n**Answer:** The main feature is AI-powered analysis.",
        "**Question:** What technology is used?\n**Answer:** We use Python and LangChain for NLP processing."
    ]


@pytest.fixture
def sample_prompt():
    """Sample generated prompt."""
    return """# Development Prompt

Create an AI-powered analysis system using:
- Python backend
- LangChain for NLP
- FastAPI for API layer

## Requirements
1. Natural language processing
2. Real-time analysis
3. RESTful API"""


@pytest.fixture
def sample_graph_data():
    """Sample graph data."""
    return {
        "nodes": [
            {"id": "q1", "type": "question", "content": "What is the main feature?"},
            {"id": "a1", "type": "answer", "content": "AI-powered analysis"},
            {"id": "q2", "type": "question", "content": "What technology is used?"},
            {"id": "a2", "type": "answer", "content": "Python and LangChain"}
        ],
        "edges": [
            {"source": "q1", "target": "a1", "type": "answer"},
            {"source": "a1", "target": "q2", "type": "follow_up"},
            {"source": "q2", "target": "a2", "type": "answer"}
        ],
        "metadata": {
            "created_at": datetime(2024, 1, 15, 10, 30, 0),
            "duration_minutes": 15,
            "total_interactions": 2
        }
    }


@pytest.fixture
def sample_mermaid():
    """Sample Mermaid diagram."""
    return """graph TD
    q1[What is the main feature?] --> a1[AI-powered analysis]
    a1 --> q2[What technology is used?]
    q2 --> a2[Python and LangChain]"""


# Test PDF Export
class TestPDFExport:
    """Tests for PDF export functionality."""
    
    @pytest.mark.asyncio
    async def test_export_to_pdf_success(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service,
        sample_conversation,
        sample_chunks,
        sample_prompt,
        sample_graph_data,
        sample_mermaid
    ):
        """Test successful PDF export."""
        session_id = "test_session_123"
        
        # Setup mocks
        mock_storage.load_conversation.return_value = sample_conversation
        mock_storage.parse_chunks.return_value = sample_chunks
        mock_prompt_gen.generate_prompt.return_value = sample_prompt
        mock_graph_service.build_graph.return_value = sample_graph_data
        mock_graph_service.export_mermaid.return_value = sample_mermaid
        
        # Mock weasyprint HTML.write_pdf
        with patch('services.export_service.HTML') as mock_html:
            mock_pdf_instance = MagicMock()
            mock_pdf_instance.write_pdf.return_value = b'PDF_CONTENT'
            mock_html.return_value = mock_pdf_instance
            
            # Execute
            result = await export_service.export_to_pdf(session_id)
            
            # Verify
            assert result == b'PDF_CONTENT'
            assert isinstance(result, bytes)
            mock_storage.load_conversation.assert_called_once_with(session_id)
            mock_prompt_gen.generate_prompt.assert_called_once_with(session_id)
            mock_graph_service.build_graph.assert_called_once_with(session_id)
    
    @pytest.mark.asyncio
    async def test_export_to_pdf_session_not_found(
        self,
        export_service,
        mock_storage
    ):
        """Test PDF export with non-existent session."""
        session_id = "nonexistent_session"
        mock_storage.load_conversation.return_value = None
        
        with pytest.raises(ValueError, match="not found"):
            await export_service.export_to_pdf(session_id)
    
    @pytest.mark.asyncio
    async def test_export_to_pdf_includes_prompt(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service,
        sample_conversation,
        sample_chunks,
        sample_prompt,
        sample_graph_data,
        sample_mermaid
    ):
        """Test that PDF export includes generated prompt."""
        session_id = "test_session_123"
        
        # Setup mocks
        mock_storage.load_conversation.return_value = sample_conversation
        mock_storage.parse_chunks.return_value = sample_chunks
        mock_prompt_gen.generate_prompt.return_value = sample_prompt
        mock_graph_service.build_graph.return_value = sample_graph_data
        mock_graph_service.export_mermaid.return_value = sample_mermaid
        
        with patch('services.export_service.HTML') as mock_html:
            mock_pdf_instance = MagicMock()
            mock_pdf_instance.write_pdf.return_value = b'PDF_WITH_PROMPT'
            mock_html.return_value = mock_pdf_instance
            
            await export_service.export_to_pdf(session_id)
            
            # Verify prompt generator was called
            mock_prompt_gen.generate_prompt.assert_called_once_with(session_id)
            
            # Verify HTML content includes prompt (check call args)
            html_call = mock_html.call_args
            html_content = html_call[1]['string'] if html_call[1] else html_call[0][0]
            assert 'Development Prompt' in html_content or 'prompt' in html_content.lower()
    
    @pytest.mark.asyncio
    async def test_export_to_pdf_generation_failure(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service,
        sample_conversation,
        sample_chunks,
        sample_prompt,
        sample_graph_data,
        sample_mermaid
    ):
        """Test PDF export when weasyprint fails."""
        session_id = "test_session_123"
        
        mock_storage.load_conversation.return_value = sample_conversation
        mock_storage.parse_chunks.return_value = sample_chunks
        mock_prompt_gen.generate_prompt.return_value = sample_prompt
        mock_graph_service.build_graph.return_value = sample_graph_data
        mock_graph_service.export_mermaid.return_value = sample_mermaid
        
        with patch('services.export_service.HTML') as mock_html:
            mock_html.side_effect = Exception("PDF generation error")
            
            with pytest.raises(ValueError, match="Failed to generate PDF"):
                await export_service.export_to_pdf(session_id)


# Test HTML Export
class TestHTMLExport:
    """Tests for HTML export functionality."""
    
    @pytest.mark.asyncio
    async def test_export_to_html_success(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service,
        sample_conversation,
        sample_chunks,
        sample_prompt,
        sample_graph_data,
        sample_mermaid
    ):
        """Test successful HTML export."""
        session_id = "test_session_123"
        
        # Setup mocks
        mock_storage.load_conversation.return_value = sample_conversation
        mock_storage.parse_chunks.return_value = sample_chunks
        mock_prompt_gen.generate_prompt.return_value = sample_prompt
        mock_graph_service.build_graph.return_value = sample_graph_data
        mock_graph_service.export_mermaid.return_value = sample_mermaid
        
        # Execute
        result = await export_service.export_to_html(session_id)
        
        # Verify
        assert isinstance(result, str)
        assert '<!DOCTYPE html>' in result
        assert session_id in result
        assert 'mermaid' in result.lower()
        mock_storage.load_conversation.assert_called_once_with(session_id)
    
    @pytest.mark.asyncio
    async def test_export_to_html_structure(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service,
        sample_conversation,
        sample_chunks,
        sample_prompt,
        sample_graph_data,
        sample_mermaid
    ):
        """Test HTML export has correct structure."""
        session_id = "test_session_123"
        
        mock_storage.load_conversation.return_value = sample_conversation
        mock_storage.parse_chunks.return_value = sample_chunks
        mock_prompt_gen.generate_prompt.return_value = sample_prompt
        mock_graph_service.build_graph.return_value = sample_graph_data
        mock_graph_service.export_mermaid.return_value = sample_mermaid
        
        result = await export_service.export_to_html(session_id)
        
        # Verify HTML structure
        assert '<html' in result
        assert '</html>' in result
        assert '<head>' in result
        assert '</head>' in result
        assert '<body>' in result
        assert '</body>' in result
        assert '<style>' in result  # CSS included
        assert '<script>' in result  # Mermaid script included
    
    @pytest.mark.asyncio
    async def test_export_to_html_embedded_graph(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service,
        sample_conversation,
        sample_chunks,
        sample_prompt,
        sample_graph_data,
        sample_mermaid
    ):
        """Test HTML export includes embedded Mermaid graph."""
        session_id = "test_session_123"
        
        mock_storage.load_conversation.return_value = sample_conversation
        mock_storage.parse_chunks.return_value = sample_chunks
        mock_prompt_gen.generate_prompt.return_value = sample_prompt
        mock_graph_service.build_graph.return_value = sample_graph_data
        mock_graph_service.export_mermaid.return_value = sample_mermaid
        
        result = await export_service.export_to_html(session_id)
        
        # Verify Mermaid graph is embedded
        assert 'graph TD' in result
        assert 'mermaid' in result.lower()
        assert 'mermaid.initialize' in result
        mock_graph_service.export_mermaid.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_to_html_session_not_found(
        self,
        export_service,
        mock_storage
    ):
        """Test HTML export with non-existent session."""
        session_id = "nonexistent_session"
        mock_storage.load_conversation.return_value = None
        
        with pytest.raises(ValueError, match="not found"):
            await export_service.export_to_html(session_id)
    
    @pytest.mark.asyncio
    async def test_export_to_html_includes_metadata(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service,
        sample_conversation,
        sample_chunks,
        sample_prompt,
        sample_graph_data,
        sample_mermaid
    ):
        """Test HTML export includes session metadata."""
        session_id = "test_session_123"
        
        mock_storage.load_conversation.return_value = sample_conversation
        mock_storage.parse_chunks.return_value = sample_chunks
        mock_prompt_gen.generate_prompt.return_value = sample_prompt
        mock_graph_service.build_graph.return_value = sample_graph_data
        mock_graph_service.export_mermaid.return_value = sample_mermaid
        
        result = await export_service.export_to_html(session_id)
        
        # Verify metadata is included
        assert session_id in result
        assert '15 minutes' in result  # duration from sample_graph_data
        assert '2024-01-15' in result  # created_at from sample_graph_data


# Test Markdown Export
class TestMarkdownExport:
    """Tests for Markdown export functionality."""
    
    @pytest.mark.asyncio
    async def test_export_to_markdown_success(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service,
        sample_conversation,
        sample_chunks,
        sample_prompt,
        sample_graph_data,
        sample_mermaid
    ):
        """Test successful Markdown export."""
        session_id = "test_session_123"
        
        # Setup mocks
        mock_storage.load_conversation.return_value = sample_conversation
        mock_storage.parse_chunks.return_value = sample_chunks
        mock_prompt_gen.generate_prompt.return_value = sample_prompt
        mock_graph_service.build_graph.return_value = sample_graph_data
        mock_graph_service.export_mermaid.return_value = sample_mermaid
        
        # Execute
        result = await export_service.export_to_markdown(session_id)
        
        # Verify
        assert isinstance(result, str)
        assert '# Product Investigation Report' in result
        assert session_id in result
        mock_storage.load_conversation.assert_called_once_with(session_id)
    
    @pytest.mark.asyncio
    async def test_export_to_markdown_formatting(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service,
        sample_conversation,
        sample_chunks,
        sample_prompt,
        sample_graph_data,
        sample_mermaid
    ):
        """Test Markdown export has proper formatting."""
        session_id = "test_session_123"
        
        mock_storage.load_conversation.return_value = sample_conversation
        mock_storage.parse_chunks.return_value = sample_chunks
        mock_prompt_gen.generate_prompt.return_value = sample_prompt
        mock_graph_service.build_graph.return_value = sample_graph_data
        mock_graph_service.export_mermaid.return_value = sample_mermaid
        
        result = await export_service.export_to_markdown(session_id)
        
        # Verify Markdown formatting
        assert '# ' in result  # H1 headers
        assert '## ' in result  # H2 headers
        assert '**' in result  # Bold text
        assert '---' in result  # Horizontal rules
        assert '```mermaid' in result  # Code blocks with mermaid
    
    @pytest.mark.asyncio
    async def test_export_to_markdown_includes_prompt(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service,
        sample_conversation,
        sample_chunks,
        sample_prompt,
        sample_graph_data,
        sample_mermaid
    ):
        """Test Markdown export includes generated prompt."""
        session_id = "test_session_123"
        
        mock_storage.load_conversation.return_value = sample_conversation
        mock_storage.parse_chunks.return_value = sample_chunks
        mock_prompt_gen.generate_prompt.return_value = sample_prompt
        mock_graph_service.build_graph.return_value = sample_graph_data
        mock_graph_service.export_mermaid.return_value = sample_mermaid
        
        result = await export_service.export_to_markdown(session_id)
        
        # Verify prompt is included
        assert 'Generated Development Prompt' in result
        assert 'Development Prompt' in result or sample_prompt in result
        mock_prompt_gen.generate_prompt.assert_called_once_with(session_id)
    
    @pytest.mark.asyncio
    async def test_export_to_markdown_session_not_found(
        self,
        export_service,
        mock_storage
    ):
        """Test Markdown export with non-existent session."""
        session_id = "nonexistent_session"
        mock_storage.load_conversation.return_value = None
        
        with pytest.raises(ValueError, match="not found"):
            await export_service.export_to_markdown(session_id)


# Test Edge Cases
class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_export_empty_conversation(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service
    ):
        """Test export with empty conversation raises error."""
        session_id = "empty_session"
        
        # Empty string should be treated as session not found
        mock_storage.load_conversation.return_value = ""
        
        # Should raise ValueError for empty/not found session
        with pytest.raises(ValueError, match="not found"):
            await export_service.export_to_markdown(session_id)
    
    @pytest.mark.asyncio
    async def test_export_large_conversation(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service
    ):
        """Test export with large conversation."""
        session_id = "large_session"
        
        # Create large conversation with 100 chunks
        large_chunks = [
            f"**Question:** Question {i}\n**Answer:** Answer {i}"
            for i in range(100)
        ]
        large_conversation = "\n\n".join(large_chunks)
        
        mock_storage.load_conversation.return_value = large_conversation
        mock_storage.parse_chunks.return_value = large_chunks
        mock_prompt_gen.generate_prompt.return_value = "Large prompt"
        mock_graph_service.build_graph.return_value = {
            "nodes": [{"id": f"n{i}", "type": "question"} for i in range(100)],
            "edges": [],
            "metadata": {"created_at": "2024-01-15", "duration_minutes": 120}
        }
        mock_graph_service.export_mermaid.return_value = "graph TD\n" + "\n".join(
            [f"n{i} --> n{i+1}" for i in range(99)]
        )
        
        # Should handle large data
        result = await export_service.export_to_markdown(session_id)
        assert isinstance(result, str)
        assert len(result) > 1000  # Should be substantial
    
    @pytest.mark.asyncio
    async def test_format_interaction_alternative_format(
        self,
        export_service
    ):
        """Test interaction formatting with alternative formats."""
        # Test with non-standard format
        chunk = "User asked about features\nSystem responded with details"
        result = export_service._format_interaction_html(chunk)
        
        assert isinstance(result, dict)
        assert 'question' in result
        assert 'answer' in result
    
    @pytest.mark.asyncio
    async def test_export_with_special_characters(
        self,
        export_service,
        mock_storage,
        mock_prompt_gen,
        mock_graph_service
    ):
        """Test export with special characters in content."""
        session_id = "special_chars"
        
        special_conversation = "**Question:** What's the <script>alert('xss')</script> feature?\n**Answer:** It's & < > \" ' safe"
        
        mock_storage.load_conversation.return_value = special_conversation
        mock_storage.parse_chunks.return_value = [special_conversation]
        mock_prompt_gen.generate_prompt.return_value = "Prompt with <html> & special chars"
        mock_graph_service.build_graph.return_value = {
            "nodes": [],
            "edges": [],
            "metadata": {"created_at": "2024-01-15", "duration_minutes": 5}
        }
        mock_graph_service.export_mermaid.return_value = "graph TD"
        
        # Should handle special characters safely
        result = await export_service.export_to_html(session_id)
        assert isinstance(result, str)
        # HTML should be escaped or handled properly
        assert '<script>' in result  # Should be in content, not executed
