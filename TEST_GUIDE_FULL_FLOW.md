# Full Application Test Guide - Token Setup & Conversation Flow

This guide walks through testing the complete application flow from user token setup to conversation completion.

## Prerequisites

- Groq API key (from console.groq.com)  
- Backend and frontend running

## Step 1: Start Backend

```bash
cd backend
source ../.venv/bin/activate
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 2: Start Frontend

In a new terminal:

```bash
cd frontend
npm install  # if not already done
npm run dev
```

Expected output:
```
  VITE v7.2.2  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

## Step 3: Test Token Configuration UI

1. **Open browser**: Navigate to `http://localhost:5173`

2. **Navigate to Settings/Config**:
   - Look for a Settings, Config, or API Configuration page
   - If not visible, check the navigation menu

3. **Configure Groq Token**:
   - Select **Groq** as provider
   - Enter your Groq API token (starts with `gsk_`)
   - Click **Test Connection** (optional but recommended)
   - Should see message: "✓ Connection successful! Found X models"
   - Click **Save Token**

4. **Select Model**:
   - A dropdown should appear with available models
   - Select a model (e.g., "llama-3.3-70b-versatile")
   - Click **Save Model Selection**
   - Should see: "🎉 Configuration complete! You're ready to start an investigation."

## Step 4: Test Conversation Flow

1. **Start Investigation**:
   - Navigate to the main chat/investigation page
   - Click "Start Investigation" or similar button
   - Should see an initial question about your product

2. **Answer Questions**:
   Test with these sample answers:
   
   **Question 1** (Usually about functionality):
   ```
   A task management app for remote teams with real-time collaboration and time tracking
   ```
   
   **Question 2** (Usually about target audience):
   ```
   Remote teams, project managers, and freelancers who need to coordinate work across time zones
   ```
   
   **Question 3** (Usually about key features):
   ```
   Task assignment, real-time chat, file sharing, time tracking, Gantt charts, and calendar integration
   ```
   
   **Question 4** (Usually about platforms):
   ```
   Web application with mobile apps for iOS and Android
   ```

3. **Verify Conversation Memory**:
   - Later questions should reference earlier answers
   - Example: If you mentioned "remote teams" earlier, the bot should remember this context
   - Questions should become more specific as the conversation progresses

4. **Complete Investigation**:
   - Continue answering until the investigation is complete
   - Should see a completion message
   - Option to generate final prompt should appear

5. **Generate Prompt**:
   - Click "Generate Prompt" or similar button
   - Should see a comprehensive prompt that includes all your answers
   - Verify it includes details from throughout the conversation

## Step 5: Test Session Persistence

1. **Refresh the page**
2. **Check if conversation persists**:
   - Navigate back to conversation history
   - Your previous answers should still be visible
   - Session should be marked as complete

## Expected Behavior Checklist

### Token Configuration
- [ ] Can switch between Groq and OpenAI providers
- [ ] Token validation shows error for invalid format
- [ ] Test Connection successfully fetches models
- [ ] Token is saved (and encrypted in backend)
- [ ] Model list populates after saving token
- [ ] Selected model is saved
- [ ] Completion message shows when fully configured

### Conversation Flow  
- [ ] Cannot start investigation without token configured
- [ ] Clear error message if token not configured
- [ ] Initial question is generated successfully
- [ ] Can answer questions  
- [ ] Follow-up questions are contextual
- [ ] Short answers trigger follow-up questions
- [ ] Questions progress through different categories
- [ ] Investigation eventually completes

### Memory & Context
- [ ] Later questions reference earlier answers
- [ ] Bot remembers product type, audience, features
- [ ] Final prompt includes all conversation details
- [ ] Session persists after page refresh

### Error Handling
- [ ] Invalid token format shows clear error
- [ ] Network errors show user-friendly messages
- [ ] Missing configuration redirects to settings
- [ ] Loading states show during API calls

## API Endpoints to Verify

You can test these directly using curl or Postman:

### 1. Check Config Status
```bash
curl http://localhost:8000/api/config/status
```

Expected response:
```json
{
  "active_provider": "groq",
  "providers": {
    "groq": {
      "token_exists": true,
      "selected_model": "llama-3.3-70b-versatile"
    }
  }
}
```

### 2. Start Investigation
```bash
curl -X POST http://localhost:8000/api/chat/start \
  -H "Content-Type: application/json"
```

Expected response:
```json
{
  "session_id": "abc-123-...",
  "question": {
    "text": "What is the main functionality...",
    "category": "FUNCTIONALITY"
  },
  "message": "Investigation started successfully"
}
```

### 3. Send Message
```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123-...",
    "message": "A task management app"
  }'
```

Expected response:
```json
{
  "question": {
    "text": "Who is your target audience...",
    "category": "AUDIENCE"
  },
  "complete": false,
  "message": "Message processed successfully"
}
```

## Troubleshooting

### "GROQ_API_KEY not found"
- Check that .env file exists in project root
- Verify GROQ_API_KEY is set correctly
- Try restarting the backend

### "Failed to connect to backend"
- Verify backend is running on port 8000
- Check for CORS errors in browser console
- Ensure frontend API base URL is `http://localhost:8000`

### "No models available"
- Token might be invalid - try a new one
- Check Groq API status at status.groq.com
- Verify token has correct permissions

### Questions not contextual
- Check RAG service is initialized
- Verify conversation history is being stored
- Check backend logs for errors

## Success Criteria

✅ **Complete Success** if:
1. Can configure token through UI (**no** manual .env editing needed)
2. Token is validated and saved
3. Model selection works
4. Can start and complete investigation 
5. Questions are contextual and remember previous answers
6. Final prompt includes all conversation details
7. Session persists after page refresh

## Notes

- The `test_conversation_flow.py` script tests the same flow programmatically
- All configuration is stored in backend/.env (encrypted)
- Tokens are encrypted using Fernet (symmetric encryption)
- Sessions are stored in `backend/storage/` directory
