import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`[API] Response from ${response.config.url}:`, response.status);
    return response;
  },
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error(`[API] Error ${error.response.status}:`, error.response.data);
    } else if (error.request) {
      // Request made but no response
      console.error('[API] No response received:', error.request);
    } else {
      // Error in request setup
      console.error('[API] Request setup error:', error.message);
    }
    return Promise.reject(error);
  }
);

// ============================================
// Configuration API Methods
// ============================================

/**
 * Save API token for a provider
 * @param {string} provider - 'groq' or 'openai'
 * @param {string} token - API token
 * @returns {Promise} Response with status
 */
export const saveToken = async (provider, token) => {
  const response = await api.post('/api/config/token', { provider, token });
  return response.data;
};

/**
 * Get available models for a provider
 * @param {string} provider - 'groq' or 'openai'
 * @param {boolean} forceRefresh - Force cache refresh
 * @returns {Promise} Response with models array
 */
export const getModels = async (provider, forceRefresh = false) => {
  const response = await api.get('/api/config/models', {
    params: { provider, force_refresh: forceRefresh }
  });
  return response.data;
};

/**
 * Select a model for use
 * @param {string} provider - 'groq' or 'openai'
 * @param {string} modelId - Model ID to select
 * @returns {Promise} Response with status
 */
export const selectModel = async (provider, modelId) => {
  const response = await api.post('/api/config/model/select', {
    provider,
    model_id: modelId
  });
  return response.data;
};

/**
 * Get current configuration status
 * @returns {Promise} Response with config status
 */
export const getConfigStatus = async () => {
  const response = await api.get('/api/config/status');
  return response.data;
};

/**
 * Delete token for a provider
 * @param {string} provider - 'groq' or 'openai'
 * @returns {Promise} Response with status
 */
export const deleteToken = async (provider) => {
  const response = await api.delete(`/api/config/token/${provider}`);
  return response.data;
};

// ============================================
// Chat API Methods
// ============================================

/**
 * Start a new investigation session
 * @param {string} provider - Optional provider override
 * @param {string} modelId - Optional model ID override
 * @returns {Promise} Response with session_id and initial question
 */
export const startInvestigation = async (provider = null, modelId = null) => {
  const data = {};
  if (provider) data.provider = provider;
  if (modelId) data.model_id = modelId;
  
  const response = await api.post('/api/chat/start', data);
  return response.data;
};

/**
 * Send a message in a chat session
 * @param {string} sessionId - Session ID
 * @param {string} message - User message
 * @returns {Promise} Response with next question or completion
 */
export const sendMessage = async (sessionId, message) => {
  const response = await api.post('/api/chat/message', {
    session_id: sessionId,
    message
  });
  return response.data;
};

/**
 * Get conversation history
 * @param {string} sessionId - Session ID
 * @returns {Promise} Response with message history
 */
export const getHistory = async (sessionId) => {
  const response = await api.get(`/api/chat/history/${sessionId}`);
  return response.data;
};

/**
 * Get session status
 * @param {string} sessionId - Session ID
 * @returns {Promise} Response with session status
 */
export const getSessionStatus = async (sessionId) => {
  const response = await api.get(`/api/chat/status/${sessionId}`);
  return response.data;
};

/**
 * Check backend health
 * @returns {Promise} Health status
 */
export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
