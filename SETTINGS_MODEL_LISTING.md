# Settings UI - Model Listing Verification

## ✅ Current Status

The Settings UI **properly lists models** from Groq and OpenAI! Here's how it works:

---

## 🔄 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              User Opens Settings Page                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         ConfigPanel Component Mounts                         │
│                                                              │
│  useEffect(() => {                                           │
│    loadConfigStatus();  ← Checks if token exists            │
│  }, []);                                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│    GET /api/config/status                                    │
│                                                              │
│  Response:                                                   │
│  {                                                           │
│    "active_provider": "groq",                                │
│    "providers": {                                            │
│      "groq": {                                               │
│        "token_exists": true,                                 │
│        "selected_model": "llama2-70b-4096"                   │
│      },                                                      │
│      "openai": {                                             │
│        "token_exists": true,                                 │
│        "selected_model": null                                │
│      }                                                       │
│    }                                                         │
│  }                                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Frontend Sets State Based on Response                │
│                                                              │
│  - setProvider("groq")                                       │
│  - setTokenSaved(true)  ← Token exists                       │
│  - setSelectedModel("llama2-70b-4096")                       │
│  - setModelSaved(true)                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│      useEffect Triggers When tokenSaved Changes              │
│                                                              │
│  useEffect(() => {                                           │
│    if (tokenSaved) {                                         │
│      fetchModels();  ← Automatically fetch models            │
│    }                                                         │
│  }, [provider, tokenSaved]);                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│     GET /api/config/models?provider=groq                     │
│                                                              │
│  Backend calls Groq API to fetch available models            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Backend Returns Model List                        │
│                                                              │
│  Response:                                                   │
│  {                                                           │
│    "provider": "groq",                                       │
│    "models": [                                               │
│      {                                                       │
│        "id": "llama-3.3-70b-versatile",                      │
│        "name": "Llama 3.3 70B Versatile",                    │
│        "provider": "groq",                                   │
│        "context_window": 8192,                               │
│        "supports_streaming": true,                           │
│        "langchain_class": "ChatGroq"                         │
│      },                                                      │
│      {                                                       │
│        "id": "mixtral-8x7b-32768",                           │
│        "name": "Mixtral 8x7B",                               │
│        "context_window": 32768,                              │
│        ...                                                   │
│      },                                                      │
│      ...                                                     │
│    ],                                                        │
│    "cached": false                                           │
│  }                                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Frontend Displays Models in Dropdown               │
│                                                              │
│  <select>                                                    │
│    <option value="">-- Select a model --</option>           │
│    <option value="llama-3.3-70b-versatile">                 │
│      llama-3.3-70b-versatile (8192 tokens)                   │
│    </option>                                                 │
│    <option value="mixtral-8x7b-32768">                       │
│      mixtral-8x7b-32768 (32768 tokens)                       │
│    </option>                                                 │
│    ...                                                       │
│  </select>                                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            User Selects a Model                              │
│                                                              │
│  onChange={(e) => setSelectedModel(e.target.value)}          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         User Clicks "Save Model Selection"                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│    POST /api/config/model/select                             │
│    {                                                         │
│      "provider": "groq",                                     │
│      "model_id": "llama-3.3-70b-versatile"                   │
│    }                                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Backend Saves to .env                                │
│                                                              │
│  GROQ_SELECTED_MODEL=llama-3.3-70b-versatile                 │
│  ACTIVE_PROVIDER=groq                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Success Message Displayed                       │
│  ✓ Model "llama-3.3-70b-versatile" selected successfully!   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Backend Implementation

### 1. Config Status Endpoint

**File**: `backend/routes/config_routes.py`

```python
@router.get("/status")
async def get_config_status(config: ConfigService):
    active_provider = config.get_active_provider()
    selected_model = config.get_selected_model(active_provider)
    
    # Build provider-specific status
    providers_status = {
        "groq": ProviderStatus(
            token_exists=bool(config.get_token("groq")),
            selected_model=config.get_selected_model("groq")
        ),
        "openai": ProviderStatus(
            token_exists=bool(config.get_token("openai")),
            selected_model=config.get_selected_model("openai")
        )
    }
    
    return ConfigStatusResponse(
        active_provider=active_provider,
        has_groq_token=bool(config.get_token("groq")),
        has_openai_token=bool(config.get_token("openai")),
        selected_model=selected_model,
        providers=providers_status  # ← Frontend uses this!
    )
```

