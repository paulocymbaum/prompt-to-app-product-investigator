# LAST MILE BACKLOG
## Critical Pre-Launch Tasks for Real LLM API Integration

**Priority:** P0 - BLOCKER  
**Date Created:** November 16, 2025  
**Status:** Pre-Production Checklist  
**Estimated Total:** 8-12 hours

---

## 🎯 PRIMARY OBJECTIVE

**Enable real LLM API integration with proper token validation to prevent API calls before user configuration is complete.**

---

## 🚨 CRITICAL BLOCKERS (Must Complete Before Launch)

### BLOCKER-1: Enforce Token Validation Before Any LLM Call
**Priority:** P0 - CRITICAL BLOCKER  
**Estimated Time:** 2-3 hours  
**Current Status:** ❌ NOT IMPLEMENTED

#### Problem Statement
Currently, the system may attempt to make LLM API calls even when no valid API token is configured. This will result in:
- Failed API calls with authentication errors
- Poor user experience with cryptic error messages
- Potential rate limiting or IP blocking from providers
- Wasted computation and resources

#### Required Implementation

**1. Create Token Validation Middleware** (30 min)
```python
# File: backend/middleware/token_validator.py

from fastapi import Request, HTTPException, status
from services.config_service import ConfigService
import structlog

logger = structlog.get_logger()

async def validate_token_middleware(request: Request, call_next):
    """
    Middleware to validate API token exists before processing requests
    that require LLM API calls.
    """
    # Routes that require LLM access
    llm_required_routes = [
        "/api/chat/start",
        "/api/chat/message",
        "/api/prompt/generate",
        "/api/graph/generate"
    ]
    
    # Check if this route requires LLM
    path = request.url.path
    requires_llm = any(path.startswith(route) for route in llm_required_routes)
    
    if requires_llm:
        config = ConfigService()
        active_provider = config.get_active_provider()
        
        # No provider configured
        if not active_provider:
            logger.warning("llm_call_blocked_no_provider", path=path)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "NoProviderConfigured",
                    "message": "Please configure an API token before starting a conversation.",
                    "user_message": "You need to add your Groq or OpenAI API token first. Go to Settings → API Configuration.",
                    "action_required": "configure_token"
                }
            )
        
        # Provider configured but no token
        token = config.get_token(active_provider)
        if not token:
            logger.warning("llm_call_blocked_no_token", path=path, provider=active_provider)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "NoTokenConfigured",
                    "message": f"No API token found for {active_provider}.",
                    "user_message": f"Please add your {active_provider.title()} API token in Settings.",
                    "action_required": "configure_token",
                    "provider": active_provider
                }
            )
        
        # Token exists but no model selected
        selected_model = config.get_selected_model(active_provider)
        if not selected_model:
            logger.warning("llm_call_blocked_no_model", path=path, provider=active_provider)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "NoModelSelected",
                    "message": f"No model selected for {active_provider}.",
                    "user_message": f"Please select a model from your {active_provider.title()} account.",
                    "action_required": "select_model",
                    "provider": active_provider
                }
            )
        
        logger.info("token_validation_passed", path=path, provider=active_provider, model=selected_model)
    
    response = await call_next(request)
    return response
```

**2. Add Middleware to FastAPI App** (15 min)
```python
# File: backend/app.py

from middleware.token_validator import validate_token_middleware

# Add before routes
app.middleware("http")(validate_token_middleware)
```

**3. Add Frontend Token Check** (45 min)
```javascript
// File: frontend/src/hooks/useTokenValidation.js

import { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';

export function useTokenValidation() {
  const [hasToken, setHasToken] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const [configStatus, setConfigStatus] = useState(null);

  useEffect(() => {
    checkTokenStatus();
  }, []);

  const checkTokenStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/config/status');
      const data = await response.json();
      
      setConfigStatus(data);
      
      const hasValidConfig = (
        data.active_provider &&
        (data.has_groq_token || data.has_openai_token) &&
        data.selected_model
      );
      
      setHasToken(hasValidConfig);
      setIsChecking(false);
      
      if (!hasValidConfig && window.location.pathname !== '/settings') {
        toast.error(
          'Please configure your API token and select a model in Settings',
          { duration: 5000 }
        );
      }
    } catch (error) {
      console.error('Failed to check token status:', error);
      setIsChecking(false);
    }
  };

  return { hasToken, isChecking, configStatus, recheckToken: checkTokenStatus };
}
```

