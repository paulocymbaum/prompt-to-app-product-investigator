import { useState, useEffect, useRef } from 'react';
// import ReactMarkdown from 'react-markdown';
import { startInvestigation, sendMessage } from '../services/api';

/**
 * ChatInterface Component
 * 
 * Main chat interface for conducting product investigations.
 * Features:
 * - Auto-scrolling message list
 * - User/system message differentiation
 * - Markdown rendering for system messages
 * - Loading states and typing indicators
 * - Responsive design
 * - Timestamp display
 * - Investigation completion detection
 */
function ChatInterface({ onSessionChange, onStateChange }) {
  // Session state
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [investigationComplete, setInvestigationComplete] = useState(false);
  
  // Input state
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Initial loading
  const [initializing, setInitializing] = useState(true);
  
  // Refs
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  
  /**
   * Scroll to bottom of messages
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  /**
   * Start a new investigation
   */
  const handleStartInvestigation = async () => {
    setInitializing(true);
    setError(null);
    
    try {
      console.log('[ChatInterface] Starting investigation...');
      const response = await startInvestigation();
      console.log('[ChatInterface] Investigation started:', response);
      
      if (!response || !response.session_id) {
        throw new Error('Invalid response from server: missing session_id');
      }
      
      if (!response.question || !response.question.text) {
        throw new Error('Invalid response from server: missing question');
      }
      
      setSessionId(response.session_id);
      if (onSessionChange) {
        onSessionChange(response.session_id);
      }
      if (onStateChange && response.question.category) {
        onStateChange(response.question.category);
      }
      
      setMessages([{
        type: 'system',
        content: response.question.text,
        timestamp: new Date().toISOString(),
        questionId: response.question.id,
        category: response.question.category
      }]);
      
      setInvestigationComplete(false);
    } catch (err) {
      console.error('Failed to start investigation:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to start investigation';
      setError(errorMsg);
      
      // Add error message to chat
      setMessages([{
        type: 'error',
        content: `⚠️ **Error starting investigation:**\n\n${errorMsg}\n\nPlease check:\n1. Backend server is running\n2. You have configured an API token\n3. You have selected a model`,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setInitializing(false);
    }
  };
  
  /**
   * Send user message
   */
  const handleSendMessage = async () => {
    if (!input.trim() || loading || !sessionId) return;
    
    // Add user message to UI
    const userMessage = {
      type: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);
    
    try {
      const response = await sendMessage(sessionId, userMessage.content);
      
      // Check if investigation is complete
      if (response.complete) {
        setInvestigationComplete(true);
        
        // Add completion message
        const completionMessage = {
          type: 'system',
          content: response.message || '🎉 **Investigation Complete!**\n\nThank you for providing all the information. Your responses have been recorded.',
          timestamp: new Date().toISOString(),
          isCompletion: true
        };
        
        setMessages(prev => [...prev, completionMessage]);
      } else if (response.question) {
        // Add next question
        const systemMessage = {
          type: 'system',
          content: response.question.text,
          timestamp: new Date().toISOString(),
          questionId: response.question.id,
          category: response.question.category
        };
        
        // Notify parent of state change
        if (onStateChange && response.question.category) {
          onStateChange(response.question.category);
        }
        
        setMessages(prev => [...prev, systemMessage]);
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to send message';
      setError(errorMsg);
      
      // Add error message to chat
      const errorMessage = {
        type: 'error',
        content: `⚠️ **Error:** ${errorMsg}`,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      // Focus input after sending
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };
  
  /**
   * Handle Enter key press
   */
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  
  /**
   * Reset investigation
   */
  const handleReset = () => {
    setMessages([]);
    setSessionId(null);
    setInput('');
    setInvestigationComplete(false);
    setError(null);
    handleStartInvestigation();
  };
  
  /**
   * Format timestamp for display
   */
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };
  
  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  // If initializing state is still true on first render, show button to start
  if (initializing && messages.length === 0) {
    return (
      <div className="w-full max-w-4xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 text-center">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-4">💬 Product Investigation</h2>
        <p className="text-gray-600 dark:text-gray-300 mb-6">Click the button below to start a new investigation</p>
        <button
          onClick={handleStartInvestigation}
          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors"
        >
          Start Investigation
        </button>
      </div>
    );
  }
  
  return (
    <div className="w-full max-w-4xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-xl overflow-hidden flex flex-col" style={{ height: '600px' }}>
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            💬 Product Investigation
          </h2>
          <p className="text-indigo-100 text-sm mt-1">
            {sessionId ? `Session: ${sessionId.substring(0, 8)}...` : 'Starting...'}
          </p>
        </div>
        {sessionId && (
          <button
            onClick={handleReset}
            disabled={loading}
            className="px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-lg 
                     transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                     flex items-center gap-2 text-sm font-medium"
          >
            <span>🔄</span>
            <span>New Investigation</span>
          </button>
        )}
      </div>
      
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50 dark:bg-gray-900">
        {/* Initializing state */}
        {initializing && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
              <p className="text-gray-600 dark:text-gray-400">Starting investigation...</p>
            </div>
          </div>
        )}
        
        {/* Messages */}
        {!initializing && messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-3 ${
                message.type === 'user'
                  ? 'bg-indigo-600 text-white'
                  : message.type === 'error'
                  ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200'
                  : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-md border border-gray-200 dark:border-gray-700'
              }`}
            >
              {/* Message content */}
              <div className="message-content">
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
              
              {/* Metadata */}
              <div className={`flex items-center gap-2 mt-2 text-xs ${
                message.type === 'user' 
                  ? 'text-indigo-100' 
                  : message.type === 'error'
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-gray-500 dark:text-gray-400'
              }`}>
                <span>{formatTime(message.timestamp)}</span>
                {message.category && (
                  <>
                    <span>•</span>
                    <span className="capitalize">{message.category}</span>
                  </>
                )}
                {message.isCompletion && (
                  <>
                    <span>•</span>
                    <span>✅ Complete</span>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
        
        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-gray-800 rounded-lg px-4 py-3 shadow-md border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-sm">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        
        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Error display */}
      {error && !loading && (
        <div className="px-6 py-3 bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800">
          <p className="text-red-800 dark:text-red-200 text-sm">
            ⚠️ {error}
          </p>
        </div>
      )}
      
      {/* Investigation complete message */}
      {investigationComplete && (
        <div className="px-6 py-3 bg-green-50 dark:bg-green-900/20 border-t border-green-200 dark:border-green-800">
          <p className="text-green-800 dark:text-green-200 text-sm font-medium">
            🎉 Investigation complete! Start a new investigation to explore another idea.
          </p>
        </div>
      )}
      
      {/* Input Area */}
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
        <div className="flex gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              investigationComplete 
                ? "Investigation complete. Click 'New Investigation' to start over." 
                : "Type your answer... (Shift+Enter for new line)"
            }
            disabled={loading || initializing || investigationComplete}
            rows={2}
            className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg 
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                     focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                     disabled:opacity-50 disabled:cursor-not-allowed
                     resize-none"
          />
          <button
            onClick={handleSendMessage}
            disabled={!input.trim() || loading || initializing || investigationComplete}
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 
                     dark:disabled:bg-gray-700 text-white font-medium rounded-lg 
                     transition-colors disabled:cursor-not-allowed
                     flex items-center gap-2 self-end"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>Sending...</span>
              </>
            ) : (
              <>
                <span>📤</span>
                <span>Send</span>
              </>
            )}
          </button>
        </div>
        
        {/* Helper text */}
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          Press <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded border border-gray-300 dark:border-gray-600">Enter</kbd> to send, 
          <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded border border-gray-300 dark:border-gray-600 ml-1">Shift+Enter</kbd> for new line
        </p>
      </div>
    </div>
  );
}

export default ChatInterface;