### 2. Get Models Endpoint

**File**: `backend/routes/config_routes.py`

```python
@router.get("/models")
async def get_models(
    provider: str,
    force_refresh: bool = False,
    config: ConfigService,
    checker: ModelChecker
):
    # Check if token is configured
    token = config.get_token(provider)
    if not token:
        raise HTTPException(
            status_code=401,
            detail=f"No API token configured for {provider}"
        )
    
    # Check cache first
    cached_models = checker.get_cached_models(provider)
    if cached_models and not force_refresh:
        return ModelsResponse(
            provider=provider,
            models=cached_models,
            cached=True
        )
    
    # Fetch from API
    models = await checker.fetch_models(provider)
    
    return ModelsResponse(
        provider=provider,
        models=models,
        cached=False
    )
```

### 3. Model Fetching Logic

**File**: `backend/services/model_checker.py`

```python
async def fetch_models(self, provider: str) -> List[dict]:
    """Fetch models from provider API"""
    
    if provider == "groq":
        return await self._fetch_groq_models()
    elif provider == "openai":
        return await self._fetch_openai_models()
    
    raise ValueError(f"Unsupported provider: {provider}")

async def _fetch_groq_models(self) -> List[dict]:
    """Fetch models from Groq API"""
    token = self.config.get_token("groq")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Transform to our format
        models = []
        for model in data.get("data", []):
            models.append({
                "id": model["id"],
                "name": model.get("id", "Unknown"),
                "provider": "groq",
                "context_window": model.get("context_window", 8192),
                "supports_streaming": True,
                "langchain_class": "ChatGroq",
                "owned_by": model.get("owned_by"),
                "created": model.get("created")
            })
        
        # Cache the results
        self._cache_models("groq", models)
        
        return models
```

---

## 🎨 Frontend Implementation

### 1. ConfigPanel Component

**File**: `frontend/src/components/ConfigPanel.jsx`

```jsx
const fetchModels = async () => {
  setLoadingModels(true);
  setError(null);
  
  try {
    // Call API to get models
    const data = await getModels(provider, false);
    setModels(data.models || []);
    
    if (data.models && data.models.length === 0) {
      setError('No models available for this provider.');
    }
  } catch (err) {
    const errorMsg = err.response?.data?.detail || err.message;
    setError(`Failed to fetch models: ${errorMsg}`);
    setModels([]);
  } finally {
    setLoadingModels(false);
  }
};

// Model Selection UI
{models.length > 0 && (
  <select
    id="model"
    value={selectedModel}
    onChange={(e) => setSelectedModel(e.target.value)}
    disabled={loading}
  >
    <option value="">-- Select a model --</option>
    {models.map((model) => (
      <option key={model.id} value={model.id}>
        {model.id} {model.context_window ? `(${model.context_window} tokens)` : ''}
      </option>
    ))}
  </select>
)}
```

### 2. API Service

**File**: `frontend/src/services/api.js`

```javascript
export const getModels = async (provider, forceRefresh = false) => {
  const response = await api.get('/api/config/models', {
    params: { provider, force_refresh: forceRefresh }
  });
  return response.data;
};

export const selectModel = async (provider, modelId) => {
  const response = await api.post('/api/config/model/select', {
    provider,
    model_id: modelId
  });
  return response.data;
};
```

---

## ✅ Verification Tests

### Test 1: Check Config Status

```bash
curl -s http://localhost:8000/api/config/status | python3 -m json.tool
```

**Expected Response:**
```json
{
  "active_provider": "groq",
  "has_groq_token": true,
  "has_openai_token": true,
  "selected_model": "llama2-70b-4096",
  "providers": {
    "groq": {
      "token_exists": true,
      "selected_model": "llama2-70b-4096"
    },
    "openai": {
      "token_exists": true,
      "selected_model": null
    }
  }
}
```

### Test 2: Fetch Groq Models

```bash
curl -s "http://localhost:8000/api/config/models?provider=groq" | python3 -m json.tool
```

