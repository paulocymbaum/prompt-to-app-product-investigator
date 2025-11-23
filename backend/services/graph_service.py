"""
Graph Service

Builds conversation flow graphs using LangGraph for visualization.
Provides DAG representation with color-coded categories and metadata.
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime
from storage.conversation_storage import ConversationStorage
import structlog
import re

logger = structlog.get_logger()


class GraphService:
    """
    Service for building conversation graphs with LangGraph.
    
    Features:
    - DAG construction from conversation history
    - Category-based color coding (6 categories)
    - Metadata tracking (timestamps, duration, counts)
    - Mermaid diagram export
    - JSON serialization for frontend
    """
    
    def __init__(self, storage: ConversationStorage):
        """
        Initialize graph service.
        
        Args:
            storage: ConversationStorage instance for loading conversations
        """
        self.storage = storage
        
        # Color mapping for 6 categories
        self.category_colors = {
            'functionality': '#3B82F6',  # blue
            'users': '#10B981',          # green
            'demographics': '#F59E0B',   # amber
            'design': '#8B5CF6',         # purple
            'market': '#EF4444',         # red
            'technical': '#6366F1',      # indigo
            'general': '#6B7280'         # gray (fallback)
        }
        
        logger.info("graph_service_initialized")
    
    async def build_graph(self, session_id: str) -> Dict:
        """
        Build conversation graph from session history.
        
        Creates a DAG with:
        - Question nodes (rectangles)
        - Answer nodes (rounded)
        - Color-coded by category
        - Edges showing conversation flow
        - Metadata (timestamps, duration, counts)
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with nodes, edges, and metadata
            {
                'nodes': [{'id': str, 'type': str, 'content': str, 'category': str, 'color': str, 'timestamp': str}],
                'edges': [{'source': str, 'target': str, 'label': str}],
                'metadata': {'session_id': str, 'total_interactions': int, 'created_at': str, 'duration_minutes': float}
            }
        """
        logger.info("building_graph", session_id=session_id)
        
        # Load conversation
        conversation = await self.storage.load_conversation(session_id)
        
        if not conversation:
            logger.warning("no_conversation_found", session_id=session_id)
            return {
                'nodes': [],
                'edges': [],
                'metadata': {
                    'session_id': session_id,
                    'total_interactions': 0,
                    'created_at': None,
                    'duration_minutes': 0
                }
            }
        
        # Parse into chunks
        chunks = self.storage.parse_chunks(conversation)
        
        # Initialize graph structure
        graph_data = {
            'nodes': [],
            'edges': [],
            'metadata': {
                'session_id': session_id,
                'total_interactions': len(chunks),
                'created_at': None,
                'duration_minutes': 0
            }
        }
        
        # Track for duration calculation
        start_time = None
        end_time = None
        prev_answer_node_id = None
        
        # Build nodes and edges from chunks
        for idx, chunk in enumerate(chunks):
            # Parse chunk
            question, answer, timestamp, category = self._parse_chunk(chunk)
            
            if idx == 0:
                start_time = timestamp
                graph_data['metadata']['created_at'] = timestamp.isoformat() if timestamp else None
            
            if timestamp:
                end_time = timestamp
            
            # Determine category if not in chunk
            if not category or category == 'unknown':
                category = self._categorize_interaction(question)
            
            # Get color
            color = self.category_colors.get(category, self.category_colors['general'])
            
            # Create question node (rectangle shape)
            question_node = {
                'id': f'q{idx}',
                'type': 'question',
                'content': question,
                'category': category,
                'color': color,
                'timestamp': timestamp.isoformat() if timestamp else None,
                'shape': 'rectangle'
            }
            graph_data['nodes'].append(question_node)
            
            # Create answer node (rounded shape)
            answer_node = {
                'id': f'a{idx}',
                'type': 'answer',
                'content': answer,
                'category': category,
                'color': color,
                'timestamp': timestamp.isoformat() if timestamp else None,
                'shape': 'rounded'
            }
            graph_data['nodes'].append(answer_node)
            
            # Create edges
            # Edge from previous answer to current question (conversation flow)
            if prev_answer_node_id:
                graph_data['edges'].append({
                    'source': prev_answer_node_id,
                    'target': question_node['id'],
                    'label': 'next'
                })
            
            # Edge from question to answer (Q&A pair)
            graph_data['edges'].append({
                'source': question_node['id'],
                'target': answer_node['id'],
                'label': 'answer'
            })
            
            prev_answer_node_id = answer_node['id']
        
        # Calculate duration
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds() / 60
            graph_data['metadata']['duration_minutes'] = round(duration, 2)
        
        logger.info(
            "graph_built",
            session_id=session_id,
            node_count=len(graph_data['nodes']),
            edge_count=len(graph_data['edges']),
            duration_minutes=graph_data['metadata']['duration_minutes']
        )
        
        return graph_data
    
    def _parse_chunk(self, chunk: str) -> Tuple[str, str, Optional[datetime], str]:
        """
        Extract question, answer, timestamp, and category from chunk.
        
        Args:
            chunk: Markdown chunk text
            
        Returns:
            Tuple of (question, answer, timestamp, category)
        """
        question = ''
        answer = ''
        timestamp = None
        category = 'unknown'
        
        lines = chunk.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Extract category from header if present
            if line.startswith('### Interaction'):
                # Format: "### Interaction (category)"
                match = re.search(r'\(([^)]+)\)', line)
                if match:
                    category = match.group(1)
            
            # Extract question
            elif line.startswith('**Question:**'):
                question = line.replace('**Question:**', '').strip()
            
            # Extract answer
            elif line.startswith('**Answer:**'):
                answer = line.replace('**Answer:**', '').strip()
            
            # Extract timestamp
            elif line.startswith('**Timestamp:**'):
                timestamp_str = line.replace('**Timestamp:**', '').strip()
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except (ValueError, AttributeError):
                    logger.warning("invalid_timestamp", timestamp_str=timestamp_str)
                    timestamp = None
        
        return question, answer, timestamp, category
    
    def _categorize_interaction(self, question: str) -> str:
        """
        Determine category from question content using keyword matching.
        
        Categories:
        - functionality: Product features, capabilities, purpose
        - users: Target audience, user personas
        - demographics: Age, location, user characteristics
        - design: UI/UX, visual style, aesthetics
        - market: Competition, business model, market position
        - technical: Tech stack, architecture, performance
        - general: Fallback for unclear categorization
        
        Args:
            question: Question text
            
        Returns:
            Category string
        """
        question_lower = question.lower()
        
        # Market keywords (check first for specific cases like "competitors")
        if any(word in question_lower for word in [
            'market', 'competitor', 'business model', 'monetization',
            'monetize', 'revenue', 'pricing', 'competition', 'industry', 'sector'
        ]):
            return 'market'
        
        # Technical keywords (check before design to catch "technical requirements")
        elif any(word in question_lower for word in [
            'technical', 'technology', 'stack', 'performance', 'architecture',
            'framework', 'database', 'backend', 'frontend', 'infrastructure',
            'security', 'scalability', 'integration', 'pattern'
        ]):
            return 'technical'
        
        # Functionality keywords
        elif any(word in question_lower for word in [
            'functionality', 'feature', 'does', 'purpose', 'capability',
            'function', 'what will', 'main goal', 'core feature'
        ]):
            return 'functionality'
        
        # Users keywords
        elif any(word in question_lower for word in [
            'user', 'audience', 'who will', 'target', 'persona',
            'customer', 'end-user', 'client', 'segment', 'who is',
            'who are'
        ]):
            return 'users'
        
        # Demographics keywords
        elif any(word in question_lower for word in [
            'age', 'demographic', 'location', 'geographic', 'region',
            'gender', 'income', 'education', 'occupation'
        ]):
            return 'demographics'
        
        # Design keywords
        elif any(word in question_lower for word in [
            'design', 'style', 'color', 'ui', 'ux', 'interface',
            'visual', 'aesthetic', 'look', 'feel', 'theme', 'layout'
        ]):
            return 'design'
        
        # Default to general
        return 'general'
    
    def export_mermaid(self, graph_data: Dict) -> str:
        """
        Export graph to Mermaid diagram format.
        
        Generates a Mermaid flowchart with:
        - Color-coded nodes by category
        - Rectangle nodes for questions
        - Rounded nodes for answers
        - Labeled edges showing flow
        
        Args:
            graph_data: Graph data dict from build_graph()
            
        Returns:
            Mermaid diagram string
        """
        logger.info("exporting_mermaid", node_count=len(graph_data.get('nodes', [])))
        
        mermaid_lines = ["graph TD"]
        
        # Add nodes with content and styling
        for node in graph_data.get('nodes', []):
            node_id = node['id']
            content = node['content']
            
            # Truncate long content for readability
            if len(content) > 60:
                content = content[:57] + '...'
            
            # Escape special characters
            content = content.replace('"', '\\"').replace('\n', ' ')
            
            # Different shapes for questions vs answers
            if node['type'] == 'question':
                # Rectangle: [content]
                mermaid_lines.append(f'    {node_id}["{content}"]')
            else:
                # Rounded: (content)
                mermaid_lines.append(f'    {node_id}("{content}")')
            
            # Add color styling
            color = node.get('color', '#6B7280')
            mermaid_lines.append(f'    style {node_id} fill:{color},stroke:#000,stroke-width:2px,color:#fff')
        
        # Add edges with labels
        for edge in graph_data.get('edges', []):
            source = edge['source']
            target = edge['target']
            label = edge.get('label', '')
            
            if label:
                mermaid_lines.append(f'    {source} -->|{label}| {target}')
            else:
                mermaid_lines.append(f'    {source} --> {target}')
        
        mermaid_diagram = '\n'.join(mermaid_lines)
        
        logger.info("mermaid_exported", line_count=len(mermaid_lines))
        
        return mermaid_diagram
    
    def get_graph_statistics(self, graph_data: Dict) -> Dict:
        """
        Calculate statistics about the conversation graph.
        
        Args:
            graph_data: Graph data dict
            
        Returns:
            Statistics dict
        """
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        # Count by category
        category_counts = {}
        for node in nodes:
            if node['type'] == 'question':  # Only count questions to avoid duplication
                category = node.get('category', 'general')
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by type
        question_count = sum(1 for n in nodes if n['type'] == 'question')
        answer_count = sum(1 for n in nodes if n['type'] == 'answer')
        
        stats = {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'question_count': question_count,
            'answer_count': answer_count,
            'category_distribution': category_counts,
            'metadata': graph_data.get('metadata', {})
        }
        
        logger.info("graph_statistics_calculated", stats=stats)
        
        return stats
