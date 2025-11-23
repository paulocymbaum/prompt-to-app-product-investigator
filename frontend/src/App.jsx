import { useState, useEffect } from 'react';
import './App.css';
import ConfigPanel from './components/ConfigPanel';
import ChatInterface from './components/ChatInterface';
import ProgressTracker from './components/ProgressTracker';
import SessionManager from './components/SessionManager';
import PromptDisplay from './components/PromptDisplay';
import { checkHealth } from './services/api';

function App() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('chat'); // 'config', 'chat', or 'prompt'
  const [sessionId, setSessionId] = useState(null);
  const [currentState, setCurrentState] = useState('start');

  useEffect(() => {
    performHealthCheck();
  }, []);

  const performHealthCheck = async () => {
    try {
      setLoading(true);
      const data = await checkHealth();
      setHealth(data);
      setError(null);
    } catch (err) {
      setError('Failed to connect to backend. Make sure the backend server is running.');
      console.error('Health check error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          <header className="text-center mb-12">
            <div className="flex justify-between items-start mb-4">
              <div className="flex-1">
                <h1 className="text-5xl font-bold text-gray-900 dark:text-white mb-4">
                  🤖 Product Investigator Chatbot
                </h1>
                <p className="text-xl text-gray-600 dark:text-gray-300">
                  LLM-powered product idea investigation and prompt generation
                </p>
              </div>
              {health && sessionId && (
                <div className="ml-4">
                  <SessionManager
                    currentSessionId={sessionId}
                    onSessionLoad={(id) => {
                      setSessionId(id);
                      // Optionally reload chat interface with new session
                      console.log('Loaded session:', id);
                    }}
                    onSessionSaved={(id) => {
                      console.log('Saved session:', id);
                    }}
                  />
                </div>
              )}
            </div>
          </header>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 mb-8">
            <h2 className="text-2xl font-semibold text-gray-800 dark:text-white mb-4">
              Backend Status
            </h2>
            
            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
              </div>
            )}

            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <p className="text-red-800 dark:text-red-200">❌ {error}</p>
                <button
                  onClick={performHealthCheck}
                  className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                >
                  Retry Connection
                </button>
              </div>
            )}

            {health && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <p className="text-green-800 dark:text-green-200 flex items-center gap-2">
                  <span className="text-2xl">✅</span>
                  <span>Backend is healthy</span>
                </p>
                <div className="mt-4 space-y-2 text-sm text-gray-700 dark:text-gray-300">
                  <p><strong>Status:</strong> {health.status}</p>
                  <p><strong>Environment:</strong> {health.environment}</p>
                  <p><strong>Version:</strong> {health.version}</p>
                </div>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-semibold text-gray-800 dark:text-white mb-3">
                🚀 Features
              </h3>
              <ul className="space-y-2 text-gray-600 dark:text-gray-300">
                <li>✓ Multi-provider LLM support</li>
                <li>✓ Conversational investigation</li>
                <li>✓ RAG-based memory</li>
                <li>✓ Prompt generation</li>
                <li>✓ Session management</li>
              </ul>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-semibold text-gray-800 dark:text-white mb-3">
                📚 Documentation
              </h3>
              <div className="space-y-2">
                <a
                  href="http://localhost:8000/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
                >
                  → API Documentation (Swagger)
                </a>
                <a
                  href="http://localhost:8000/redoc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
                >
                  → API Documentation (ReDoc)
                </a>
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          {health && (
            <div className="mt-8 mb-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-2 flex gap-2">
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`flex-1 py-3 px-6 rounded-lg font-medium transition-all ${
                    activeTab === 'chat'
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  <span className="mr-2">💬</span>
                  Chat Interface
                </button>
                <button
                  onClick={() => setActiveTab('prompt')}
                  className={`flex-1 py-3 px-6 rounded-lg font-medium transition-all ${
                    activeTab === 'prompt'
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                  disabled={!sessionId}
                >
                  <span className="mr-2">📝</span>
                  Generated Prompt
                </button>
                <button
                  onClick={() => setActiveTab('config')}
                  className={`flex-1 py-3 px-6 rounded-lg font-medium transition-all ${
                    activeTab === 'config'
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  <span className="mr-2">⚙️</span>
                  Configuration
                </button>
              </div>
            </div>
          )}

          {/* Content Area */}
          {health && (
            <div className="mt-8">
              {activeTab === 'chat' && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2">
                    <ChatInterface 
                      onSessionChange={(id) => setSessionId(id)}
                      onStateChange={(state) => setCurrentState(state)}
                    />
                  </div>
                  <div className="lg:col-span-1">
                    {sessionId && (
                      <ProgressTracker
                        sessionId={sessionId}
                        currentState={currentState}
                        onStateChange={(state) => setCurrentState(state)}
                      />
                    )}
                  </div>
                </div>
              )}
              {activeTab === 'prompt' && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg" style={{ minHeight: '600px' }}>
                  <PromptDisplay 
                    sessionId={sessionId}
                    onError={(error) => {
                      console.error('[App] Prompt display error:', error);
                      setError(error);
                    }}
                  />
                </div>
              )}
              {activeTab === 'config' && <ConfigPanel />}
            </div>
          )}

          <footer className="mt-12 text-center text-gray-500 dark:text-gray-400">
            <p className="mb-2">Sprint 1 & 2: Complete! 🎉</p>
            <p className="text-sm">Sprint 1: Config Panel & Chat Interface ✅</p>
            <p className="text-sm">Sprint 2: Progress Tracker & Session Manager ✅</p>
          </footer>
        </div>
      </div>
    </div>
  );
}

export default App;