**4. Block Chat Start Button** (30 min)
```javascript
// File: frontend/src/components/ChatInterface.jsx

import { useTokenValidation } from '../hooks/useTokenValidation';

function ChatInterface() {
  const { hasToken, isChecking, recheckToken } = useTokenValidation();
  
  const handleStartConversation = async () => {
    if (!hasToken) {
      toast.error('Please configure your API token first');
      navigate('/settings');
      return;
    }
    
    // Existing start logic...
  };
  
  return (
    <div>
      {!hasToken && !isChecking && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
          <p className="text-yellow-800">
            ⚠️ API token not configured. Please add your token in Settings before starting.
          </p>
          <button 
            onClick={() => navigate('/settings')}
            className="mt-2 text-yellow-600 underline"
          >
            Go to Settings →
          </button>
        </div>
      )}
      
      <button
        onClick={handleStartConversation}
        disabled={!hasToken || isChecking}
        className={`btn ${!hasToken ? 'btn-disabled' : 'btn-primary'}`}
      >
        {isChecking ? 'Checking configuration...' : 'Start Investigation'}
      </button>
    </div>
  );
}
```

#### Acceptance Criteria
- [ ] Backend middleware blocks all LLM-dependent routes without valid token
- [ ] Frontend checks token status on mount
- [ ] Chat start button is disabled until token is configured
- [ ] Clear error messages guide user to Settings
- [ ] No API calls made without valid token + selected model
- [ ] Status check endpoint returns complete configuration state

#### Test Cases Required
```python
# File: backend/tests/test_token_validation_middleware.py

async def test_chat_start_blocked_without_token():
    """Should return 401 when starting chat without token"""
    # Clear all tokens
    response = client.post("/api/chat/start")
    assert response.status_code == 401
    assert "configure_token" in response.json()["detail"]["action_required"]

async def test_chat_start_blocked_without_model():
    """Should return 400 when token exists but no model selected"""
    # Save token but don't select model
    response = client.post("/api/chat/start")
    assert response.status_code == 400
    assert "select_model" in response.json()["detail"]["action_required"]

async def test_chat_start_allowed_with_complete_config():
    """Should allow chat start with valid token and model"""
    # Configure token and model
    response = client.post("/api/chat/start")
    assert response.status_code == 201
```

---

### BLOCKER-2: Real LLM API Integration Testing
**Priority:** P0 - CRITICAL BLOCKER  
**Estimated Time:** 3-4 hours  
**Current Status:** ❌ NOT TESTED WITH REAL APIs

#### Problem Statement
All current tests use mocks. Need to verify:
- Real Groq API integration works
- Real OpenAI API integration works
- Token validation works with real providers
- Model selection fetches real models
- Error handling works with real API errors

#### Required Implementation

