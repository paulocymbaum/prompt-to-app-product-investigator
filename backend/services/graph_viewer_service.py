"""
Graph Viewer Service with LangGraph State Management

This service uses LangGraph to manage the state and flow of graph visualization.
It handles data fetching, filtering, selection, and export operations using
a StateGraph architecture for clean separation of concerns.
"""

from typing import List, Dict, Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
import operator
from services.graph_service import GraphService
from storage.conversation_storage import ConversationStorage
import structlog

logger = structlog.get_logger()


# Define the state schema for graph visualization
class GraphViewerState(TypedDict):
    """State schema for graph viewer with LangGraph"""
    
    # Core graph data
    session_id: str
    raw_graph_data: Optional[Dict]
    
    # Filtered/processed data
    visible_nodes: List[Dict]
    visible_edges: List[Dict]
    
    # User interaction state
    selected_node_id: Optional[str]
    selected_node_data: Optional[Dict]
    
    # Filter state
    active_categories: List[str]
    search_query: str
    
    # Viewport state
    zoom_level: float
    viewport_center: Dict[str, float]
    
    # Export state
    export_format: Optional[str]
    export_data: Optional[bytes]
    
    # Metadata
    loading: bool
    error: Optional[str]
    metadata: Dict


class GraphViewerService:
    """
    Service for managing graph visualization state using LangGraph.
    
    Uses StateGraph to define clean state transitions for:
    - Fetching graph data
    - Filtering nodes by category
    - Selecting and highlighting nodes
    - Exporting graphs in different formats
    - Managing viewport state
    """
    
    def __init__(self, storage: ConversationStorage):
        self.storage = storage
        self.graph_service = GraphService(storage)
        self.state_graph = self._build_state_graph()
    
    def _build_state_graph(self) -> StateGraph:
        """
        Build LangGraph StateGraph for graph viewer operations.
        
        Graph structure:
        - START → fetch_graph → filter_nodes → END
        - filter_nodes → select_node (conditional)
        - filter_nodes → export_graph (conditional)
        - filter_nodes → update_viewport (conditional)
        """
        
        # Define state graph with annotations for list accumulation
        workflow = StateGraph(GraphViewerState)
        
        # Add nodes for each operation
        workflow.add_node("fetch_graph", self._fetch_graph_node)
        workflow.add_node("filter_nodes", self._filter_nodes_node)
        workflow.add_node("select_node", self._select_node_node)
        workflow.add_node("export_graph", self._export_graph_node)
        workflow.add_node("update_viewport", self._update_viewport_node)
        
        # Define edges (workflow flow)
        workflow.set_entry_point("fetch_graph")
        workflow.add_edge("fetch_graph", "filter_nodes")
        
        # Conditional routing from filter_nodes
        workflow.add_conditional_edges(
            "filter_nodes",
            self._route_after_filter,
            {
                "select": "select_node",
                "export": "export_graph",
                "viewport": "update_viewport",
                "end": END
            }
        )
        
        # All operations end after completion
        workflow.add_edge("select_node", END)
        workflow.add_edge("export_graph", END)
        workflow.add_edge("update_viewport", END)
        
        return workflow.compile()
    
    def _route_after_filter(self, state: GraphViewerState) -> str:
        """
        Conditional routing after filtering.
        
        Determines next action based on state:
        - If selected_node_id is set → go to select_node
        - If export_format is set → go to export_graph
        - If viewport changed → go to update_viewport
        - Otherwise → end
        """
        if state.get("selected_node_id"):
            return "select"
        elif state.get("export_format"):
            return "export"
        elif state.get("zoom_level") or state.get("viewport_center"):
            return "viewport"
        else:
            return "end"
    
    async def _fetch_graph_node(self, state: GraphViewerState) -> GraphViewerState:
        """
        Node: Fetch graph data from GraphService.
        
        This is the entry point that loads the raw graph data
        and initializes the state with all nodes and edges.
        """
        logger.info("fetch_graph_node", session_id=state.get("session_id"))
        
        try:
            session_id = state["session_id"]
            
            # Fetch raw graph data
            graph_data = await self.graph_service.build_graph(session_id)
            
            # Update state with fetched data
            return {
                **state,
                "raw_graph_data": graph_data,
                "visible_nodes": graph_data.get("nodes", []),
                "visible_edges": graph_data.get("edges", []),
                "metadata": graph_data.get("metadata", {}),
                "loading": False,
                "error": None,
                # Initialize default filters (show all categories)
                "active_categories": [
                    "functionality", "users", "demographics",
                    "design", "market", "technical", "general"
                ],
                "search_query": "",
                "zoom_level": 1.0,
                "viewport_center": {"x": 0, "y": 0}
            }
        
        except Exception as e:
            logger.error("fetch_graph_failed", error=str(e))
            return {
                **state,
                "loading": False,
                "error": f"Failed to fetch graph: {str(e)}"
            }
    
    def _filter_nodes_node(self, state: GraphViewerState) -> GraphViewerState:
        """
        Node: Filter nodes based on active categories and search query.
        
        Applies both category filtering and text search to determine
        which nodes should be visible in the visualization.
        """
        logger.info(
            "filter_nodes_node",
            active_categories=state.get("active_categories", []),
            search_query=state.get("search_query", "")
        )
        
        raw_graph = state.get("raw_graph_data", {})
        all_nodes = raw_graph.get("nodes", [])
        all_edges = raw_graph.get("edges", [])
        
        active_categories = set(state.get("active_categories", []))
        search_query = state.get("search_query", "").lower()
        
        # Filter nodes by category
        visible_nodes = [
            node for node in all_nodes
            if node.get("category", "general") in active_categories
        ]
        
        # Further filter by search query if present
        if search_query:
            visible_nodes = [
                node for node in visible_nodes
                if search_query in node.get("content", "").lower()
            ]
        
        # Get IDs of visible nodes
        visible_node_ids = {node["id"] for node in visible_nodes}
        
        # Filter edges to only include those between visible nodes
        visible_edges = [
            edge for edge in all_edges
            if edge["source"] in visible_node_ids
            and edge["target"] in visible_node_ids
        ]
        
        logger.info(
            "filter_nodes_complete",
            total_nodes=len(all_nodes),
            visible_nodes=len(visible_nodes),
            visible_edges=len(visible_edges)
        )
        
        return {
            **state,
            "visible_nodes": visible_nodes,
            "visible_edges": visible_edges
        }
    
    def _select_node_node(self, state: GraphViewerState) -> GraphViewerState:
        """
        Node: Select a specific node and load its full details.
        
        When a user clicks on a node, this retrieves the full
        node data including complete content (not truncated).
        """
        logger.info("select_node_node", node_id=state.get("selected_node_id"))
        
        selected_id = state.get("selected_node_id")
        if not selected_id:
            return state
        
        # Find the selected node in visible nodes
        visible_nodes = state.get("visible_nodes", [])
        selected_node = next(
            (node for node in visible_nodes if node["id"] == selected_id),
            None
        )
        
        if selected_node:
            logger.info("node_selected", node_id=selected_id, category=selected_node.get("category"))
            return {
                **state,
                "selected_node_data": selected_node
            }
        else:
            logger.warning("node_not_found", node_id=selected_id)
            return {
                **state,
                "selected_node_data": None,
                "error": f"Node {selected_id} not found"
            }
    
    def _export_graph_node(self, state: GraphViewerState) -> GraphViewerState:
        """
        Node: Export graph in specified format.
        
        Supports:
        - JSON: Raw graph data
        - Mermaid: Diagram format
        - Statistics: Summary data
        """
        logger.info("export_graph_node", format=state.get("export_format"))
        
        export_format = state.get("export_format")
        raw_graph = state.get("raw_graph_data", {})
        
        if export_format == "json":
            # Export visible graph as JSON
            export_data = {
                "nodes": state.get("visible_nodes", []),
                "edges": state.get("visible_edges", []),
                "metadata": state.get("metadata", {})
            }
            return {
                **state,
                "export_data": export_data
            }
        
        elif export_format == "mermaid":
            # Export as Mermaid diagram
            mermaid = self.graph_service.export_mermaid(raw_graph)
            return {
                **state,
                "export_data": {"mermaid": mermaid}
            }
        
        elif export_format == "statistics":
            # Export graph statistics
            stats = self.graph_service.get_graph_statistics(raw_graph)
            return {
                **state,
                "export_data": stats
            }
        
        else:
            logger.error("invalid_export_format", format=export_format)
            return {
                **state,
                "error": f"Invalid export format: {export_format}"
            }
    
    def _update_viewport_node(self, state: GraphViewerState) -> GraphViewerState:
        """
        Node: Update viewport state (zoom, pan).
        
        Stores viewport transformations for maintaining
        user's view when state updates.
        """
        logger.info(
            "update_viewport_node",
            zoom=state.get("zoom_level"),
            center=state.get("viewport_center")
        )
        
        # State is already updated, just log and return
        return state
    
    async def get_initial_state(self, session_id: str) -> GraphViewerState:
        """
        Get initial state for a session.
        
        This is the entry point for the frontend to initialize
        the graph viewer with LangGraph state management.
        """
        initial_state: GraphViewerState = {
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
        
        # Run through state graph to fetch and initialize
        result = await self.state_graph.ainvoke(initial_state)
        
        return result
    
    async def update_filters(
        self,
        session_id: str,
        current_state: GraphViewerState,
        active_categories: Optional[List[str]] = None,
        search_query: Optional[str] = None
    ) -> GraphViewerState:
        """
        Update filter state and recompute visible nodes.
        
        Args:
            session_id: Session identifier
            current_state: Current state of the graph viewer
            active_categories: Categories to show (if provided)
            search_query: Search text (if provided)
        
        Returns:
            Updated state with filtered nodes
        """
        # Update filter parameters
        updated_state = {
            **current_state,
            "session_id": session_id
        }
        
        if active_categories is not None:
            updated_state["active_categories"] = active_categories
        
        if search_query is not None:
            updated_state["search_query"] = search_query
        
        # Run through filter node
        result = self._filter_nodes_node(updated_state)
        
        return result
    
    async def select_node(
        self,
        session_id: str,
        current_state: GraphViewerState,
        node_id: str
    ) -> GraphViewerState:
        """
        Select a node and load its details.
        
        Args:
            session_id: Session identifier
            current_state: Current state
            node_id: ID of node to select
        
        Returns:
            Updated state with selected node data
        """
        updated_state = {
            **current_state,
            "session_id": session_id,
            "selected_node_id": node_id
        }
        
        # Run through select node
        result = self._select_node_node(updated_state)
        
        return result
    
    async def export_graph(
        self,
        session_id: str,
        current_state: GraphViewerState,
        export_format: str
    ) -> GraphViewerState:
        """
        Export graph in specified format.
        
        Args:
            session_id: Session identifier
            current_state: Current state
            export_format: 'json', 'mermaid', or 'statistics'
        
        Returns:
            Updated state with export data
        """
        updated_state = {
            **current_state,
            "session_id": session_id,
            "export_format": export_format
        }
        
        # Run through export node
        result = self._export_graph_node(updated_state)
        
        return result
    
    async def update_viewport(
        self,
        session_id: str,
        current_state: GraphViewerState,
        zoom_level: Optional[float] = None,
        viewport_center: Optional[Dict[str, float]] = None
    ) -> GraphViewerState:
        """
        Update viewport state (zoom/pan).
        
        Args:
            session_id: Session identifier
            current_state: Current state
            zoom_level: New zoom level (if provided)
            viewport_center: New center position (if provided)
        
        Returns:
            Updated state with viewport changes
        """
        updated_state = {
            **current_state,
            "session_id": session_id
        }
        
        if zoom_level is not None:
            updated_state["zoom_level"] = zoom_level
        
        if viewport_center is not None:
            updated_state["viewport_center"] = viewport_center
        
        # Run through viewport node
        result = self._update_viewport_node(updated_state)
        
        return result
