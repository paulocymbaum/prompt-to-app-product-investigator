import { useEffect, useState } from 'react';
import { CheckCircle, Circle, Clock } from 'lucide-react';
import '../styles/ProgressTracker.css';

/**
 * ProgressTracker Component
 * 
 * Displays the investigation progress with:
 * - Progress bar showing overall completion
 * - Category list with completion status
 * - Question counter
 * - Real-time updates
 */
export function ProgressTracker({ sessionId, currentState, onStateChange }) {
  const [progress, setProgress] = useState({
    functionality: 0,
    users: 0,
    demographics: 0,
    design: 0,
    market: 0,
    technical: 0
  });
  const [stats, setStats] = useState({
    totalQuestions: 0,
    totalMessages: 0,
    isComplete: false
  });

  const categories = [
    { name: 'Functionality', state: 'functionality', icon: '🎯' },
    { name: 'Target Users', state: 'users', icon: '👥' },
    { name: 'Demographics', state: 'demographics', icon: '📊' },
    { name: 'Design', state: 'design', icon: '🎨' },
    { name: 'Market', state: 'market', icon: '🏪' },
    { name: 'Technical', state: 'technical', icon: '⚙️' }
  ];

  // Fetch session status
  const fetchSessionStatus = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`http://localhost:8000/api/chat/status/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        setProgress(data.progress || {});
        setStats({
          totalQuestions: data.total_questions || 0,
          totalMessages: data.total_messages || 0,
          isComplete: data.is_complete || false
        });
        
        // Notify parent of state changes
        if (onStateChange && data.state !== currentState) {
          onStateChange(data.state);
        }
      }
    } catch (error) {
      console.error('Error fetching session status:', error);
    }
  };

  // Poll for updates every 3 seconds
  useEffect(() => {
    if (!sessionId) return;

    fetchSessionStatus(); // Initial fetch
    const interval = setInterval(fetchSessionStatus, 3000);

    return () => clearInterval(interval);
  }, [sessionId]);

  // Calculate overall progress
  const completedCategories = Object.entries(progress).filter(
    ([_, value]) => value > 0.5 // Consider >50% as completed
  );
  const progressPercent = (completedCategories.length / categories.length) * 100;

  // Get category completion status
  const getCategoryStatus = (categoryState) => {
    const value = progress[categoryState] || 0;
    if (value > 0.5) return 'completed';
    if (value > 0) return 'in-progress';
    return 'pending';
  };

  if (!sessionId) {
    return (
      <div className="progress-tracker empty">
        <div className="empty-state">
          <Clock size={48} className="text-gray-300" />
          <p className="text-gray-500 mt-4">Start an investigation to see progress</p>
        </div>
      </div>
    );
  }

  return (
    <div className="progress-tracker">
      <div className="progress-header">
        <h3 className="progress-title">Investigation Progress</h3>
        <div className="progress-percentage">
          {Math.round(progressPercent)}%
        </div>
      </div>

      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div 
          className="progress-bar-fill"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Stats Summary */}
      <div className="progress-stats">
        <div className="stat-item">
          <span className="stat-label">Categories:</span>
          <span className="stat-value">
            {completedCategories.length} / {categories.length}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Questions:</span>
          <span className="stat-value">{stats.totalQuestions}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Messages:</span>
          <span className="stat-value">{stats.totalMessages}</span>
        </div>
      </div>

      {/* Categories List */}
      <div className="categories-list">
        {categories.map((category) => {
          const status = getCategoryStatus(category.state);
          const isCurrent = currentState === category.state;
          const progressValue = progress[category.state] || 0;

          return (
            <div
              key={category.state}
              className={`category-item ${status} ${isCurrent ? 'current' : ''}`}
            >
              <div className="category-icon">
                {status === 'completed' ? (
                  <CheckCircle size={20} className="icon-completed" />
                ) : status === 'in-progress' ? (
                  <Clock size={20} className="icon-in-progress" />
                ) : (
                  <Circle size={20} className="icon-pending" />
                )}
              </div>
              
              <div className="category-content">
                <div className="category-header">
                  <span className="category-emoji">{category.icon}</span>
                  <span className="category-name">{category.name}</span>
                  {isCurrent && (
                    <span className="current-badge">Current</span>
                  )}
                </div>
                
                {status !== 'pending' && (
                  <div className="category-progress-mini">
                    <div 
                      className="category-progress-fill"
                      style={{ width: `${progressValue * 100}%` }}
                    />
                  </div>
                )}
              </div>
              
              {status === 'completed' && (
                <span className="completion-check">✓</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Completion Status */}
      {stats.isComplete && (
        <div className="completion-banner">
          <CheckCircle size={24} className="text-green-500" />
          <span className="completion-text">Investigation Complete!</span>
        </div>
      )}
    </div>
  );
}

export default ProgressTracker;