**1. Create Integration Test Suite** (2 hours)
```python
# File: backend/tests/integration/test_real_llm_integration.py

import pytest
import os
from services.config_service import ConfigService
from services.model_checker import ModelChecker
from services.llm_service import LLMService

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="Requires real GROQ_API_KEY"
)
class TestGroqIntegration:
    """Integration tests with real Groq API"""
    
    def test_groq_token_validation(self):
        """Test real Groq token validation"""
        config = ConfigService()
        token = os.getenv("GROQ_API_KEY")
        
        # Should validate format
        is_valid = config.validate_token_format("groq", token)
        assert is_valid
        
    async def test_groq_model_fetching(self):
        """Test fetching real models from Groq"""
        config = ConfigService()
        checker = ModelChecker(config)
        
        models = await checker.fetch_models("groq")
        
        assert len(models) > 0
        assert any("llama" in m["id"].lower() for m in models)
        
    async def test_groq_llm_generation(self):
        """Test real LLM generation with Groq"""
        config = ConfigService()
        config.save_token("groq", os.getenv("GROQ_API_KEY"))
        config.save_selected_model("groq", "llama2-70b-4096")
        config.switch_provider("groq")
        
        llm_service = LLMService(config)
        
        response = await llm_service.generate(
            prompt="What is 2+2? Answer in one word.",
            max_tokens=10
        )
        
        assert response
        assert "4" in response.lower() or "four" in response.lower()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires real OPENAI_API_KEY"
)
class TestOpenAIIntegration:
    """Integration tests with real OpenAI API"""
    
    def test_openai_token_validation(self):
        """Test real OpenAI token validation"""
        config = ConfigService()
        token = os.getenv("OPENAI_API_KEY")
        
        is_valid = config.validate_token_format("openai", token)
        assert is_valid
        
    async def test_openai_model_fetching(self):
        """Test fetching real models from OpenAI"""
        config = ConfigService()
        checker = ModelChecker(config)
        
        models = await checker.fetch_models("openai")
        
        assert len(models) > 0
        assert any("gpt" in m["id"].lower() for m in models)
        
    async def test_openai_llm_generation(self):
        """Test real LLM generation with OpenAI"""
        config = ConfigService()
        config.save_token("openai", os.getenv("OPENAI_API_KEY"))
        config.save_selected_model("openai", "gpt-3.5-turbo")
        config.switch_provider("openai")
        
        llm_service = LLMService(config)
        
        response = await llm_service.generate(
            prompt="What is 2+2? Answer in one word.",
            max_tokens=10
        )
        
        assert response
        assert "4" in response.lower() or "four" in response.lower()


@pytest.mark.integration
class TestEndToEndInvestigation:
    """End-to-end integration test with real LLM"""
    
    async def test_complete_investigation_flow(self):
        """Test complete investigation flow with real API"""
        # Requires GROQ_API_KEY or OPENAI_API_KEY
        
        # 1. Configure token
        response = client.post("/api/config/token", json={
            "provider": "groq",
            "token": os.getenv("GROQ_API_KEY")
        })
        assert response.status_code == 200
        
        # 2. Fetch and select model
        response = client.get("/api/config/models?provider=groq")
        assert response.status_code == 200
        models = response.json()["models"]
        
        response = client.post("/api/config/model/select", json={
            "provider": "groq",
            "model_id": models[0]["id"]
        })
        assert response.status_code == 200
        
        # 3. Start investigation
        response = client.post("/api/chat/start")
        assert response.status_code == 201
        session_id = response.json()["session_id"]
        
        # 4. Answer first question
        response = client.post("/api/chat/message", json={
            "session_id": session_id,
            "message": "A task management app for remote teams"
        })
        assert response.status_code == 200
        assert "question" in response.json()
        
        # 5. Verify RAG context was stored
        # (Implementation depends on RAG service)
```

**2. Create Integration Test Runner** (30 min)
```bash
# File: backend/test_integration_real.sh

#!/bin/bash
set -e

echo "🧪 Running Real LLM Integration Tests"
echo "======================================"

# Check for API keys
if [ -z "$GROQ_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: No API keys found"
    echo "Please set GROQ_API_KEY or OPENAI_API_KEY environment variable"
    exit 1
fi

echo ""
if [ -n "$GROQ_API_KEY" ]; then
    echo "✅ GROQ_API_KEY found"
fi
if [ -n "$OPENAI_API_KEY" ]; then
    echo "✅ OPENAI_API_KEY found"
fi

echo ""
echo "Running integration tests..."
echo ""

# Run tests with integration marker
pytest tests/integration/test_real_llm_integration.py \
    -m integration \
    -v \
    --tb=short \
    --maxfail=1

echo ""
echo "✅ Integration tests passed!"
```

