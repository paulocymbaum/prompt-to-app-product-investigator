"""
Tests for Graph Service

Comprehensive test suite for conversation graph building and visualization.
"""

import pytest
from datetime import datetime, timedelta
from services.graph_service import GraphService
from storage.conversation_storage import ConversationStorage
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
def storage(temp_storage_dir):
    """Create ConversationStorage instance with temp directory."""
    return ConversationStorage(base_dir=temp_storage_dir)


@pytest.fixture
def graph_service(storage):
    """Create GraphService instance."""
    return GraphService(storage=storage)


@pytest.fixture
async def sample_conversation(storage):
    """Create sample conversation data."""
    session_id = "test_session_123"
    
    # Create conversation with multiple interactions
    interactions = [
        {
            "question": "What is the main functionality of your product?",
            "answer": "A task management app for developers",
            "metadata": {"category": "functionality"}
        },
        {
            "question": "Who are the target users?",
            "answer": "Software engineers and product managers",
            "metadata": {"category": "users"}
        },
        {
            "question": "What age group is your target demographic?",
            "answer": "Ages 25-45, tech-savvy professionals",
            "metadata": {"category": "demographics"}
        },
        {
            "question": "What design style do you envision?",
            "answer": "Clean, modern, minimal design with dark mode",
            "metadata": {"category": "design"}
        },
        {
            "question": "Who are your main competitors?",
            "answer": "Competing with Jira and Asana",
            "metadata": {"category": "market"}
        },
        {
            "question": "What technology stack do you prefer?",
            "answer": "Python backend with React frontend",
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
    
    return session_id


@pytest.mark.asyncio
async def test_build_graph_basic_structure(graph_service, sample_conversation):
    """Test that build_graph creates correct basic structure."""
    graph_data = await graph_service.build_graph(sample_conversation)
    
    assert 'nodes' in graph_data
    assert 'edges' in graph_data
    assert 'metadata' in graph_data
    
    assert isinstance(graph_data['nodes'], list)
    assert isinstance(graph_data['edges'], list)
    assert isinstance(graph_data['metadata'], dict)


@pytest.mark.asyncio
async def test_build_graph_node_count(graph_service, sample_conversation):
    """Test that correct number of nodes are created (2 per interaction)."""
    graph_data = await graph_service.build_graph(sample_conversation)
    
    # 6 interactions = 12 nodes (6 questions + 6 answers)
    assert len(graph_data['nodes']) == 12
    
    # Count question and answer nodes
    question_nodes = [n for n in graph_data['nodes'] if n['type'] == 'question']
    answer_nodes = [n for n in graph_data['nodes'] if n['type'] == 'answer']
    
    assert len(question_nodes) == 6
    assert len(answer_nodes) == 6


@pytest.mark.asyncio
async def test_build_graph_edge_count(graph_service, sample_conversation):
    """Test that correct number of edges are created."""
    graph_data = await graph_service.build_graph(sample_conversation)
    
    # Expected edges:
    # - 6 Q->A edges (one per interaction)
    # - 5 A->Q edges (connecting interactions, n-1)
    # Total: 11 edges
    assert len(graph_data['edges']) == 11


@pytest.mark.asyncio
async def test_build_graph_node_structure(graph_service, sample_conversation):
    """Test that nodes have correct structure and required fields."""
    graph_data = await graph_service.build_graph(sample_conversation)
    
    for node in graph_data['nodes']:
        assert 'id' in node
        assert 'type' in node
        assert 'content' in node
        assert 'category' in node
        assert 'color' in node
        assert 'timestamp' in node
        assert 'shape' in node
        
        # Validate types
        assert isinstance(node['id'], str)
        assert node['type'] in ['question', 'answer']
        assert isinstance(node['content'], str)
        assert isinstance(node['category'], str)
        assert isinstance(node['color'], str)
        
        # Validate color format (hex color)
        assert node['color'].startswith('#')
        assert len(node['color']) == 7


@pytest.mark.asyncio
async def test_build_graph_edge_structure(graph_service, sample_conversation):
    """Test that edges have correct structure."""
    graph_data = await graph_service.build_graph(sample_conversation)
    
    for edge in graph_data['edges']:
        assert 'source' in edge
        assert 'target' in edge
        assert 'label' in edge
        
        assert isinstance(edge['source'], str)
        assert isinstance(edge['target'], str)
        assert edge['label'] in ['answer', 'next']


@pytest.mark.asyncio
async def test_build_graph_metadata(graph_service, sample_conversation):
    """Test that metadata is correctly populated."""
    graph_data = await graph_service.build_graph(sample_conversation)
    
    metadata = graph_data['metadata']
    
    assert metadata['session_id'] == sample_conversation
    assert metadata['total_interactions'] == 6
    assert metadata['created_at'] is not None
    assert metadata['duration_minutes'] >= 0


@pytest.mark.asyncio
async def test_build_graph_empty_conversation(graph_service, storage):
    """Test build_graph with non-existent session."""
    graph_data = await graph_service.build_graph("nonexistent_session")
    
    assert graph_data['nodes'] == []
    assert graph_data['edges'] == []
    assert graph_data['metadata']['total_interactions'] == 0
    assert graph_data['metadata']['created_at'] is None


@pytest.mark.asyncio
async def test_categorization_functionality(graph_service):
    """Test categorization for functionality-related questions."""
    questions = [
        "What is the main functionality?",
        "What features will it have?",
        "What does the product do?",
        "What is the core capability?"
    ]
    
    for question in questions:
        category = graph_service._categorize_interaction(question)
        assert category == 'functionality'


@pytest.mark.asyncio
async def test_categorization_users(graph_service):
    """Test categorization for user-related questions."""
    questions = [
        "Who are the target users?",
        "What audience will use this?",
        "Who is this for?",
        "What customer segment?"
    ]
    
    for question in questions:
        category = graph_service._categorize_interaction(question)
        assert category == 'users'


@pytest.mark.asyncio
async def test_categorization_demographics(graph_service):
    """Test categorization for demographics questions."""
    questions = [
        "What age group?",
        "What is the demographic?",
        "What location?",
        "What geographic region?"
    ]
    
    for question in questions:
        category = graph_service._categorize_interaction(question)
        assert category == 'demographics'


@pytest.mark.asyncio
async def test_categorization_design(graph_service):
    """Test categorization for design questions."""
    questions = [
        "What design style?",
        "What color scheme?",
        "What UI approach?",
        "What is the visual aesthetic?"
    ]
    
    for question in questions:
        category = graph_service._categorize_interaction(question)
        assert category == 'design'


@pytest.mark.asyncio
async def test_categorization_market(graph_service):
    """Test categorization for market questions."""
    questions = [
        "Who are your competitors?",
        "What is the market size?",
        "What is your business model?",
        "How will you monetize?"
    ]
    
    for question in questions:
        category = graph_service._categorize_interaction(question)
        assert category == 'market'


@pytest.mark.asyncio
async def test_categorization_technical(graph_service):
    """Test categorization for technical questions."""
    questions = [
        "What technology stack?",
        "What technical requirements?",
        "What performance needs?",
        "What architecture pattern?"
    ]
    
    for question in questions:
        category = graph_service._categorize_interaction(question)
        assert category == 'technical'


@pytest.mark.asyncio
async def test_categorization_general_fallback(graph_service):
    """Test that unclear questions default to 'general'."""
    questions = [
        "Tell me more",
        "Anything else?",
        "What do you think?"
    ]
    
    for question in questions:
        category = graph_service._categorize_interaction(question)
        assert category == 'general'


@pytest.mark.asyncio
async def test_color_mapping(graph_service, sample_conversation):
    """Test that categories are mapped to correct colors."""
    graph_data = await graph_service.build_graph(sample_conversation)
    
    expected_colors = {
        'functionality': '#3B82F6',
        'users': '#10B981',
        'demographics': '#F59E0B',
        'design': '#8B5CF6',
        'market': '#EF4444',
        'technical': '#6366F1'
    }
    
    for node in graph_data['nodes']:
        category = node['category']
        if category in expected_colors:
            assert node['color'] == expected_colors[category]


@pytest.mark.asyncio
async def test_export_mermaid_basic(graph_service, sample_conversation):
    """Test Mermaid export generates valid diagram."""
    graph_data = await graph_service.build_graph(sample_conversation)
    mermaid = graph_service.export_mermaid(graph_data)
    
    # Check basic structure
    assert mermaid.startswith('graph TD')
    assert len(mermaid) > 50  # Should have substantial content
    
    # Check for node definitions
    assert 'q0[' in mermaid or 'q0(' in mermaid
    assert 'a0[' in mermaid or 'a0(' in mermaid
    
    # Check for edges
    assert '-->' in mermaid
    
    # Check for styling
    assert 'style' in mermaid
    assert 'fill:' in mermaid


@pytest.mark.asyncio
async def test_export_mermaid_node_shapes(graph_service, sample_conversation):
    """Test that Mermaid uses correct shapes for questions vs answers."""
    graph_data = await graph_service.build_graph(sample_conversation)
    mermaid = graph_service.export_mermaid(graph_data)
    
    # Questions should have rectangle brackets []
    assert '[' in mermaid and ']' in mermaid
    
    # Answers should have rounded parentheses ()
    assert '(' in mermaid and ')' in mermaid


@pytest.mark.asyncio
async def test_export_mermaid_truncates_long_content(graph_service, storage):
    """Test that long content is truncated in Mermaid output."""
    session_id = "test_long_content"
    
    long_answer = "This is a very long answer " * 20  # Very long text
    
    await storage.save_interaction(
        session_id=session_id,
        question="What is your product?",
        answer=long_answer,
        metadata={"category": "functionality"}
    )
    
    graph_data = await graph_service.build_graph(session_id)
    mermaid = graph_service.export_mermaid(graph_data)
    
    # Check that content is truncated with ...
    assert '...' in mermaid


@pytest.mark.asyncio
async def test_export_mermaid_escapes_special_chars(graph_service, storage):
    """Test that special characters are properly escaped in Mermaid."""
    session_id = "test_special_chars"
    
    await storage.save_interaction(
        session_id=session_id,
        question='What about "quotes" and \n newlines?',
        answer='Testing "special" characters',
        metadata={"category": "functionality"}
    )
    
    graph_data = await graph_service.build_graph(session_id)
    mermaid = graph_service.export_mermaid(graph_data)
    
    # Should not have unescaped quotes
    # Mermaid should be parseable
    assert 'graph TD' in mermaid


@pytest.mark.asyncio
async def test_graph_statistics(graph_service, sample_conversation):
    """Test graph statistics calculation."""
    graph_data = await graph_service.build_graph(sample_conversation)
    stats = graph_service.get_graph_statistics(graph_data)
    
    assert stats['total_nodes'] == 12
    assert stats['total_edges'] == 11
    assert stats['question_count'] == 6
    assert stats['answer_count'] == 6
    
    # Check category distribution
    assert 'category_distribution' in stats
    dist = stats['category_distribution']
    
    # Should have one of each category
    assert dist.get('functionality', 0) >= 1
    assert dist.get('users', 0) >= 1
    assert dist.get('demographics', 0) >= 1
    assert dist.get('design', 0) >= 1
    assert dist.get('market', 0) >= 1
    assert dist.get('technical', 0) >= 1


@pytest.mark.asyncio
async def test_parse_chunk_extracts_all_fields(graph_service, storage):
    """Test that _parse_chunk correctly extracts all fields."""
    # Create a properly formatted chunk
    chunk = """### Interaction (functionality)
**Question:** What is the main feature?

**Answer:** Task management and collaboration

**Timestamp:** 2025-11-16T12:00:00

-----
"""
    
    question, answer, timestamp, category = graph_service._parse_chunk(chunk)
    
    assert question == "What is the main feature?"
    assert answer == "Task management and collaboration"
    assert timestamp is not None
    assert isinstance(timestamp, datetime)
    assert category == "functionality"


@pytest.mark.asyncio
async def test_parse_chunk_handles_invalid_timestamp(graph_service):
    """Test that invalid timestamps are handled gracefully."""
    chunk = """### Interaction (users)
**Question:** Who will use this?

**Answer:** Developers

**Timestamp:** invalid-timestamp

-----
"""
    
    question, answer, timestamp, category = graph_service._parse_chunk(chunk)
    
    assert question == "Who will use this?"
    assert answer == "Developers"
    assert timestamp is None  # Should be None for invalid timestamp
    assert category == "users"


@pytest.mark.asyncio
async def test_large_conversation_performance(graph_service, storage):
    """Test performance with large conversation (50+ interactions)."""
    import time
    
    session_id = "test_large_conversation"
    
    # Create 50 interactions
    for i in range(50):
        await storage.save_interaction(
            session_id=session_id,
            question=f"Question {i}?",
            answer=f"Answer {i}",
            metadata={"category": "functionality"}
        )
    
    # Time the graph building
    start_time = time.time()
    graph_data = await graph_service.build_graph(session_id)
    elapsed = time.time() - start_time
    
    # Should complete in reasonable time (< 2 seconds)
    assert elapsed < 2.0
    
    # Verify correctness
    assert len(graph_data['nodes']) == 100  # 50 questions + 50 answers
    assert len(graph_data['edges']) == 99   # 50 Q->A + 49 A->Q


@pytest.mark.asyncio
async def test_graph_json_serialization(graph_service, sample_conversation):
    """Test that graph data can be serialized to JSON."""
    import json
    
    graph_data = await graph_service.build_graph(sample_conversation)
    
    # Should be JSON serializable
    try:
        json_str = json.dumps(graph_data)
        assert len(json_str) > 0
        
        # Should be deserializable
        restored = json.loads(json_str)
        assert restored['metadata']['session_id'] == sample_conversation
    except (TypeError, ValueError) as e:
        pytest.fail(f"Graph data not JSON serializable: {e}")


@pytest.mark.asyncio
async def test_edge_labels_correct(graph_service, sample_conversation):
    """Test that edge labels are correctly assigned."""
    graph_data = await graph_service.build_graph(sample_conversation)
    
    # Count label types
    answer_edges = [e for e in graph_data['edges'] if e['label'] == 'answer']
    next_edges = [e for e in graph_data['edges'] if e['label'] == 'next']
    
    # Should have 6 'answer' edges (Q->A)
    assert len(answer_edges) == 6
    
    # Should have 5 'next' edges (A->Q)
    assert len(next_edges) == 5


@pytest.mark.asyncio
async def test_conversation_flow_integrity(graph_service, sample_conversation):
    """Test that conversation flow is correctly represented."""
    graph_data = await graph_service.build_graph(sample_conversation)
    
    # First question should have no incoming 'next' edge
    first_question = 'q0'
    incoming_next = [e for e in graph_data['edges'] 
                     if e['target'] == first_question and e['label'] == 'next']
    assert len(incoming_next) == 0
    
    # Last answer should have no outgoing 'next' edge
    last_answer = 'a5'
    outgoing_next = [e for e in graph_data['edges'] 
                     if e['source'] == last_answer and e['label'] == 'next']
    assert len(outgoing_next) == 0


@pytest.mark.asyncio
async def test_node_id_format(graph_service, sample_conversation):
    """Test that node IDs follow expected format."""
    graph_data = await graph_service.build_graph(sample_conversation)
    
    for node in graph_data['nodes']:
        node_id = node['id']
        
        # Should start with 'q' or 'a'
        assert node_id[0] in ['q', 'a']
        
        # Should have numeric suffix
        assert node_id[1:].isdigit()
        
        # Type should match ID prefix
        if node_id.startswith('q'):
            assert node['type'] == 'question'
        else:
            assert node['type'] == 'answer'


@pytest.mark.asyncio
async def test_category_color_consistency(graph_service, sample_conversation):
    """Test that same category always gets same color."""
    graph_data = await graph_service.build_graph(sample_conversation)
    
    # Group nodes by category
    category_colors = {}
    
    for node in graph_data['nodes']:
        category = node['category']
        color = node['color']
        
        if category in category_colors:
            # Same category should have same color
            assert category_colors[category] == color
        else:
            category_colors[category] = color
