import { useState, useEffect } from 'react';
import { Save, FolderOpen, Trash2, Clock, MessageSquare, X } from 'lucide-react';
import '../styles/SessionManager.css';

/**
 * SessionManager Component
 * 
 * Handles session management:
 * - Save current session
 * - Load saved sessions
 * - Delete sessions
 * - Auto-save indicator
 */
export function SessionManager({ currentSessionId, onSessionLoad, onSessionSaved }) {
  const [sessions, setSessions] = useState([]);
  const [showLoadDialog, setShowLoadDialog] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Fetch sessions list
  const fetchSessions = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8000/api/session/list?limit=50');
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
      } else {
        setError('Failed to load sessions');
      }
    } catch (err) {
      console.error('Error fetching sessions:', err);
      setError('Network error loading sessions');
    } finally {
      setLoading(false);
    }
  };

  // Save current session
  const handleSave = async () => {
    if (!currentSessionId) {
      setError('No active session to save');
      return;
    }

    setSaving(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8000/api/session/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: currentSessionId })
      });

      if (response.ok) {
        const data = await response.json();
        setSuccessMessage('Session saved successfully!');
        setTimeout(() => setSuccessMessage(null), 3000);
        
        if (onSessionSaved) {
          onSessionSaved(currentSessionId);
        }
        
        // Refresh sessions list
        fetchSessions();
      } else {
        const error = await response.json();
        setError(error.detail || 'Failed to save session');
      }
    } catch (err) {
      console.error('Error saving session:', err);
      setError('Network error saving session');
    } finally {
      setSaving(false);
    }
  };

  // Load session
  const handleLoad = async (sessionId) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`http://localhost:8000/api/session/load/${sessionId}`);
      
      if (response.ok) {
        const data = await response.json();
        setSuccessMessage(`Loaded session: ${sessionId}`);
        setTimeout(() => setSuccessMessage(null), 3000);
        setShowLoadDialog(false);
        
        if (onSessionLoad) {
          onSessionLoad(sessionId);
        }
      } else {
        const error = await response.json();
        setError(error.detail || 'Failed to load session');
      }
    } catch (err) {
      console.error('Error loading session:', err);
      setError('Network error loading session');
    } finally {
      setLoading(false);
    }
  };

  // Delete session
  const handleDelete = async (sessionId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/session/${sessionId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setSuccessMessage('Session deleted successfully');
        setTimeout(() => setSuccessMessage(null), 3000);
        setDeleteConfirm(null);
        
        // Refresh sessions list
        fetchSessions();
      } else {
        const error = await response.json();
        setError(error.detail || 'Failed to delete session');
      }
    } catch (err) {
      console.error('Error deleting session:', err);
      setError('Network error deleting session');
    }
  };

  // Format date
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Format session ID for display
  const formatSessionId = (id) => {
    if (id.length > 20) {
      return id.substring(0, 20) + '...';
    }
    return id;
  };

  return (
    <div className="session-manager">
      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={!currentSessionId || saving}
        className="session-button save-button"
        title="Save current session"
      >
        <Save size={18} />
        {saving ? 'Saving...' : 'Save Session'}
      </button>

      {/* Load Button */}
      <button
        onClick={() => {
          setShowLoadDialog(true);
          fetchSessions();
        }}
        className="session-button load-button"
        title="Load saved session"
      >
        <FolderOpen size={18} />
        Load Session
      </button>

      {/* Success Message */}
      {successMessage && (
        <div className="toast success-toast">
          {successMessage}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="toast error-toast">
          {error}
          <button onClick={() => setError(null)} className="toast-close">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Load Sessions Dialog */}
      {showLoadDialog && (
        <div className="dialog-overlay" onClick={() => setShowLoadDialog(false)}>
          <div className="dialog-content" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-header">
              <h3>Load Session</h3>
              <button
                onClick={() => setShowLoadDialog(false)}
                className="dialog-close"
              >
                <X size={20} />
              </button>
            </div>

            <div className="dialog-body">
              {loading ? (
                <div className="loading-state">
                  <div className="spinner"></div>
                  <p>Loading sessions...</p>
                </div>
              ) : sessions.length === 0 ? (
                <div className="empty-sessions">
                  <FolderOpen size={48} className="empty-icon" />
                  <p>No saved sessions yet</p>
                  <p className="empty-hint">
                    Save your current session to load it later
                  </p>
                </div>
              ) : (
                <div className="sessions-list">
                  {sessions.map((session) => (
                    <div
                      key={session.id}
                      className={`session-item ${
                        session.id === currentSessionId ? 'current-session' : ''
                      }`}
                    >
                      <div className="session-info">
                        <div className="session-id">
                          {formatSessionId(session.id)}
                        </div>
                        <div className="session-meta">
                          <span className="session-date">
                            <Clock size={14} />
                            {formatDate(session.last_updated)}
                          </span>
                          <span className="session-messages">
                            <MessageSquare size={14} />
                            {session.message_count} messages
                          </span>
                        </div>
                        <div className="session-state">
                          Category: <strong>{session.state}</strong>
                        </div>
                      </div>

                      <div className="session-actions">
                        {session.id !== currentSessionId && (
                          <button
                            onClick={() => handleLoad(session.id)}
                            className="action-button load-action"
                            title="Load this session"
                          >
                            <FolderOpen size={16} />
                            Load
                          </button>
                        )}
                        
                        <button
                          onClick={() => setDeleteConfirm(session.id)}
                          className="action-button delete-action"
                          title="Delete this session"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>

                      {/* Delete Confirmation */}
                      {deleteConfirm === session.id && (
                        <div className="delete-confirm">
                          <p>Delete this session?</p>
                          <div className="confirm-actions">
                            <button
                              onClick={() => handleDelete(session.id)}
                              className="confirm-button delete-confirm-button"
                            >
                              Yes, Delete
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              className="confirm-button cancel-button"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="dialog-footer">
              <button
                onClick={() => fetchSessions()}
                className="refresh-button"
                disabled={loading}
              >
                Refresh List
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SessionManager;