**3. Manual Testing Checklist** (1 hour)
```markdown
# Manual Test Checklist - Real LLM Integration

## Groq Integration
- [ ] Add real Groq API token in Settings
- [ ] Verify token format validation (must start with gsk_)
- [ ] Fetch models list - should show llama2, mixtral, etc.
- [ ] Select a model (e.g., llama2-70b-4096)
- [ ] Start new investigation
- [ ] Verify first question is generated
- [ ] Answer with "A mobile fitness tracking app"
- [ ] Verify follow-up question is contextual
- [ ] Complete investigation (answer ~8 questions)
- [ ] Generate prompt - verify it includes all context
- [ ] Export to PDF - verify formatting

## OpenAI Integration
- [ ] Switch to OpenAI provider
- [ ] Add real OpenAI API token
- [ ] Verify token format (must start with sk-)
- [ ] Fetch models list - should show gpt-3.5, gpt-4, etc.
- [ ] Select a model (e.g., gpt-3.5-turbo)
- [ ] Start new investigation
- [ ] Complete same flow as Groq
- [ ] Compare response quality

## Error Handling
- [ ] Try to start chat without token - should block
- [ ] Try invalid token - should show error
- [ ] Try with expired token - should show auth error
- [ ] Try with rate-limited account - should retry
- [ ] Test network timeout handling
- [ ] Test provider switching mid-investigation

## Frontend Validation
- [ ] Chat button disabled without token
- [ ] Warning message shows when no token
- [ ] Clicking warning redirects to Settings
- [ ] Token status updates after configuration
- [ ] Chat button enables after valid config
- [ ] Loading states during API calls
- [ ] Error toasts for failed requests
```

#### Acceptance Criteria
- [ ] Integration tests pass with real Groq API
- [ ] Integration tests pass with real OpenAI API
- [ ] End-to-end investigation flow works with real LLM
- [ ] All error scenarios are tested
- [ ] Manual testing checklist completed
- [ ] Documentation updated with real API examples

---

### BLOCKER-3: Production-Ready Error Messages
**Priority:** P0 - CRITICAL BLOCKER  
**Estimated Time:** 1-2 hours  
**Current Status:** ⚠️ PARTIALLY IMPLEMENTED

#### Problem Statement
Current error messages may be too technical for end users. Need user-friendly messages that guide users to fix issues.

#### Required Implementation

**1. Standardize Error Response Format** (30 min)
```python
# Already implemented in utils/exceptions.py, but verify all routes use it

# Ensure all custom exceptions follow this pattern:
class APITokenError(AppException):
    def __init__(self, provider: str, reason: str):
        super().__init__(
            message=f"API token error for {provider}: {reason}",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"provider": provider, "reason": reason},
            user_message=f"There's a problem with your {provider} API token. Please check that it's valid and has the necessary permissions."
        )
```

**2. Add Frontend Error Handler** (45 min)
```javascript
// File: frontend/src/utils/errorHandler.js

export function handleAPIError(error, defaultMessage = 'An error occurred') {
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail;
    
    // Structured error from backend
    if (detail.user_message) {
      toast.error(detail.user_message, { duration: 6000 });
      
      // Handle specific actions
      if (detail.action_required === 'configure_token') {
        setTimeout(() => {
          navigate('/settings');
        }, 1500);
      }
      
      return detail;
    }
    
    // String error message
    if (typeof detail === 'string') {
      toast.error(detail);
      return { message: detail };
    }
  }
  
  // Generic error
  toast.error(defaultMessage);
  return { message: defaultMessage };
}

// Usage in components:
try {
  const response = await fetch('/api/chat/start');
  // ...
} catch (error) {
  handleAPIError(error, 'Failed to start investigation');
}
```

