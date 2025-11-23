"""
Graph Viewer API Routes with LangGraph State Management

Enhanced routes that use GraphViewerService with LangGraph
for managing complex UI state and interactions.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional
from pydantic import BaseModel
from services.graph_viewer_service import GraphViewerService, GraphViewerState
from storage.conversation_storage import ConversationStorage
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/graph/viewer", tags=["graph-viewer"])


# Request/Response models
class FilterRequest(BaseModel):
    """Request to update filters"""
    active_categories: Optional[List[str]] = None
    search_query: Optional[str] = None


class SelectNodeRequest(BaseModel):
    """Request to select a node"""
    node_id: str


class ExportRequest(BaseModel):
    """Request to export graph"""
    format: str  # 'json', 'mermaid', or 'statistics'


class ViewportRequest(BaseModel):
    """Request to update viewport"""
    zoom_level: Optional[float] = None
    viewport_center: Optional[Dict[str, float]] = None


# Dependency to get GraphViewerService instance
def get_graph_viewer_service() -> GraphViewerService:
    """
    Create and return a GraphViewerService instance.
    
    Returns:
        GraphViewerService instance with LangGraph state management
    """
    storage = ConversationStorage()
    return GraphViewerService(storage=storage)


@router.get("/initialize/{session_id}")
async def initialize_graph_viewer(
    session_id: str,
    service: GraphViewerService = Depends(get_graph_viewer_service)
) -> Dict:
    """
    Initialize graph viewer with LangGraph state.
    
    This endpoint fetches the graph data and returns the initial state
    managed by LangGraph. The frontend can then use this state to
    render the visualization and maintain consistency.
    
    Args:
        session_id: Unique session identifier
        service: Injected GraphViewerService instance
        
    Returns:
        Dict with:
        - state: Complete LangGraph state for the graph viewer
        - nodes: Visible nodes list
        - edges: Visible edges list
        - metadata: Session metadata
        - filters: Active filter configuration
        
    Example Response:
    ```json
    {
        "state": {
            "session_id": "session_123",
            "visible_nodes": [...],
            "visible_edges": [...],
            "metadata": {...},
            "active_categories": ["functionality", "users", ...],
            "loading": false,
            "error": null
        },
        "nodes": [...],
        "edges": [...],
        "metadata": {...}
    }
    ```
    
    Raises:
        HTTPException 404: Session not found or no conversation data
        HTTPException 500: Internal server error during initialization
    """
    logger.info("initialize_graph_viewer_requested", session_id=session_id)
    
    try:
        # Get initial state through LangGraph
        state = await service.get_initial_state(session_id)
        
        # Check if there was an error
        if state.get("error"):
            error_msg = state.get("error", "")
            logger.error(
                "initialization_failed",
                session_id=session_id,
                error=error_msg
            )
            status_code = 404 if error_msg and "not found" in error_msg.lower() else 500
            raise HTTPException(
                status_code=status_code,
                detail=error_msg
            )
        
        # Check if graph is empty (no conversation found)
        if not state.get("visible_nodes"):
            logger.warning(
                "empty_graph",
                session_id=session_id
            )
            raise HTTPException(
                status_code=404,
                detail=f"No conversation found for session: {session_id}"
            )
        
        logger.info(
            "graph_viewer_initialized",
            session_id=session_id,
            node_count=len(state.get("visible_nodes", [])),
            edge_count=len(state.get("visible_edges", []))
        )
        
        # Return state in a frontend-friendly format
        return {
            "state": state,
            "nodes": state.get("visible_nodes", []),
            "edges": state.get("visible_edges", []),
            "metadata": state.get("metadata", {}),
            "filters": {
                "active_categories": state.get("active_categories", []),
                "search_query": state.get("search_query", "")
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "failed_to_initialize_graph_viewer",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize graph viewer: {str(e)}"
        )


@router.post("/filter/{session_id}")
async def update_filters(
    session_id: str,
    request: FilterRequest,
    current_state: GraphViewerState,
    service: GraphViewerService = Depends(get_graph_viewer_service)
) -> Dict:
    """
    Update graph filters using LangGraph state management.
    
    Filters the visible nodes based on categories and search query.
    LangGraph manages the state transition and ensures consistency.
    
    Args:
        session_id: Unique session identifier
        request: Filter configuration
        current_state: Current state from frontend
        service: Injected GraphViewerService instance
        
    Returns:
        Dict with:
        - state: Updated LangGraph state
        - nodes: Filtered nodes list
        - edges: Filtered edges list
        
    Example Request:
    ```json
    {
        "active_categories": ["functionality", "technical"],
        "search_query": "api"
    }
    ```
    
    Raises:
        HTTPException 500: Internal server error during filtering
    """
    logger.info(
        "update_filters_requested",
        session_id=session_id,
        categories=request.active_categories,
        search_query=request.search_query
    )
    
    try:
        # Update filters through LangGraph
        updated_state = await service.update_filters(
            session_id=session_id,
            current_state=current_state,
            active_categories=request.active_categories,
            search_query=request.search_query
        )
        
        logger.info(
            "filters_updated",
            session_id=session_id,
            visible_nodes=len(updated_state.get("visible_nodes", [])),
            visible_edges=len(updated_state.get("visible_edges", []))
        )
        
        return {
            "state": updated_state,
            "nodes": updated_state.get("visible_nodes", []),
            "edges": updated_state.get("visible_edges", [])
        }
        
    except Exception as e:
        logger.error(
            "failed_to_update_filters",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update filters: {str(e)}"
        )


@router.post("/select/{session_id}")
async def select_node(
    session_id: str,
    request: SelectNodeRequest,
    current_state: GraphViewerState,
    service: GraphViewerService = Depends(get_graph_viewer_service)
) -> Dict:
    """
    Select a node and load its full details using LangGraph.
    
    When a user clicks on a node in the graph, this endpoint
    processes the selection through LangGraph and returns
    the complete node data.
    
    Args:
        session_id: Unique session identifier
        request: Node selection request with node_id
        current_state: Current state from frontend
        service: Injected GraphViewerService instance
        
    Returns:
        Dict with:
        - state: Updated state with selected node data
        - selected_node: Complete node object
        
    Example Request:
    ```json
    {
        "node_id": "q3"
    }
    ```
    
    Example Response:
    ```json
    {
        "state": {...},
        "selected_node": {
            "id": "q3",
            "type": "question",
            "content": "What technology stack will you use?",
            "category": "technical",
            "color": "#6366F1",
            "timestamp": "2025-11-16T12:05:30"
        }
    }
    ```
    
    Raises:
        HTTPException 404: Node not found
        HTTPException 500: Internal server error
    """
    logger.info(
        "select_node_requested",
        session_id=session_id,
        node_id=request.node_id
    )
    
    try:
        # Select node through LangGraph
        updated_state = await service.select_node(
            session_id=session_id,
            current_state=current_state,
            node_id=request.node_id
        )
        
        # Check if node was found
        if updated_state.get("error"):
            logger.warning(
                "node_not_found",
                session_id=session_id,
                node_id=request.node_id
            )
            raise HTTPException(
                status_code=404,
                detail=updated_state["error"]
            )
        
        selected_node = updated_state.get("selected_node_data")
        
        logger.info(
            "node_selected",
            session_id=session_id,
            node_id=request.node_id,
            category=selected_node.get("category") if selected_node else None
        )
        
        return {
            "state": updated_state,
            "selected_node": selected_node
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "failed_to_select_node",
            session_id=session_id,
            node_id=request.node_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to select node: {str(e)}"
        )


@router.post("/export/{session_id}")
async def export_graph(
    session_id: str,
    request: ExportRequest,
    current_state: GraphViewerState,
    service: GraphViewerService = Depends(get_graph_viewer_service)
) -> Dict:
    """
    Export graph in specified format using LangGraph.
    
    Supports multiple export formats managed through LangGraph state:
    - 'json': Raw graph data
    - 'mermaid': Mermaid diagram format
    - 'statistics': Graph statistics
    
    Args:
        session_id: Unique session identifier
        request: Export configuration
        current_state: Current state from frontend
        service: Injected GraphViewerService instance
        
    Returns:
        Dict with:
        - state: Updated state with export data
        - export_data: Exported data in requested format
        - format: Export format used
        
    Example Request:
    ```json
    {
        "format": "mermaid"
    }
    ```
    
    Raises:
        HTTPException 400: Invalid export format
        HTTPException 500: Internal server error
    """
    logger.info(
        "export_graph_requested",
        session_id=session_id,
        format=request.format
    )
    
    # Validate format
    valid_formats = ["json", "mermaid", "statistics"]
    if request.format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format '{request.format}'. Must be one of: {valid_formats}"
        )
    
    try:
        # Export through LangGraph
        updated_state = await service.export_graph(
            session_id=session_id,
            current_state=current_state,
            export_format=request.format
        )
        
        # Check for errors
        if updated_state.get("error"):
            logger.error(
                "export_failed",
                session_id=session_id,
                error=updated_state["error"]
            )
            raise HTTPException(
                status_code=500,
                detail=updated_state["error"]
            )
        
        export_data = updated_state.get("export_data")
        
        logger.info(
            "graph_exported",
            session_id=session_id,
            format=request.format,
            data_size=len(str(export_data)) if export_data else 0
        )
        
        return {
            "state": updated_state,
            "export_data": export_data,
            "format": request.format
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "failed_to_export_graph",
            session_id=session_id,
            format=request.format,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export graph: {str(e)}"
        )


@router.post("/viewport/{session_id}")
async def update_viewport(
    session_id: str,
    request: ViewportRequest,
    current_state: GraphViewerState,
    service: GraphViewerService = Depends(get_graph_viewer_service)
) -> Dict:
    """
    Update viewport state (zoom/pan) using LangGraph.
    
    Stores viewport transformations so the view can be
    maintained across state updates and interactions.
    
    Args:
        session_id: Unique session identifier
        request: Viewport configuration
        current_state: Current state from frontend
        service: Injected GraphViewerService instance
        
    Returns:
        Dict with:
        - state: Updated state with viewport changes
        - viewport: Current viewport configuration
        
    Example Request:
    ```json
    {
        "zoom_level": 1.5,
        "viewport_center": {"x": 200, "y": 300}
    }
    ```
    
    Raises:
        HTTPException 500: Internal server error
    """
    logger.info(
        "update_viewport_requested",
        session_id=session_id,
        zoom=request.zoom_level,
        center=request.viewport_center
    )
    
    try:
        # Update viewport through LangGraph
        updated_state = await service.update_viewport(
            session_id=session_id,
            current_state=current_state,
            zoom_level=request.zoom_level,
            viewport_center=request.viewport_center
        )
        
        logger.info(
            "viewport_updated",
            session_id=session_id,
            zoom=updated_state.get("zoom_level"),
            center=updated_state.get("viewport_center")
        )
        
        return {
            "state": updated_state,
            "viewport": {
                "zoom_level": updated_state.get("zoom_level"),
                "viewport_center": updated_state.get("viewport_center")
            }
        }
        
    except Exception as e:
        logger.error(
            "failed_to_update_viewport",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update viewport: {str(e)}"
        )