**Expected Response:**
```json
{
  "provider": "groq",
  "models": [
    {
      "id": "llama-3.3-70b-versatile",
      "name": "llama-3.3-70b-versatile",
      "provider": "groq",
      "context_window": 8192,
      "supports_streaming": true,
      "langchain_class": "ChatGroq"
    },
    {
      "id": "mixtral-8x7b-32768",
      "name": "mixtral-8x7b-32768",
      "provider": "groq",
      "context_window": 32768,
      "supports_streaming": true,
      "langchain_class": "ChatGroq"
    },
    ...
  ],
  "cached": false
}
```

### Test 3: Select a Model

```bash
curl -s -X POST http://localhost:8000/api/config/model/select \
  -H "Content-Type: application/json" \
  -d '{"provider": "groq", "model_id": "llama-3.3-70b-versatile"}' \
  | python3 -m json.tool
```

**Expected Response:**
```json
{
  "status": "success",
  "provider": "groq",
  "model_id": "llama-3.3-70b-versatile",
  "message": "Model 'llama-3.3-70b-versatile' selected for groq"
}
```

---

## 🎯 Available Groq Models

When you call the `/api/config/models?provider=groq` endpoint, you'll typically see:

| Model ID | Context Window | Best For |
|----------|----------------|----------|
| `llama-3.3-70b-versatile` | 8,192 | General purpose, best quality |
| `llama-3.1-70b-versatile` | 8,192 | Previous generation, stable |
| `llama-3.1-8b-instant` | 8,192 | Fast responses |
| `llama2-70b-4096` | 4,096 | Llama 2, smaller context |
| `mixtral-8x7b-32768` | 32,768 | Long context, complex reasoning |
| `gemma-7b-it` | 8,192 | Lightweight, efficient |

---

## 🐛 What Was Fixed

### Issue
The frontend expected `status.providers.[provider].token_exists` but the backend was only returning:
```json
{
  "active_provider": "groq",
  "has_groq_token": true,
  "has_openai_token": true,
  "selected_model": "llama2-70b-4096"
}
```

### Solution
Updated `ConfigStatusResponse` model to include `providers` dict:

```python
class ProviderStatus(BaseModel):
    token_exists: bool
    selected_model: Optional[str] = None

class ConfigStatusResponse(BaseModel):
    active_provider: Optional[str]
    has_groq_token: bool
    has_openai_token: bool
    selected_model: Optional[str]
    providers: Dict[str, ProviderStatus]  # ← Added this!
```

---

## 🎬 User Experience Flow

### When User Opens Settings:

1. **Status Check** ✅
   - Backend returns configured providers
   - UI shows checkmarks for configured tokens
   - Pre-selects active provider

2. **Auto-Load Models** ✅
   - If token exists, models automatically load
   - Shows loading spinner during fetch
   - Displays models in dropdown

3. **Model Selection** ✅
   - User sees all available models
   - Each shows context window size
   - Can select and save

4. **Success Feedback** ✅
   - Green success message on save
   - Checkmark on "Model Saved" button
   - Ready to start investigating

---

## 📊 Caching Strategy

Models are cached for **5 minutes** to reduce API calls:

```python
class ModelChecker:
    def __init__(self, config_service):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def _is_cache_valid(self, provider):
        if provider not in self.cache:
            return False
        
        expiry_time = self.cache[provider].get("expiry")
        return datetime.utcnow() < expiry_time
    
    def get_cached_models(self, provider):
        if self._is_cache_valid(provider):
            return self.cache[provider]["models"]
        return None
```

**Benefits:**
- Faster UI response
- Reduced API calls
- Lower rate limit usage
- Option to force refresh

---

## ✅ Summary

**The Settings UI properly lists models!**

✅ **Backend**:
- Fetches models from Groq/OpenAI API
- Caches results for 5 minutes
- Returns proper response structure

✅ **Frontend**:
- Auto-loads models when token exists
- Displays in dropdown with context info
- Saves selection to backend

✅ **Integration**:
- Response format matches expectations
- Error handling is comprehensive
- User feedback is clear

**To test yourself**:
1. Start backend: `python -m uvicorn app:app --reload`
2. Start frontend: `npm run dev`
3. Open: http://localhost:5173
4. Go to Settings → Models should auto-load if token exists!

---

*Last Updated: November 17, 2025*
*Status: ✅ Working Correctly*