**3. User-Friendly Error Messages Map** (15 min)
```python
# File: backend/utils/error_messages.py

ERROR_MESSAGES = {
    "NO_TOKEN": {
        "technical": "No API token configured for provider",
        "user": "Please add your API token in Settings to get started.",
        "action": "configure_token"
    },
    "INVALID_TOKEN": {
        "technical": "Token format validation failed",
        "user": "The API token format is invalid. Please check and try again.",
        "action": "reconfigure_token"
    },
    "TOKEN_EXPIRED": {
        "technical": "API token expired or revoked",
        "user": "Your API token has expired. Please add a new token in Settings.",
        "action": "reconfigure_token"
    },
    "NO_MODEL_SELECTED": {
        "technical": "No model selected for provider",
        "user": "Please select a model from the available options in Settings.",
        "action": "select_model"
    },
    "RATE_LIMIT": {
        "technical": "API rate limit exceeded",
        "user": "You've reached the API rate limit. Please try again in a few minutes.",
        "action": "wait"
    },
    "NETWORK_ERROR": {
        "technical": "Network connection failed",
        "user": "Can't connect to the API. Please check your internet connection.",
        "action": "retry"
    },
    "QUOTA_EXCEEDED": {
        "technical": "API quota exceeded",
        "user": "Your API quota is exhausted. Please check your account or upgrade your plan.",
        "action": "check_billing"
    }
}
```

#### Acceptance Criteria
- [ ] All API errors return user-friendly messages
- [ ] Error responses include action_required field
- [ ] Frontend handles all error types gracefully
- [ ] Users are guided to fix issues (e.g., redirected to Settings)
- [ ] Technical details logged but not shown to users
- [ ] Toast notifications show appropriate duration

---

## ⚡ HIGH PRIORITY (Should Complete Before Launch)

### TASK-4: Environment Configuration Documentation
**Priority:** P1 - HIGH  
**Estimated Time:** 1 hour  
**Current Status:** ⚠️ INCOMPLETE

#### Required Files

**1. Create .env.example** (15 min)
```bash
# File: backend/.env.example

# LLM Provider API Keys
# Get Groq key from: https://console.groq.com/keys
GROQ_API_KEY=gsk_your_groq_api_key_here

# Get OpenAI key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your_openai_api_key_here

# Active Provider (groq or openai)
ACTIVE_PROVIDER=groq

# Selected Models
GROQ_SELECTED_MODEL=llama2-70b-4096
OPENAI_SELECTED_MODEL=gpt-3.5-turbo

# Application Settings
LOG_LEVEL=INFO
ENVIRONMENT=development

# RAG Settings (Optional)
ENABLE_RAG=true
VECTOR_STORE_PATH=./data/vectors

# Session Settings
SESSION_TIMEOUT_HOURS=24
```

**2. Update README.md** (30 min)
```markdown
# Add to README.md

## Quick Start

### 1. Clone and Install
\`\`\`bash
git clone <repo-url>
cd lovable_prompt_generator
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
\`\`\`

### 2. Configure API Keys

**Option A: Through Web Interface (Recommended)**
1. Start the application (see step 3)
2. Navigate to Settings
3. Add your Groq or OpenAI API token
4. Select a model

**Option B: Using Environment Variables**
\`\`\`bash
cp backend/.env.example backend/.env
# Edit backend/.env and add your API keys
\`\`\`

**Getting API Keys:**
- **Groq:** https://console.groq.com/keys (Free tier available)
- **OpenAI:** https://platform.openai.com/api-keys (Requires billing)

### 3. Run the Application
\`\`\`bash
# Terminal 1 - Backend
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev
\`\`\`

### 4. Access the Application
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 5. Start Your First Investigation
1. Click "Start Investigation"
2. Answer questions about your product
3. Generate comprehensive prompt
4. Export to PDF/Markdown

## Troubleshooting

### "Please configure your API token first"
- Go to Settings → API Configuration
- Add your Groq or OpenAI API token
- Select a model from the dropdown

### "Failed to fetch models"
- Check that your API token is valid
- Verify your internet connection
- Check API provider status page

### Tests Failing
- Ensure `.env` file exists in backend/
- Run: `pytest tests/ -v`
\`\`\`
```

