# How the System Knows Which Groq Model to Call

## 📋 Quick Answer

The system determines which Groq model to call through this priority chain:

```
1. Explicit parameter (if provided) → highest priority
2. Environment variable: GROQ_SELECTED_MODEL
3. Environment variable: DEFAULT_MODEL
4. Fallback: raises RuntimeError "No model selected"
```

---

## 🔍 Detailed Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Action                               │
│  • Starts chat OR                                            │
│  • Sends message                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Chat Route Handler                              │
│  POST /api/chat/start                                        │
│  POST /api/chat/message                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           ConversationService.start_investigation()          │
│  OR ConversationService.process_answer()                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│               LLMService.initialize_provider()               │
│                                                              │
│  Step 1: Get provider                                        │
│    if provider is None:                                      │
│      provider = config.get_active_provider()                 │
│      # Reads: ACTIVE_PROVIDER env var                        │
│                                                              │
│  Step 2: Get model_id                                        │
│    if model_id is None:                                      │
│      model_id = config.get_selected_model()  ←── HERE!       │
│      # This is where model is determined                     │
│                                                              │
│  Step 3: Get API key                                         │
│    api_key = config.get_token(provider)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         ConfigService.get_selected_model(provider)           │
│                                                              │
│  def get_selected_model(provider=None):                      │
│    if not provider:                                          │
│      provider = get_active_provider()                        │
│      # Returns: ACTIVE_PROVIDER or "groq"                    │
│                                                              │
│    # For Groq, this becomes:                                 │
│    env_var = "GROQ_SELECTED_MODEL"                           │
│    model = os.getenv("GROQ_SELECTED_MODEL")                  │
│                                                              │
│    # Returns model from .env file                            │
│    return model  # e.g., "llama2-70b-4096"                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│       ModelChecker.get_langchain_model()                     │
│                                                              │
│  Creates the actual LangChain model instance:                │
│                                                              │
│  if provider == "groq":                                      │
│    return ChatGroq(                                          │
│      groq_api_key=api_key,                                   │
│      model_name=model_id,  ←── "llama2-70b-4096"             │
│      temperature=0.7,                                        │
│      max_tokens=2000                                         │
│    )                                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Groq API Call                               │
│  POST https://api.groq.com/openai/v1/chat/completions       │
│  {                                                           │
│    "model": "llama2-70b-4096",  ←── Model is specified here  │
│    "messages": [...],                                        │
│    "temperature": 0.7,                                       │
│    "max_tokens": 2000                                        │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Configuration Storage

The model selection is stored in **two places**:

### 1. Environment Variable (`.env` file)
```bash
# backend/.env
GROQ_SELECTED_MODEL='llama2-70b-4096'
```

### 2. Memory (Runtime)
```python
# In LLMService instance
self.model_id = "llama2-70b-4096"
```

---

## 🔄 How Model Gets Set

### Method 1: Via Web UI (Most Common)

```
User Action Flow:
1. User goes to Settings
2. Clicks "Fetch Models" button
   ↓
3. Frontend calls: GET /api/config/models?provider=groq
   ↓
4. Backend fetches available models from Groq API
   ↓
5. Frontend displays list (e.g., llama2-70b-4096, mixtral-8x7b, etc.)
   ↓
6. User selects "llama-3.3-70b-versatile"
   ↓
7. Frontend calls: POST /api/config/model/select
   {
     "provider": "groq",
     "model_id": "llama-3.3-70b-versatile"
   }
   ↓
8. Backend (ConfigService.save_selected_model):
   - Writes to .env file: GROQ_SELECTED_MODEL=llama-3.3-70b-versatile
   - Sets ACTIVE_PROVIDER=groq
   ↓
9. Done! Model is now configured
```

### Method 2: Via Environment Variable

```bash
# Edit backend/.env
GROQ_SELECTED_MODEL=llama-3.3-70b-versatile
ACTIVE_PROVIDER=groq
```

### Method 3: Via Setup Script

```bash
./setup_groq_key.sh
# Script automatically sets:
# GROQ_SELECTED_MODEL=llama-3.3-70b-versatile
```

---

## 🔍 Code Trace Example

Let's trace a real example when a user sends a chat message:

### Step 1: User sends message
```javascript
// Frontend
POST /api/chat/message
{
  "session_id": "abc123",
  "message": "I want to build a task manager"
}
```

### Step 2: Chat route receives request
```python
# backend/routes/chat_routes.py
@router.post("/api/chat/message")
async def send_message(request: MessageRequest):
    conv_service = ConversationService()
    result = await conv_service.process_answer(
        session_id=request.session_id,
        answer=request.message
    )
```

### Step 3: Conversation service needs LLM
```python
# backend/services/conversation_service.py
async def process_answer(self, session_id, answer):
    # Need to generate next question using LLM
    llm_service = LLMService(config_service, model_checker)
    
    # Initialize LLM (no explicit model_id passed)
    llm_service.initialize_provider()  # ← No parameters!
```

### Step 4: LLM service determines model
```python
# backend/services/llm_service.py
def initialize_provider(self, provider=None, model_id=None):
    # provider is None, so get from config
    if provider is None:
        provider = self.config.get_active_provider()
        # Returns: "groq" (from ACTIVE_PROVIDER in .env)
    
    # model_id is None, so get from config
    if model_id is None:
        model_id = self.config.get_selected_model()
        # ← THIS IS WHERE IT HAPPENS!
```

### Step 5: Config service reads environment
```python
# backend/services/config_service.py
def get_selected_model(self, provider=None):
    if not provider:
        provider = self.get_active_provider()
        # Returns: "groq"
    
    # Build environment variable name
    env_var = f"{provider.upper()}_SELECTED_MODEL"
    # env_var = "GROQ_SELECTED_MODEL"
    
    # Read from environment
    model = os.getenv("GROQ_SELECTED_MODEL")
    # Returns: "llama2-70b-4096"
    
    return model
```

### Step 6: Model checker creates instance
```python
# backend/services/model_checker.py
def get_langchain_model(self, provider, model_id, api_key, ...):
    if provider == "groq":
        return ChatGroq(
            groq_api_key=api_key,
            model_name=model_id,  # ← "llama2-70b-4096"
            temperature=temperature,
            max_tokens=max_tokens
        )
```

### Step 7: LangChain makes API call
```python
# LangChain internally
response = await groq_client.chat.completions.create(
    model="llama2-70b-4096",  # ← Sent to Groq API
    messages=[...],
    temperature=0.7
)
```

---

## 🎯 Current Configuration

Based on your `.env` file:

```bash
ACTIVE_PROVIDER='groq'
GROQ_SELECTED_MODEL='llama2-70b-4096'
```

**This means:**
- Provider: Groq Cloud
- Model: llama2-70b-4096 (Llama 2 70B, 4K context window)

---

## 🔧 How to Change the Model

### Option 1: Via UI
```
1. Go to Settings
2. Click "Fetch Models"
3. Select different model (e.g., llama-3.3-70b-versatile)
4. Click "Select Model"
```

### Option 2: Edit .env
```bash
# backend/.env
GROQ_SELECTED_MODEL='llama-3.3-70b-versatile'
```

### Option 3: API Call
```bash
curl -X POST http://localhost:8000/api/config/model/select \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "groq",
    "model_id": "llama-3.3-70b-versatile"
  }'
```

---

## 🚨 What Happens If No Model Is Set?

```python
# In LLMService.initialize_provider()
if model_id is None:
    model_id = self.config.get_selected_model()
    if not model_id:
        raise RuntimeError("No model selected")
        # Application will fail with clear error message
```

**Error Message:**
```
RuntimeError: No model selected
```

**Solution:**
- Set `GROQ_SELECTED_MODEL` in `.env`, OR
- Select a model via Settings UI, OR
- Pass `model_id` explicitly when initializing

---

## 📊 Priority Order Summary

When determining which model to use:

| Priority | Source | Example |
|----------|--------|---------|
| 1 (Highest) | Explicit parameter | `initialize_provider(model_id="mixtral-8x7b")` |
| 2 | Environment variable | `GROQ_SELECTED_MODEL='llama2-70b-4096'` |
| 3 | Default fallback | `DEFAULT_MODEL='llama2-70b-4096'` (if set) |
| 4 (Lowest) | Error raised | `RuntimeError: No model selected` |

---

## 💡 Best Practices

### 1. Always Set a Model
```bash
# In .env
GROQ_SELECTED_MODEL=llama-3.3-70b-versatile
```

### 2. Use UI for Easy Switching
The Settings panel makes it easy to switch between models without editing files.

### 3. Different Models for Different Tasks
```python
# Example: Use fast model for simple queries
llm_service.initialize_provider(
    provider="groq",
    model_id="llama-3.1-8b-instant"  # Fast model
)

# Use powerful model for complex reasoning
llm_service.initialize_provider(
    provider="groq",
    model_id="mixtral-8x7b-32768"  # Complex reasoning
)
```

---

## 🔍 Debugging Model Selection

### Check Current Configuration
```bash
# See what model is configured
curl http://localhost:8000/api/config/status
```

**Response:**
```json
{
  "active_provider": "groq",
  "has_groq_token": true,
  "has_openai_token": true,
  "selected_model": "llama2-70b-4096"  ← Current model
}
```

### Check Environment Variables
```bash
cd backend
cat .env | grep SELECTED_MODEL
```

### Check Runtime Configuration
```python
# In Python console
from services.config_service import ConfigService

config = ConfigService()
provider = config.get_active_provider()
model = config.get_selected_model(provider)

print(f"Provider: {provider}")
print(f"Model: {model}")
```

---

## 📖 Related Files

- **Model Selection Logic**: `backend/services/config_service.py` (lines 242-262)
- **LLM Initialization**: `backend/services/llm_service.py` (lines 59-115)
- **Model Instance Creation**: `backend/services/model_checker.py` (lines 280-340)
- **API Endpoints**: `backend/routes/config_routes.py`
- **Environment Config**: `backend/.env`

---

## ✅ Summary

**The system knows which Groq model to call by:**

1. **Reading** `GROQ_SELECTED_MODEL` from the `.env` file
2. **Using** that value when creating the `ChatGroq` instance
3. **Passing** it to the Groq API in the `model` parameter

**The model is set by:**
- User selecting it in the Settings UI, OR
- Developer editing the `.env` file, OR
- API call to `/api/config/model/select`

**Current model:** `llama2-70b-4096` (from your `.env`)

**To change:** Go to Settings → Fetch Models → Select a different model → Done!

---

*For more details, see: `backend/services/config_service.py` and `backend/services/llm_service.py`*
