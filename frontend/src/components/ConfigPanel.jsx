import { useState, useEffect } from 'react';
import { saveToken, getModels, selectModel, getConfigStatus, deleteToken } from '../services/api';

/**
 * ConfigPanel Component
 * 
 * Provides UI for:
 * - API token input and validation
 * - Provider selection (Groq/OpenAI)
 * - Model selection from available models
 * - Token management (save/delete)
 * - Real-time validation feedback
 */
function ConfigPanel() {
  // Provider state
  const [provider, setProvider] = useState('groq');
  const [token, setToken] = useState('');
  const [tokenSaved, setTokenSaved] = useState(false);
  
  // Model state
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [modelSaved, setModelSaved] = useState(false);
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [testingConnection, setTestingConnection] = useState(false);
  
  // Load configuration status on mount
  useEffect(() => {
    loadConfigStatus();
  }, []);
  
  // Load models when provider changes or token is saved
  useEffect(() => {
    if (tokenSaved) {
      fetchModels();
    }
  }, [provider, tokenSaved]);
  
  /**
   * Load current configuration status from backend
   */
  const loadConfigStatus = async () => {
    try {
      const status = await getConfigStatus();
      
      // Set provider if one is active
      if (status.active_provider) {
        setProvider(status.active_provider);
      }
      
      // Check if token exists for current provider
      const providerStatus = status.providers?.[provider];
      if (providerStatus?.token_exists) {
        setTokenSaved(true);
      }
      
      // Set selected model if exists
      if (providerStatus?.selected_model) {
        setSelectedModel(providerStatus.selected_model);
        setModelSaved(true);
      }
    } catch (err) {
      console.error('Failed to load config status:', err);
    }
  };
  
  /**
   * Validate token format based on provider
   */
  const validateTokenFormat = (provider, token) => {
    if (!token || token.trim() === '') {
      return { valid: false, message: 'Token is required' };
    }
    
    if (provider === 'groq') {
      if (!token.startsWith('gsk_')) {
        return { valid: false, message: 'Groq tokens must start with "gsk_"' };
      }
    } else if (provider === 'openai') {
      if (!token.startsWith('sk-')) {
        return { valid: false, message: 'OpenAI tokens must start with "sk-"' };
      }
    }
    
    if (token.length < 20) {
      return { valid: false, message: 'Token appears too short' };
    }
    
    return { valid: true, message: 'Token format is valid' };
  };
  
  /**
   * Handle provider change
   */
  const handleProviderChange = async (newProvider) => {
    setProvider(newProvider);
    setToken('');
    setTokenSaved(false);
    setModels([]);
    setSelectedModel('');
    setModelSaved(false);
    setError(null);
    setSuccess(null);
    
    // Check if token exists for new provider
    try {
      const status = await getConfigStatus();
      const providerStatus = status.providers?.[newProvider];
      if (providerStatus?.token_exists) {
        setTokenSaved(true);
      }
      if (providerStatus?.selected_model) {
        setSelectedModel(providerStatus.selected_model);
        setModelSaved(true);
      }
    } catch (err) {
      console.error('Failed to check provider status:', err);
    }
  };
  
  /**
   * Test connection by fetching models
   */
  const handleTestConnection = async () => {
    const validation = validateTokenFormat(provider, token);
    if (!validation.valid) {
      setError(validation.message);
      return;
    }
    
    setTestingConnection(true);
    setError(null);
    setSuccess(null);
    
    try {
      // Save token first
      await saveToken(provider, token);
      
      // Try to fetch models
      const data = await getModels(provider, true); // Force refresh
      
      if (data.models && data.models.length > 0) {
        setSuccess(`✓ Connection successful! Found ${data.models.length} models.`);
        setTokenSaved(true);
        setModels(data.models);
      } else {
        setError('Connection successful but no models found.');
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to connect';
      setError(`✗ Connection failed: ${errorMsg}`);
      setTokenSaved(false);
    } finally {
      setTestingConnection(false);
    }
  };
  
  /**
   * Save token
   */
  const handleSaveToken = async () => {
    const validation = validateTokenFormat(provider, token);
    if (!validation.valid) {
      setError(validation.message);
      return;
    }
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      await saveToken(provider, token);
      setSuccess('✓ Token saved successfully!');
      setTokenSaved(true);
      // Clear token input for security
      setToken('');
      // Fetch models automatically
      fetchModels();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to save token';
      setError(`✗ ${errorMsg}`);
      setTokenSaved(false);
    } finally {
      setLoading(false);
    }
  };
  
  /**
   * Fetch available models
   */
  const fetchModels = async () => {
    setLoadingModels(true);
    setError(null);
    
    try {
      const data = await getModels(provider, false);
      setModels(data.models || []);
      
      if (data.models && data.models.length === 0) {
        setError('No models available for this provider.');
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to fetch models';
      setError(`Failed to fetch models: ${errorMsg}`);
      setModels([]);
    } finally {
      setLoadingModels(false);
    }
  };
  
  /**
   * Handle model selection
   */
  const handleSelectModel = async () => {
    if (!selectedModel) {
      setError('Please select a model');
      return;
    }
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      await selectModel(provider, selectedModel);
      setSuccess(`✓ Model "${selectedModel}" selected successfully!`);
      setModelSaved(true);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to select model';
      setError(`✗ ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };
  
  /**
   * Handle token deletion
   */
  const handleDeleteToken = async () => {
    if (!window.confirm(`Delete ${provider} token? This will also clear the selected model.`)) {
      return;
    }
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      await deleteToken(provider);
      setSuccess('✓ Token deleted successfully!');
      setTokenSaved(false);
      setToken('');
      setModels([]);
      setSelectedModel('');
      setModelSaved(false);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to delete token';
      setError(`✗ ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };
  
  /**
   * Handle cancel/reset
   */
  const handleCancel = () => {
    setToken('');
    setError(null);
    setSuccess(null);
    if (!tokenSaved) {
      setProvider('groq');
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8">
      <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
        ⚙️ LLM Configuration
      </h2>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        Configure your API tokens and select a language model
      </p>
      
      {/* Status messages */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-red-800 dark:text-red-200 text-sm">{error}</p>
        </div>
      )}
      
      {success && (
        <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <p className="text-green-800 dark:text-green-200 text-sm">{success}</p>
        </div>
      )}
      
      {/* Provider Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Select Provider
        </label>
        <div className="flex gap-4">
          <button
            onClick={() => handleProviderChange('groq')}
            disabled={loading || testingConnection}
            className={`flex-1 py-3 px-4 rounded-lg border-2 font-medium transition-all ${
              provider === 'groq'
                ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
            } ${(loading || testingConnection) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <div className="flex items-center justify-center gap-2">
              <span className="text-xl">⚡</span>
              <span>Groq</span>
              {tokenSaved && provider === 'groq' && <span className="text-green-500">✓</span>}
            </div>
          </button>
          
          <button
            onClick={() => handleProviderChange('openai')}
            disabled={loading || testingConnection}
            className={`flex-1 py-3 px-4 rounded-lg border-2 font-medium transition-all ${
              provider === 'openai'
                ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
            } ${(loading || testingConnection) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <div className="flex items-center justify-center gap-2">
              <span className="text-xl">🤖</span>
              <span>OpenAI</span>
              {tokenSaved && provider === 'openai' && <span className="text-green-500">✓</span>}
            </div>
          </button>
        </div>
      </div>
      
      {/* Token Input */}
      {!tokenSaved && (
        <div className="mb-6">
          <label htmlFor="token" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            API Token {provider === 'groq' ? '(starts with gsk_)' : '(starts with sk-)'}
          </label>
          <input
            id="token"
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder={`Enter your ${provider === 'groq' ? 'Groq' : 'OpenAI'} API token`}
            disabled={loading || testingConnection}
            className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg 
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                     focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                     disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Your token is encrypted and stored securely. Get your token from{' '}
            {provider === 'groq' ? (
              <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer" 
                 className="text-indigo-600 dark:text-indigo-400 hover:underline">
                console.groq.com
              </a>
            ) : (
              <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer"
                 className="text-indigo-600 dark:text-indigo-400 hover:underline">
                platform.openai.com
              </a>
            )}
          </p>
        </div>
      )}
      
      {/* Token actions */}
      {!tokenSaved && (
        <div className="flex gap-3 mb-6">
          <button
            onClick={handleTestConnection}
            disabled={!token || loading || testingConnection}
            className="flex-1 py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 
                     dark:disabled:bg-gray-700 text-white font-medium rounded-lg 
                     transition-colors disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {testingConnection ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>Testing...</span>
              </>
            ) : (
              <>
                <span>🔍</span>
                <span>Test Connection</span>
              </>
            )}
          </button>
          
          <button
            onClick={handleSaveToken}
            disabled={!token || loading || testingConnection}
            className="flex-1 py-3 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 
                     dark:disabled:bg-gray-700 text-white font-medium rounded-lg 
                     transition-colors disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>Saving...</span>
              </>
            ) : (
              <>
                <span>💾</span>
                <span>Save Token</span>
              </>
            )}
          </button>
          
          <button
            onClick={handleCancel}
            disabled={loading || testingConnection}
            className="py-3 px-6 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 
                     text-gray-700 dark:text-gray-300 font-medium rounded-lg 
                     transition-colors disabled:cursor-not-allowed"
          >
            Cancel
          </button>
        </div>
      )}
      
      {/* Saved token indicator with delete option */}
      {tokenSaved && (
        <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-green-600 dark:text-green-400">✓</span>
              <span className="text-green-800 dark:text-green-200 font-medium">
                {provider === 'groq' ? 'Groq' : 'OpenAI'} token is configured
              </span>
            </div>
            <button
              onClick={handleDeleteToken}
              disabled={loading}
              className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 
                       text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Delete Token
            </button>
          </div>
        </div>
      )}
      
      {/* Model Selection */}
      {tokenSaved && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="model" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Select Model
            </label>
            {models.length > 0 && (
              <button
                onClick={() => fetchModels()}
                disabled={loadingModels}
                className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 
                         dark:hover:text-indigo-300 disabled:opacity-50"
              >
                Refresh
              </button>
            )}
          </div>
          
          {loadingModels ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : models.length > 0 ? (
            <>
              <select
                id="model"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                disabled={loading}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg 
                         bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="">-- Select a model --</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.id} {model.context_window ? `(${model.context_window} tokens)` : ''}
                  </option>
                ))}
              </select>
              
              {selectedModel && (
                <div className="mt-3">
                  <button
                    onClick={handleSelectModel}
                    disabled={!selectedModel || loading}
                    className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 
                             dark:disabled:bg-gray-700 text-white font-medium rounded-lg 
                             transition-colors disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                        <span>Saving...</span>
                      </>
                    ) : modelSaved ? (
                      <>
                        <span>✓</span>
                        <span>Model Saved</span>
                      </>
                    ) : (
                      <>
                        <span>💾</span>
                        <span>Save Model Selection</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <p>No models available. Try refreshing your token.</p>
            </div>
          )}
        </div>
      )}
      
      {/* Help text */}
      {tokenSaved && modelSaved && (
        <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <p className="text-blue-800 dark:text-blue-200 text-sm flex items-center gap-2">
            <span>🎉</span>
            <span>Configuration complete! You're ready to start an investigation.</span>
          </p>
        </div>
      )}
    </div>
  );
}

export default ConfigPanel;