**3. Create DEPLOYMENT.md** (15 min)
```markdown
# File: DEPLOYMENT.md

# Deployment Guide

## Environment Variables

Required environment variables for production:

\`\`\`bash
# LLM Provider Keys (at least one required)
GROQ_API_KEY=gsk_xxxxx
OPENAI_API_KEY=sk-xxxxx

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO

# Optional
ENABLE_RAG=true
SESSION_TIMEOUT_HOURS=24
\`\`\`

## Docker Deployment

\`\`\`bash
# Build
docker-compose build

# Run
docker-compose up -d

# Check logs
docker-compose logs -f
\`\`\`

## Production Checklist
- [ ] API keys configured
- [ ] Environment set to production
- [ ] HTTPS enabled
- [ ] CORS configured correctly
- [ ] Rate limiting enabled
- [ ] Monitoring configured
- [ ] Backup strategy in place
\`\`\`
```

---

### TASK-5: Docker Configuration for WeasyPrint
**Priority:** P1 - HIGH  
**Estimated Time:** 1 hour  
**Current Status:** ⚠️ NEEDS SYSTEM DEPENDENCIES

#### Problem Statement
WeasyPrint requires system libraries (Cairo, Pango, GDK-PixBuf) that must be installed in Docker container.

#### Required Implementation

**1. Update Dockerfile** (30 min)
```dockerfile
# File: backend/Dockerfile

FROM python:3.10-slim

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/conversations data/sessions data/vectors

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**2. Test Docker Build** (30 min)
```bash
# Build and test
cd backend
docker build -t lovable-backend .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key lovable-backend

# Test PDF generation endpoint
curl -X POST http://localhost:8000/api/export/session/test_session_id/pdf
```

---

### TASK-6: Rate Limiting Configuration
**Priority:** P1 - HIGH  
**Estimated Time:** 1 hour  
**Current Status:** ❌ NOT IMPLEMENTED

#### Required Implementation

**1. Add Rate Limiting Middleware** (45 min)
```python
# File: backend/middleware/rate_limiter.py

from fastapi import Request, HTTPException, status
from collections import defaultdict
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            "/api/chat/start": (5, 60),  # 5 requests per 60 seconds
            "/api/chat/message": (20, 60),  # 20 requests per 60 seconds
            "/api/prompt/generate": (10, 60),  # 10 requests per 60 seconds
        }
    
    def is_allowed(self, client_id: str, endpoint: str) -> bool:
        """Check if request is allowed"""
        if endpoint not in self.limits:
            return True
        
        max_requests, window_seconds = self.limits[endpoint]
        now = datetime.now()
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= max_requests:
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True


rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    client_id = request.client.host
    endpoint = request.url.path
    
    if not rate_limiter.is_allowed(client_id, endpoint):
        logger.warning("rate_limit_exceeded", client=client_id, endpoint=endpoint)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "RateLimitExceeded",
                "message": "Too many requests. Please try again later.",
                "user_message": "You're making requests too quickly. Please wait a moment and try again.",
                "retry_after": 60
            }
        )
    
    response = await call_next(request)
    return response
```

**2. Add to FastAPI App** (15 min)
```python
# File: backend/app.py

from middleware.rate_limiter import rate_limit_middleware

app.middleware("http")(rate_limit_middleware)
```

---

## 📝 MEDIUM PRIORITY (Nice to Have)

### TASK-7: Add Health Check Endpoint Enhancement
**Priority:** P2 - MEDIUM  
**Estimated Time:** 30 minutes

```python
# Enhance backend/app.py health check

