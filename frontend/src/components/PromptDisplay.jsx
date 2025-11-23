import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import { 
  Copy, 
  Download, 
  RefreshCw, 
  Check, 
  FileText, 
  FileCode,
  Loader2,
  AlertCircle,
  X
} from 'lucide-react';
import './PromptDisplay.css';

/**
 * PromptDisplay Component
 * 
 * Displays generated product development prompts with interactive features.
 * 
 * Features:
 * - Markdown rendering with syntax highlighting
 * - Copy to clipboard functionality
 * - Download in txt/md formats
 * - Regenerate with modifications
 * - Loading states and error handling
 * - Responsive design
 * - Token count display
 * - Version tracking
 * 
 * @param {Object} props
 * @param {string} props.sessionId - Current session ID
 * @param {Function} props.onError - Error callback (optional)
 */
function PromptDisplay({ sessionId, onError }) {
  // Prompt data state
  const [prompt, setPrompt] = useState('');
  const [promptMetadata, setPromptMetadata] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // UI state
  const [copied, setCopied] = useState(false);
  const [showRegenerateDialog, setShowRegenerateDialog] = useState(false);
  const [additionalRequirements, setAdditionalRequirements] = useState('');
  const [downloading, setDownloading] = useState(false);

  /**
   * Fetch prompt on session change
   */
  useEffect(() => {
    if (sessionId) {
      fetchPrompt();
    }
  }, [sessionId]);

  /**
   * Fetch prompt from API
   */
  const fetchPrompt = async (forceRegenerate = false) => {
    if (!sessionId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      console.log(`[PromptDisplay] Fetching prompt for session ${sessionId}`);
      
      const url = `/api/prompt/generate/${sessionId}${forceRegenerate ? '?force_regenerate=true' : ''}`;
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}${url}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch prompt: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('[PromptDisplay] Prompt fetched successfully');
      
      setPrompt(data.prompt);
      setPromptMetadata({
        cached: data.cached,
        tokenCount: data.token_count,
        version: data.version || 1,
        sessionId: data.session_id
      });
      
    } catch (err) {
      console.error('[PromptDisplay] Error fetching prompt:', err);
      const errorMessage = err.message || 'Failed to load prompt';
      setError(errorMessage);
      if (onError) onError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Copy prompt to clipboard
   */
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(prompt);
      console.log('[PromptDisplay] Prompt copied to clipboard');
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('[PromptDisplay] Failed to copy:', err);
      setError('Failed to copy to clipboard');
    }
  };

  /**
   * Download prompt in specified format
   */
  const handleDownload = async (format) => {
    if (!sessionId) return;
    
    setDownloading(true);
    setError(null);
    
    try {
      console.log(`[PromptDisplay] Downloading prompt as ${format}`);
      
      const url = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/prompt/download/${sessionId}?format=${format}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to download: ${response.status}`);
      }
      
      // Get the blob from response
      const blob = await response.blob();
      
      // Create download link
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `product_prompt_${sessionId}.${format}`;
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
      
      console.log('[PromptDisplay] Download completed');
      
    } catch (err) {
      console.error('[PromptDisplay] Download error:', err);
      setError('Failed to download prompt');
    } finally {
      setDownloading(false);
    }
  };

  /**
   * Regenerate prompt with modifications
   */
  const handleRegenerate = async () => {
    if (!sessionId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      console.log('[PromptDisplay] Regenerating prompt with modifications');
      
      const url = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/prompt/regenerate/${sessionId}`;
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          modifications: additionalRequirements || undefined
        })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to regenerate: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('[PromptDisplay] Prompt regenerated successfully');
      
      setPrompt(data.prompt);
      setPromptMetadata({
        cached: false,
        tokenCount: data.token_count,
        version: data.version,
        sessionId: data.session_id
      });
      
      setShowRegenerateDialog(false);
      setAdditionalRequirements('');
      
    } catch (err) {
      console.error('[PromptDisplay] Regenerate error:', err);
      setError('Failed to regenerate prompt');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Render loading state
   */
  if (loading && !prompt) {
    return (
      <div className="prompt-display-container">
        <div className="prompt-loading">
          <Loader2 className="animate-spin" size={48} />
          <p className="text-lg mt-4">Generating comprehensive prompt...</p>
          <p className="text-sm text-gray-500 mt-2">
            Analyzing conversation and applying SOLID principles
          </p>
        </div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (error && !prompt) {
    return (
      <div className="prompt-display-container">
        <div className="prompt-error">
          <AlertCircle size={48} className="text-red-500" />
          <p className="text-lg mt-4 font-semibold">Error Loading Prompt</p>
          <p className="text-sm text-gray-600 mt-2">{error}</p>
          <button 
            onClick={() => fetchPrompt()}
            className="btn-primary mt-4"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  /**
   * Render empty state
   */
  if (!prompt) {
    return (
      <div className="prompt-display-container">
        <div className="prompt-empty">
          <FileCode size={48} className="text-gray-400" />
          <p className="text-lg mt-4 text-gray-600">No prompt generated yet</p>
          <p className="text-sm text-gray-500 mt-2">
            Complete the investigation to generate a development prompt
          </p>
        </div>
      </div>
    );
  }

  /**
   * Main render
   */
  return (
    <div className="prompt-display-container">
      {/* Header */}
      <div className="prompt-header">
        <div className="prompt-title-section">
          <h2 className="prompt-title">Generated Development Prompt</h2>
          {promptMetadata && (
            <div className="prompt-metadata">
              <span className="metadata-badge">
                Version {promptMetadata.version}
              </span>
              <span className="metadata-badge">
                ~{promptMetadata.tokenCount} tokens
              </span>
              {promptMetadata.cached && (
                <span className="metadata-badge cached">
                  Cached
                </span>
              )}
            </div>
          )}
        </div>
        
        <div className="prompt-actions">
          <button
            onClick={handleCopy}
            className="btn-action"
            title="Copy to clipboard"
            disabled={loading}
          >
            {copied ? (
              <>
                <Check size={16} />
                Copied!
              </>
            ) : (
              <>
                <Copy size={16} />
                Copy
              </>
            )}
          </button>
          
          <button
            onClick={() => handleDownload('md')}
            className="btn-action"
            title="Download as Markdown"
            disabled={downloading || loading}
          >
            <FileCode size={16} />
            {downloading ? 'Downloading...' : 'MD'}
          </button>
          
          <button
            onClick={() => handleDownload('txt')}
            className="btn-action"
            title="Download as Text"
            disabled={downloading || loading}
          >
            <FileText size={16} />
            {downloading ? 'Downloading...' : 'TXT'}
          </button>
          
          <button
            onClick={() => setShowRegenerateDialog(true)}
            className="btn-action regenerate"
            title="Regenerate with modifications"
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Regenerate
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <AlertCircle size={16} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* Prompt Content */}
      <div className="prompt-content">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ node, inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '');
              return !inline && match ? (
                <SyntaxHighlighter
                  style={vscDarkPlus}
                  language={match[1]}
                  PreTag="div"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              ) : (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            },
            h1: ({ node, ...props }) => (
              <h1 className="prompt-h1" {...props} />
            ),
            h2: ({ node, ...props }) => (
              <h2 className="prompt-h2" {...props} />
            ),
            h3: ({ node, ...props }) => (
              <h3 className="prompt-h3" {...props} />
            ),
            ul: ({ node, ...props }) => (
              <ul className="prompt-ul" {...props} />
            ),
            ol: ({ node, ...props }) => (
              <ol className="prompt-ol" {...props} />
            ),
            blockquote: ({ node, ...props }) => (
              <blockquote className="prompt-blockquote" {...props} />
            ),
            table: ({ node, ...props }) => (
              <div className="table-wrapper">
                <table className="prompt-table" {...props} />
              </div>
            )
          }}
        >
          {prompt}
        </ReactMarkdown>
      </div>

      {/* Regenerate Dialog */}
      {showRegenerateDialog && (
        <div className="modal-overlay" onClick={() => setShowRegenerateDialog(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Regenerate Prompt</h3>
              <button
                onClick={() => setShowRegenerateDialog(false)}
                className="modal-close"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="modal-body">
              <p className="modal-description">
                Add any additional requirements or focus areas to refine the generated prompt:
              </p>
              
              <textarea
                value={additionalRequirements}
                onChange={(e) => setAdditionalRequirements(e.target.value)}
                placeholder="E.g., 'Focus more on security requirements' or 'Add mobile-first considerations' or 'Emphasize microservices architecture'"
                className="modal-textarea"
                rows={6}
                disabled={loading}
              />
              
              <div className="modal-hint">
                <AlertCircle size={14} />
                <span>The prompt will be regenerated with your modifications applied</span>
              </div>
            </div>
            
            <div className="modal-footer">
              <button
                onClick={() => setShowRegenerateDialog(false)}
                className="btn-secondary"
                disabled={loading}
              >
                Cancel
              </button>
              <button
                onClick={handleRegenerate}
                className="btn-primary"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin" size={16} />
                    Regenerating...
                  </>
                ) : (
                  <>
                    <RefreshCw size={16} />
                    Regenerate Prompt
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PromptDisplay;
