"""
Graph API Routes

Provides REST API endpoints for conversation graph visualization.
Uses GraphService to build and export conversation graphs.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
from services.graph_service import GraphService
from storage.conversation_storage import ConversationStorage
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/graph", tags=["graph"])


# Dependency to get GraphService instance
def get_graph_service() -> GraphService:
    """
    Create and return a GraphService instance.
    
    Returns:
        GraphService instance
    """
    storage = ConversationStorage()
    return GraphService(storage=storage)


@router.get("/visualization/{session_id}")
async def get_visualization(
    session_id: str,
    graph_service: GraphService = Depends(get_graph_service)
) -> Dict:
    """
    Get conversation graph visualization data.
    
    Returns a JSON structure with nodes, edges, and metadata
    suitable for frontend graph visualization (React Flow, etc.).
    
    Args:
        session_id: Unique session identifier
        graph_service: Injected GraphService instance
        
    Returns:
        Dict with:
        - nodes: List of graph nodes (questions and answers)
        - edges: List of graph edges (relationships)
        - metadata: Session metadata (timestamps, counts, duration)
        
    Example Response:
    ```json
    {
        "nodes": [
            {
                "id": "q0",
                "type": "question",
                "content": "What is your product?",
                "category": "functionality",
                "color": "#3B82F6",
                "timestamp": "2025-11-16T12:00:00",
                "shape": "rectangle"
            },
            {
                "id": "a0",
                "type": "answer",
                "content": "A task management app",
                "category": "functionality",
                "color": "#3B82F6",
                "timestamp": "2025-11-16T12:00:30",
                "shape": "rounded"
            }
        ],
        "edges": [
            {
                "source": "q0",
                "target": "a0",
                "label": "answer"
            }
        ],
        "metadata": {
            "session_id": "session_123",
            "total_interactions": 6,
            "created_at": "2025-11-16T12:00:00",
            "duration_minutes": 12.5
        }
    }
    ```
    
    Raises:
        HTTPException 404: Session not found or no conversation data
        HTTPException 500: Internal server error during graph building
    """
    logger.info("get_visualization_requested", session_id=session_id)
    
    try:
        # Build graph data
        graph_data = await graph_service.build_graph(session_id)
        
        # Check if graph is empty (no conversation found)
        if not graph_data.get('nodes'):
            logger.warning(
                "conversation_not_found_or_empty",
                session_id=session_id
            )
            raise HTTPException(
                status_code=404,
                detail=f"No conversation found for session: {session_id}"
            )
        
        logger.info(
            "visualization_built_successfully",
            session_id=session_id,
            node_count=len(graph_data['nodes']),
            edge_count=len(graph_data['edges'])
        )
        
        return graph_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "failed_to_build_visualization",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build graph visualization: {str(e)}"
        )


@router.get("/mermaid/{session_id}")
async def get_mermaid(
    session_id: str,
    graph_service: GraphService = Depends(get_graph_service)
) -> Dict[str, str]:
    """
    Get conversation graph as Mermaid diagram format.
    
    Returns Mermaid flowchart syntax that can be rendered by
    Mermaid.js or other Mermaid-compatible tools.
    
    Args:
        session_id: Unique session identifier
        graph_service: Injected GraphService instance
        
    Returns:
        Dict with:
        - mermaid: Mermaid diagram string
        - session_id: Session identifier (for reference)
        
    Example Response:
    ```json
    {
        "mermaid": "graph TD\\n    q0[\\\"What is your product?\\\"]\\n    style q0 fill:#3B82F6,stroke:#000,stroke-width:2px,color:#fff\\n    a0(\\\"A task management app\\\")\\n    style a0 fill:#3B82F6,stroke:#000,stroke-width:2px,color:#fff\\n    q0 -->|answer| a0",
        "session_id": "session_123"
    }
    ```
    
    Raises:
        HTTPException 404: Session not found or no conversation data
        HTTPException 500: Internal server error during export
    """
    logger.info("get_mermaid_requested", session_id=session_id)
    
    try:
        # Build graph data first
        graph_data = await graph_service.build_graph(session_id)
        
        # Check if graph is empty
        if not graph_data.get('nodes'):
            logger.warning(
                "conversation_not_found_or_empty_for_mermaid",
                session_id=session_id
            )
            raise HTTPException(
                status_code=404,
                detail=f"No conversation found for session: {session_id}"
            )
        
        # Export to Mermaid format
        mermaid_diagram = graph_service.export_mermaid(graph_data)
        
        logger.info(
            "mermaid_diagram_generated",
            session_id=session_id,
            diagram_length=len(mermaid_diagram)
        )
        
        return {
            "mermaid": mermaid_diagram,
            "session_id": session_id
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "failed_to_generate_mermaid",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Mermaid diagram: {str(e)}"
        )


@router.get("/statistics/{session_id}")
async def get_statistics(
    session_id: str,
    graph_service: GraphService = Depends(get_graph_service)
) -> Dict:
    """
    Get conversation graph statistics.
    
    Returns statistical information about the conversation graph
    including node counts, category distribution, and metadata.
    
    Args:
        session_id: Unique session identifier
        graph_service: Injected GraphService instance
        
    Returns:
        Dict with:
        - total_nodes: Total number of nodes
        - total_edges: Total number of edges
        - question_count: Number of question nodes
        - answer_count: Number of answer nodes
        - category_distribution: Breakdown by category
        - metadata: Session metadata
        
    Example Response:
    ```json
    {
        "total_nodes": 12,
        "total_edges": 11,
        "question_count": 6,
        "answer_count": 6,
        "category_distribution": {
            "functionality": 2,
            "users": 1,
            "technical": 2,
            "design": 1
        },
        "metadata": {
            "session_id": "session_123",
            "total_interactions": 6,
            "created_at": "2025-11-16T12:00:00",
            "duration_minutes": 12.5
        }
    }
    ```
    
    Raises:
        HTTPException 404: Session not found or no conversation data
        HTTPException 500: Internal server error
    """
    logger.info("get_statistics_requested", session_id=session_id)
    
    try:
        # Build graph data
        graph_data = await graph_service.build_graph(session_id)
        
        # Check if graph is empty
        if not graph_data.get('nodes'):
            logger.warning(
                "conversation_not_found_for_statistics",
                session_id=session_id
            )
            raise HTTPException(
                status_code=404,
                detail=f"No conversation found for session: {session_id}"
            )
        
        # Calculate statistics
        statistics = graph_service.get_graph_statistics(graph_data)
        
        logger.info(
            "statistics_calculated",
            session_id=session_id,
            total_nodes=statistics['total_nodes']
        )
        
        return statistics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "failed_to_calculate_statistics",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate graph statistics: {str(e)}"
        )