@app.get("/api/health", tags=["health"])
async def health_check():
    """Enhanced health check with dependency status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check token configuration
    config = ConfigService()
    active_provider = config.get_active_provider()
    health_status["checks"]["api_token"] = {
        "status": "configured" if active_provider else "not_configured",
        "provider": active_provider
    }
    
    # Check RAG service
    try:
        rag = RAGService()
        health_status["checks"]["rag_service"] = {"status": "healthy"}
    except Exception as e:
        health_status["checks"]["rag_service"] = {"status": "unhealthy", "error": str(e)}
    
    # Overall status
    all_healthy = all(
        check.get("status") in ["healthy", "configured"]
        for check in health_status["checks"].values()
    )
    health_status["status"] = "healthy" if all_healthy else "degraded"
    
    return health_status
```

---

### TASK-8: Add Logging Configuration
**Priority:** P2 - MEDIUM  
**Estimated Time:** 30 minutes

```python
# File: backend/utils/logging_config.py

import structlog
import logging
import sys

def configure_logging(environment: str = "development"):
    """Configure structured logging"""
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if environment == "production" else logging.DEBUG,
    )
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if environment == "development":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Add to app.py
from utils.logging_config import configure_logging
configure_logging(os.getenv("ENVIRONMENT", "development"))
```

---

## 🧪 TESTING REQUIREMENTS

### Integration Test Coverage Required

```bash
# Minimum test coverage before launch:
- Token validation: 100%
- Real API integration: 80%
- Error handling: 90%
- Critical user flows: 100%

# Run full test suite:
pytest tests/ -v --cov=. --cov-report=term --cov-report=html

# Run only integration tests:
pytest tests/integration/ -m integration -v

# Run with real APIs:
GROQ_API_KEY=xxx pytest tests/integration/test_real_llm_integration.py
```

---

## ✅ DEFINITION OF DONE

Before considering the project "production-ready":

- [ ] **BLOCKER-1:** Token validation middleware implemented and tested
- [ ] **BLOCKER-2:** Real LLM API integration tests passing
- [ ] **BLOCKER-3:** User-friendly error messages everywhere
- [ ] **TASK-4:** Environment documentation complete
- [ ] **TASK-5:** Docker configuration with WeasyPrint working
- [ ] **TASK-6:** Rate limiting configured
- [ ] Frontend blocks all LLM calls until token configured
- [ ] Manual testing checklist completed
- [ ] README.md updated with quick start
- [ ] .env.example created
- [ ] Integration tests passing with real APIs
- [ ] All P0/P1 tasks complete
- [ ] System tested end-to-end with both providers

---

## 📊 ESTIMATED TIMELINE

| Task | Priority | Time | Dependencies |
|------|----------|------|--------------|
| BLOCKER-1: Token Validation | P0 | 2-3h | None |
| BLOCKER-2: Real API Testing | P0 | 3-4h | BLOCKER-1 |
| BLOCKER-3: Error Messages | P0 | 1-2h | BLOCKER-1 |
| TASK-4: Documentation | P1 | 1h | None |
| TASK-5: Docker Config | P1 | 1h | None |
| TASK-6: Rate Limiting | P1 | 1h | None |
| TASK-7: Health Check | P2 | 30m | None |
| TASK-8: Logging | P2 | 30m | None |

**Total Estimated Time:** 10-13 hours  
**Critical Path:** 6-9 hours (P0 tasks only)

---

## 🚀 LAUNCH READINESS CHECKLIST

### Pre-Launch Validation
- [ ] Can add Groq token via UI
- [ ] Can add OpenAI token via UI
- [ ] Can fetch and select models
- [ ] Chat start blocked without token
- [ ] Chat start blocked without model selection
- [ ] Chat works with Groq API
- [ ] Chat works with OpenAI API
- [ ] Error messages are user-friendly
- [ ] Rate limiting prevents abuse
- [ ] Docker deployment works
- [ ] PDF export works in Docker
- [ ] All integration tests pass
- [ ] Manual testing complete

### Documentation
- [ ] README.md has quick start guide
- [ ] .env.example exists
- [ ] DEPLOYMENT.md exists
- [ ] API documentation (Swagger) accessible
- [ ] Troubleshooting section complete

### Monitoring
- [ ] Health check endpoint working
- [ ] Structured logging configured
- [ ] Error tracking configured (optional)
- [ ] Usage metrics (optional)

---

## 🔧 QUICK COMMAND REFERENCE

```bash
# Start development
./start_backend.sh
./start_frontend.sh

# Run integration tests
cd backend
source ../.venv/bin/activate
bash test_integration_real.sh

# Test Docker
cd backend
docker-compose up --build

# Check health
curl http://localhost:8000/api/health

# Test token validation
curl -X POST http://localhost:8000/api/chat/start
# Should return 401 without token
```

---

**Last Updated:** November 16, 2025  
**Status:** Ready for Implementation  
**Next Action:** Start with BLOCKER-1 (Token Validation Middleware)
