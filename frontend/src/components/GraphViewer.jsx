/**
 * GraphViewer Component with LangGraph State Management
 * 
 * Interactive graph visualization using React Flow and LangGraph backend.
 * Manages complex state through LangGraph StateGraph for clean architecture.
 */

import { useEffect, useState, useCallback, useMemo } from 'react'
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Panel
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Download, Filter, Search, X } from 'lucide-react'
import api from '../services/api'
import './GraphViewer.css'

const CATEGORY_COLORS = {
  functionality: '#3B82F6',
  users: '#10B981',
  demographics: '#F59E0B',
  design: '#8B5CF6',
  market: '#EF4444',
  technical: '#6366F1',
  general: '#6B7280'
}

const CATEGORY_LABELS = {
  functionality: 'Functionality',
  users: 'Users',
  demographics: 'Demographics',
  design: 'Design',
  market: 'Market',
  technical: 'Technical',
  general: 'General'
}

export function GraphViewer({ sessionId }) {
  // LangGraph state from backend
  const [langGraphState, setLangGraphState] = useState(null)
  
  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  
  // UI state
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [showFilters, setShowFilters] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeCategories, setActiveCategories] = useState([])
  const [metadata, setMetadata] = useState({})
  
  // Initialize graph viewer with LangGraph
  useEffect(() => {
    if (sessionId) {
      initializeGraphViewer()
    }
  }, [sessionId])
  
  const initializeGraphViewer = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.get(`/graph/viewer/initialize/${sessionId}`)
      const { state, nodes: graphNodes, edges: graphEdges, metadata: meta, filters } = response.data
      
      // Store LangGraph state
      setLangGraphState(state)
      
      // Convert to React Flow format
      const flowNodes = convertToFlowNodes(graphNodes)
      const flowEdges = convertToFlowEdges(graphEdges)
      
      setNodes(flowNodes)
      setEdges(flowEdges)
      setMetadata(meta)
      setActiveCategories(filters.active_categories || [])
      setSearchQuery(filters.search_query || '')
      
    } catch (err) {
      console.error('Failed to initialize graph viewer:', err)
      setError(err.response?.data?.detail || 'Failed to load graph')
    } finally {
      setLoading(false)
    }
  }
  
  const convertToFlowNodes = (graphNodes) => {
    return graphNodes.map((node, index) => {
      const isQuestion = node.type === 'question'
      
      return {
        id: node.id,
        type: 'default',
        data: {
          label: truncateText(node.content, 50),
          fullContent: node.content,
          category: node.category,
          timestamp: node.timestamp,
          nodeType: node.type
        },
        position: calculateNodePosition(index, graphNodes.length),
        style: {
          background: node.color,
          color: '#fff',
          border: '2px solid #222',
          borderRadius: isQuestion ? '8px' : '20px',
          padding: '12px 16px',
          fontSize: '14px',
          fontWeight: '500',
          minWidth: '200px',
          maxWidth: '300px',
          cursor: 'pointer'
        }
      }
    })
  }
  
  const convertToFlowEdges = (graphEdges) => {
    return graphEdges.map((edge, index) => ({
      id: `${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      animated: edge.label === 'answer',
      style: {
        stroke: '#888',
        strokeWidth: 2
      },
      labelStyle: {
        fill: '#666',
        fontSize: 12
      }
    }))
  }
  
  const calculateNodePosition = (index, total) => {
    // Hierarchical layout: questions and answers in vertical columns
    const row = Math.floor(index / 2)
    const col = index % 2
    
    return {
      x: col * 400 + 100,
      y: row * 150 + 50
    }
  }
  
  const truncateText = (text, maxLength) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }
  
  // Handle node click - select node via LangGraph
  const onNodeClick = useCallback(async (event, node) => {
    try {
      const response = await api.post(`/graph/viewer/select/${sessionId}`, {
        node_id: node.id
      }, {
        headers: {
          'Content-Type': 'application/json'
        },
        data: langGraphState
      })
      
      const { state, selected_node } = response.data
      
      setLangGraphState(state)
      setSelectedNode(selected_node)
      
    } catch (err) {
      console.error('Failed to select node:', err)
    }
  }, [sessionId, langGraphState])
  
  // Update filters via LangGraph
  const updateFilters = async (categories = null, search = null) => {
    setLoading(true)
    
    try {
      const filterRequest = {}
      
      if (categories !== null) {
        filterRequest.active_categories = categories
      }
      if (search !== null) {
        filterRequest.search_query = search
      }
      
      const response = await api.post(`/graph/viewer/filter/${sessionId}`, filterRequest, {
        headers: {
          'Content-Type': 'application/json'
        },
        data: langGraphState
      })
      
      const { state, nodes: graphNodes, edges: graphEdges } = response.data
      
      setLangGraphState(state)
      
      // Update React Flow
      const flowNodes = convertToFlowNodes(graphNodes)
      const flowEdges = convertToFlowEdges(graphEdges)
      
      setNodes(flowNodes)
      setEdges(flowEdges)
      
      if (categories !== null) setActiveCategories(categories)
      if (search !== null) setSearchQuery(search)
      
    } catch (err) {
      console.error('Failed to update filters:', err)
      setError('Failed to update filters')
    } finally {
      setLoading(false)
    }
  }
  
  // Toggle category filter
  const toggleCategory = (category) => {
    const newCategories = activeCategories.includes(category)
      ? activeCategories.filter(c => c !== category)
      : [...activeCategories, category]
    
    updateFilters(newCategories, null)
  }
  
  // Handle search
  const handleSearch = (query) => {
    updateFilters(null, query)
  }
  
  // Export graph via LangGraph
  const exportGraph = async (format) => {
    try {
      const response = await api.post(`/graph/viewer/export/${sessionId}`, {
        format
      }, {
        headers: {
          'Content-Type': 'application/json'
        },
        data: langGraphState
      })
      
      const { export_data, format: exportFormat } = response.data
      
      // Handle different export formats
      if (exportFormat === 'json') {
        downloadJSON(export_data, `graph-${sessionId}.json`)
      } else if (exportFormat === 'mermaid') {
        downloadText(export_data.mermaid, `graph-${sessionId}.mmd`)
      } else if (exportFormat === 'statistics') {
        downloadJSON(export_data, `graph-stats-${sessionId}.json`)
      }
      
    } catch (err) {
      console.error('Failed to export graph:', err)
      setError('Failed to export graph')
    }
  }
  
  const downloadJSON = (data, filename) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  }
  
  const downloadText = (text, filename) => {
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  }
  
  // Export as image (PNG)
  const exportAsImage = async () => {
    const { default: html2canvas } = await import('html2canvas')
    
    const element = document.querySelector('.react-flow')
    if (element) {
      const canvas = await html2canvas(element, {
        backgroundColor: '#ffffff'
      })
      
      const url = canvas.toDataURL('image/png')
      const link = document.createElement('a')
      link.href = url
      link.download = `conversation-graph-${sessionId}.png`
      link.click()
    }
  }
  
  if (loading && !langGraphState) {
    return (
      <div className="graph-viewer-loading">
        <div className="spinner" />
        <p>Loading conversation graph...</p>
      </div>
    )
  }
  
  if (error && !langGraphState) {
    return (
      <div className="graph-viewer-error">
        <p className="error-message">{error}</p>
        <button onClick={initializeGraphViewer} className="retry-button">
          Retry
        </button>
      </div>
    )
  }
  
  return (
    <div className="graph-viewer">
      <div className="graph-header">
        <div className="header-left">
          <h2>Conversation Flow</h2>
          <div className="graph-stats">
            <span className="stat">
              {metadata.total_interactions || 0} interactions
            </span>
            <span className="stat">
              {metadata.duration_minutes || 0} minutes
            </span>
            <span className="stat">
              {nodes.length} nodes visible
            </span>
          </div>
        </div>
        
        <div className="header-actions">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`action-button ${showFilters ? 'active' : ''}`}
            title="Toggle filters"
          >
            <Filter size={18} />
            Filters
          </button>
          
          <div className="export-dropdown">
            <button className="action-button" title="Export options">
              <Download size={18} />
              Export
            </button>
            <div className="dropdown-menu">
              <button onClick={() => exportGraph('json')}>Export as JSON</button>
              <button onClick={() => exportGraph('mermaid')}>Export as Mermaid</button>
              <button onClick={() => exportGraph('statistics')}>Export Statistics</button>
              <button onClick={exportAsImage}>Export as PNG</button>
            </div>
          </div>
        </div>
      </div>
      
      {showFilters && (
        <div className="filters-panel">
          <div className="search-box">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search in conversation..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch(searchQuery)}
            />
            {searchQuery && (
              <button onClick={() => handleSearch('')} className="clear-search">
                <X size={16} />
              </button>
            )}
          </div>
          
          <div className="category-filters">
            <label>Categories:</label>
            <div className="category-chips">
              {Object.entries(CATEGORY_COLORS).map(([category, color]) => (
                <button
                  key={category}
                  onClick={() => toggleCategory(category)}
                  className={`category-chip ${activeCategories.includes(category) ? 'active' : ''}`}
                  style={{
                    '--category-color': color
                  }}
                >
                  <span className="chip-color" style={{ backgroundColor: color }} />
                  {CATEGORY_LABELS[category]}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
      
      <div className="graph-container" style={{ height: '600px' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView
          minZoom={0.5}
          maxZoom={2}
        >
          <Controls />
          <MiniMap
            nodeColor={(node) => node.style.background}
            maskColor="rgba(0, 0, 0, 0.1)"
          />
          <Background variant="dots" gap={16} size={1} />
          
          <Panel position="bottom-right" className="legend-panel">
            <div className="legend">
              <h4>Legend</h4>
              {Object.entries(CATEGORY_COLORS).map(([category, color]) => (
                <div key={category} className="legend-item">
                  <span
                    className="legend-color"
                    style={{ backgroundColor: color }}
                  />
                  <span className="legend-label">{CATEGORY_LABELS[category]}</span>
                </div>
              ))}
            </div>
          </Panel>
        </ReactFlow>
      </div>
      
      {selectedNode && (
        <div className="node-details-modal" onClick={() => setSelectedNode(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                {selectedNode.type === 'question' ? '❓ Question' : '💬 Answer'}
              </h3>
              <button onClick={() => setSelectedNode(null)} className="close-button">
                <X size={20} />
              </button>
            </div>
            
            <div className="modal-body">
              <div className="node-metadata">
                <span className="metadata-item">
                  <strong>Category:</strong>
                  <span
                    className="category-badge"
                    style={{ backgroundColor: selectedNode.color }}
                  >
                    {CATEGORY_LABELS[selectedNode.category]}
                  </span>
                </span>
                <span className="metadata-item">
                  <strong>Timestamp:</strong>
                  {new Date(selectedNode.timestamp).toLocaleString()}
                </span>
              </div>
              
              <div className="node-content">
                {selectedNode.content}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {loading && langGraphState && (
        <div className="loading-overlay">
          <div className="spinner" />
        </div>
      )}
    </div>
  )
}
