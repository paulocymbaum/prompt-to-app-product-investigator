# API Routes Configuration - VERIFIED ✅

## Summary
All API routes have been verified and are working correctly. The frontend and backend are properly synchronized.

## Backend Routes (All use `/api` prefix)

### Config Routes - `/api/config`
- ✅ `POST /api/config/token` - Save API token
- ✅ `GET /api/config/models` - List available models
- ✅ `POST /api/config/model/select` - Select a model
- ✅ `GET /api/config/status` - Get configuration status
- ✅ `DELETE /api/config/token/{provider}` - Delete API token

### Chat Routes - `/api/chat`
- ✅ `POST /api/chat/start` - Start new chat session
- ✅ `POST /api/chat/message` - Send message
- ✅ `GET /api/chat/history/{session_id}` - Get chat history
- ✅ `GET /api/chat/status/{session_id}` - Get chat status

### Session Routes - `/api/session`
- ✅ `GET /api/session/list` - List all sessions
- ✅ `POST /api/session/save` - Save session
- ✅ `GET /api/session/load/{session_id}` - Load session
- ✅ `GET /api/session/{session_id}` - Get session details
- ✅ `DELETE /api/session/{session_id}` - Delete session

### Prompt Routes - `/api/prompt`
- ✅ `GET /api/prompt/generate/{session_id}` - Generate prompt
- ✅ `GET /api/prompt/download/{session_id}` - Download prompt
- ✅ `POST /api/prompt/regenerate/{session_id}` - Regenerate prompt

### Graph Routes - `/api/graph`
- ✅ `GET /api/graph/{session_id}` - Get conversation graph
- ✅ `GET /api/graph/viewer/{session_id}` - Get graph viewer HTML

### Export Routes - `/api/export`
- ✅ `GET /api/export/markdown/{session_id}` - Export as Markdown
- ✅ `GET /api/export/html/{session_id}` - Export as HTML
- ⚠️  `GET /api/export/pdf/{session_id}` - Export as PDF (requires WeasyPrint system dependencies)

## Frontend API Calls
All frontend API calls match the backend routes:
- ✅ `src/services/api.js` - All paths use `/api/*` correctly
- ✅ `src/components/PromptDisplay.jsx` - Uses `/api/prompt/*`
- ✅ `src/components/SessionManager.jsx` - Uses `/api/session/*`
- ✅ `src/components/ProgressTracker.jsx` - Uses `/api/chat/*`

## Route Configuration Details

### Backend (`backend/app.py`)
```python
# Routes are included WITHOUT prefix in app.py
app.include_router(config_routes.router)
app.include_router(chat_routes.router)
# ... etc
```

### Individual Route Files
Each route file defines its own `/api` prefix:
- `routes/config_routes.py`: `prefix="/api/config"`
- `routes/chat_routes.py`: `prefix="/api/chat"`
- `routes/session_routes.py`: `prefix="/api/session"`
- `routes/prompt_routes.py`: `prefix="/api/prompt"`
- `routes/graph_routes.py`: `prefix="/api/graph"`
- `routes/graph_viewer_routes.py`: `prefix="/api/graph/viewer"`
- `routes/export_routes.py`: `prefix="/api/export"`

## Testing

### Run All Tests
```bash
# Test all backend endpoints
./test_all_endpoints.sh

# Verify frontend API paths
./verify_frontend_paths.sh
```

### Start Servers
```bash
# Backend
./start_backend.sh

# Frontend  
./start_frontend.sh
```

## Current Status
- ✅ Backend running on http://localhost:8000
- ✅ Frontend running on http://localhost:5173
- ✅ All API routes responding correctly
- ✅ Frontend and backend properly synchronized

## Known Issues
1. **PDF Export** - Requires WeasyPrint system dependencies (`pango`, `gdk-pixbuf`). Will return an error message if dependencies are missing but won't crash the server.

## Last Verified
2025-11-17 03:00 UTC
