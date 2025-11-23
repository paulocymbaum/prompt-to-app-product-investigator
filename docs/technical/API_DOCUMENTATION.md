# API Documentation

## Overview

The Product Investigator Chatbot exposes a RESTful API built with FastAPI. All endpoints return JSON responses and use standard HTTP status codes.

**Base URL**: `http://localhost:8000`  
**Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)  
**Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

## Authentication

Currently, no authentication is required for API access (MVP). Authentication will be added in future versions.

**Planned Authentication**:
- JWT tokens
- API keys for programmatic access
- OAuth2 for third-party integrations

---

## API Endpoints

### Configuration Routes (`/api/config`)

#### Save API Token

**Endpoint**: `POST /api/config/token`

**Description**: Save and validate LLM provider API token.

**Request Body**:
```json
{
  "provider": "groq",
  "token": "gsk_your_token_here"
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "provider": "groq",
  "message": "Token saved successfully"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid token format
- `422 Unprocessable Entity`: Missing required fields
- `500 Internal Server Error`: Server error

**Example**:
```bash
curl -X POST http://localhost:8000/api/config/token \
  -H "Content-Type: application/json" \
  -d '{"provider": "groq", "token": "gsk_..."}'
```

---

#### Get Available Models

**Endpoint**: `GET /api/config/models`

**Description**: Retrieve list of available models for a provider.

**Query Parameters**:
- `provider` (required): Provider name ("groq" or "openai")
- `force_refresh` (optional): Bypass cache (default: false)

**Response** (200 OK):
```json
{
  "models": [
    {
      "id": "llama3-70b-8192",
      "name": "Llama 3 70B",
      "provider": "groq",
      "context_window": 8192,
      "supports_streaming": true,
      "langchain_class": "ChatGroq"
    },
    {
      "id": "mixtral-8x7b-32768",
      "name": "Mixtral 8x7B",
      "provider": "groq",
      "context_window": 32768,
      "supports_streaming": true,
      "langchain_class": "ChatGroq"
    }
  ],
  "cached": true
}
```

**Error Responses**:
- `401 Unauthorized`: No token configured for provider
- `422 Unprocessable Entity`: Invalid provider
- `500 Internal Server Error`: API call failed

**Example**:
```bash
curl http://localhost:8000/api/config/models?provider=groq
```

---

#### Select Model

**Endpoint**: `POST /api/config/model/select`

**Description**: Select a specific model for use in conversations.

**Request Body**:
```json
{
  "provider": "groq",
  "model_id": "llama3-70b-8192"
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "provider": "groq",
  "model_id": "llama3-70b-8192",
  "message": "Model selected successfully"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid model ID
- `404 Not Found`: Model not found for provider
- `422 Unprocessable Entity`: Missing fields

---

#### Get Configuration Status

**Endpoint**: `GET /api/config/status`

**Description**: Get current configuration status for all providers.

**Response** (200 OK):
```json
{
  "groq": {
    "token_configured": true,
    "model_selected": "llama3-70b-8192"
  },
  "openai": {
    "token_configured": false,
    "model_selected": null
  },
  "active_provider": "groq"
}
```

---

#### Delete Token

**Endpoint**: `DELETE /api/config/token/{provider}`

**Description**: Remove API token for a provider.

**Path Parameters**:
- `provider`: Provider name ("groq" or "openai")

**Response** (204 No Content)

**Error Responses**:
- `404 Not Found`: Token not configured for provider

---

### Chat Routes (`/api/chat`)

#### Start Investigation

**Endpoint**: `POST /api/chat/start`

**Description**: Start a new product investigation session.

**Request Body** (optional):
```json
{
  "provider": "groq",
  "model_id": "llama3-70b-8192"
}
```

**Response** (201 Created):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": {
    "id": "q-uuid",
    "text": "Let's start by understanding what your product does. Can you describe the main functionality or purpose of your product idea?",
    "category": "functionality",
    "is_followup": false,
    "timestamp": "2025-11-16T10:30:00Z"
  },
  "message": "Investigation started successfully"
}
```

**Error Responses**:
- `422 Unprocessable Entity`: Invalid request body
- `500 Internal Server Error`: Failed to start investigation

**Example**:
```bash
curl -X POST http://localhost:8000/api/chat/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

#### Send Message

**Endpoint**: `POST /api/chat/message`

**Description**: Send user answer and receive next question.

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "A task management app for software developers that integrates with GitHub and Jira."
}
```

**Response** (200 OK):
```json
{
  "question": {
    "id": "q-uuid-2",
    "text": "Who are the primary users of this task management app?",
    "category": "users",
    "is_followup": false,
    "timestamp": "2025-11-16T10:32:00Z"
  },
  "complete": false
}
```

**Response** (200 OK - Investigation Complete):
```json
{
  "question": null,
  "complete": true,
  "message": "Investigation complete! You can now generate your prompt."
}
```

**Error Responses**:
- `404 Not Found`: Session not found
- `422 Unprocessable Entity`: Missing session_id or message
- `500 Internal Server Error`: Failed to process message

---

#### Get Conversation History

**Endpoint**: `GET /api/chat/history/{session_id}`

**Description**: Retrieve full conversation history for a session.

**Path Parameters**:
- `session_id`: Session UUID

**Response** (200 OK):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "id": "msg-uuid-1",
      "role": "assistant",
      "content": "Let's start by understanding what your product does...",
      "timestamp": "2025-11-16T10:30:00Z",
      "metadata": {
        "category": "functionality",
        "is_followup": false
      }
    },
    {
      "id": "msg-uuid-2",
      "role": "user",
      "content": "A task management app for software developers...",
      "timestamp": "2025-11-16T10:31:00Z",
      "metadata": {}
    }
  ],
  "total_messages": 12
}
```

**Error Responses**:
- `404 Not Found`: Session not found

---

#### Get Session Status

**Endpoint**: `GET /api/chat/status/{session_id}`

**Description**: Get investigation status and metadata.

**Path Parameters**:
- `session_id`: Session UUID

**Response** (200 OK):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "exists": true,
  "complete": false,
  "current_state": "users",
  "message_count": 4,
  "created_at": "2025-11-16T10:30:00Z",
  "last_updated": "2025-11-16T10:35:00Z"
}
```

**Response** (200 OK - Session Not Found):
```json
{
  "exists": false
}
```

---

#### Skip Question

**Endpoint**: `POST /api/chat/skip`

**Description**: Skip current question and move to next category.

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (200 OK):
```json
{
  "question": {
    "id": "q-uuid-next",
    "text": "What is the age range of your target audience?",
    "category": "demographics",
    "is_followup": false,
    "timestamp": "2025-11-16T10:36:00Z"
  },
  "skipped_category": "design",
  "message": "Question skipped"
}
```

**Response** (200 OK - Investigation Complete):
```json
{
  "question": null,
  "complete": true,
  "message": "Investigation complete"
}
```

---

#### Edit Previous Answer

**Endpoint**: `PUT /api/chat/edit`

**Description**: Edit a previous answer and update RAG context.

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message_id": "msg-uuid-2",
  "new_content": "Updated answer: A task management app specifically for remote software teams..."
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Answer updated successfully",
  "rag_updated": true
}
```

**Error Responses**:
- `404 Not Found`: Session or message not found
- `400 Bad Request`: Cannot edit system messages

---

#### WebSocket Connection

**Endpoint**: `WS /api/chat/ws/{session_id}`

**Description**: Real-time bidirectional chat connection.

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/chat/ws/session-id');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};

ws.send(JSON.stringify({
  type: 'message',
  content: 'User answer here'
}));
```

**Message Types**:

**Connected**:
```json
{
  "type": "connected",
  "session_id": "session-uuid",
  "message": "WebSocket connected"
}
```

**Question Received**:
```json
{
  "type": "question",
  "question": {
    "id": "q-uuid",
    "text": "Question text...",
    "category": "functionality"
  }
}
```

**Investigation Complete**:
```json
{
  "type": "complete",
  "message": "Investigation complete"
}
```

**Error**:
```json
{
  "type": "error",
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

---

### Session Routes (`/api/session`)

#### Save Session

**Endpoint**: `POST /api/session/save`

**Description**: Manually save current session state.

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (200 OK):
```json
{
  "status": "saved",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Session saved successfully"
}
```

**Error Responses**:
- `404 Not Found`: Session not found in memory
- `500 Internal Server Error`: Failed to save session

---

#### Load Session

**Endpoint**: `GET /api/session/load/{session_id}`

**Description**: Load a previously saved session.

**Path Parameters**:
- `session_id`: Session UUID

**Response** (200 OK):
```json
{
  "session": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "state": "users",
    "messages": [...],
    "metadata": {
      "created_at": "2025-11-16T10:30:00Z",
      "updated_at": "2025-11-16T10:35:00Z",
      "question_count": 3
    },
    "skipped_questions": ["design"]
  },
  "message": "Session loaded successfully"
}
```

**Error Responses**:
- `404 Not Found`: Session file not found

---

#### List Sessions

**Endpoint**: `GET /api/session/list`

**Description**: List all saved sessions with pagination.

**Query Parameters**:
- `page` (default: 1): Page number
- `page_size` (default: 20): Items per page
- `limit` (optional): Max items to return
- `offset` (optional): Skip items

**Response** (200 OK):
```json
{
  "sessions": [
    {
      "id": "session-uuid-1",
      "created_at": "2025-11-16T10:30:00Z",
      "updated_at": "2025-11-16T10:45:00Z",
      "message_count": 12,
      "state": "complete",
      "complete": true
    },
    {
      "id": "session-uuid-2",
      "created_at": "2025-11-15T14:20:00Z",
      "updated_at": "2025-11-15T14:30:00Z",
      "message_count": 6,
      "state": "design",
      "complete": false
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 20,
  "total_pages": 2
}
```

---

#### Delete Session

**Endpoint**: `DELETE /api/session/{session_id}`

**Description**: Delete a saved session.

**Path Parameters**:
- `session_id`: Session UUID

**Response** (200 OK):
```json
{
  "status": "deleted",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Session deleted successfully"
}
```

**Error Responses**:
- `404 Not Found`: Session not found

---

### Prompt Routes (`/api/prompt`)

#### Generate Prompt

**Endpoint**: `GET /api/prompt/generate/{session_id}`

**Description**: Generate comprehensive development prompt from investigation.

**Path Parameters**:
- `session_id`: Session UUID

**Query Parameters**:
- `force_refresh` (optional): Bypass cache (default: false)

**Response** (200 OK):
```json
{
  "prompt": "# Product Development Prompt\n\n## Your Role\n...",
  "cached": false,
  "token_count": 6432,
  "generation_time_ms": 1250
}
```

**Error Responses**:
- `404 Not Found`: Session not found
- `400 Bad Request`: Investigation not complete
- `500 Internal Server Error`: Failed to generate prompt

**Example**:
```bash
curl http://localhost:8000/api/prompt/generate/session-uuid
```

---

#### Regenerate Prompt

**Endpoint**: `POST /api/prompt/regenerate`

**Description**: Regenerate prompt with additional requirements.

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "focus_areas": ["security", "performance"],
  "additional_requirements": "Must include OAuth2 authentication and rate limiting"
}
```

**Response** (200 OK):
```json
{
  "prompt": "# Product Development Prompt\n\n...",
  "version": 2,
  "token_count": 7100,
  "changes_applied": true
}
```

---

#### Download Prompt

**Endpoint**: `GET /api/prompt/download/{session_id}`

**Description**: Download prompt as file.

**Path Parameters**:
- `session_id`: Session UUID

**Query Parameters**:
- `format`: File format ("txt" or "md", default: "md")

**Response** (200 OK):
- Content-Type: `text/plain` or `text/markdown`
- Content-Disposition: `attachment; filename="product_prompt_{session_id}.{format}"`
- Body: Prompt content

**Example**:
```bash
curl -O http://localhost:8000/api/prompt/download/session-uuid?format=md
```

---

#### Clear Cache

**Endpoint**: `DELETE /api/prompt/cache`

**Description**: Clear all prompt caches.

**Query Parameters**:
- `session_id` (optional): Clear specific session only

**Response** (200 OK):
```json
{
  "status": "cleared",
  "cleared_count": 5
}
```

---

### Graph Routes (`/api/graph`)

#### Get Visualization

**Endpoint**: `GET /api/graph/visualization/{session_id}`

**Description**: Get conversation graph data for visualization.

**Path Parameters**:
- `session_id`: Session UUID

**Response** (200 OK):
```json
{
  "nodes": [
    {
      "id": "q0",
      "type": "question",
      "content": "What does your product do?",
      "category": "functionality",
      "color": "#3B82F6",
      "timestamp": "2025-11-16T10:30:00Z"
    },
    {
      "id": "a0",
      "type": "answer",
      "content": "A task management app...",
      "category": "functionality",
      "color": "#3B82F6",
      "timestamp": "2025-11-16T10:31:00Z"
    }
  ],
  "edges": [
    {
      "source": "q0",
      "target": "a0",
      "label": "answer"
    },
    {
      "source": "a0",
      "target": "q1",
      "label": "next"
    }
  ],
  "metadata": {
    "session_id": "session-uuid",
    "total_interactions": 6,
    "created_at": "2025-11-16T10:30:00Z",
    "duration_minutes": 5.5
  }
}
```

**Error Responses**:
- `404 Not Found`: Session not found
- `500 Internal Server Error`: Failed to build graph

---

#### Get Mermaid Diagram

**Endpoint**: `GET /api/graph/mermaid/{session_id}`

**Description**: Get Mermaid diagram syntax for graph.

**Path Parameters**:
- `session_id`: Session UUID

**Response** (200 OK):
```json
{
  "mermaid": "graph TD\n    q0[\"What does your product do?\"]\n    style q0 fill:#3B82F6\n    a0{\"A task management app...\"}\n    style a0 fill:#3B82F6\n    q0 -->|answer| a0\n    a0 -->|next| q1\n    ..."
}
```

---

#### WebSocket Graph Updates

**Endpoint**: `WS /api/graph/ws/{session_id}`

**Description**: Real-time graph updates as conversation progresses.

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/graph/ws/session-id');

ws.onmessage = (event) => {
  const graphData = JSON.parse(event.data);
  // Update visualization
};
```

---

### Export Routes (`/api/export`) (Future)

#### Export to PDF

**Endpoint**: `GET /api/export/pdf/{session_id}`

**Description**: Export investigation report as PDF.

**Response** (200 OK):
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="investigation_report.pdf"`
- Body: PDF binary

---

#### Export to HTML

**Endpoint**: `GET /api/export/html/{session_id}`

**Description**: Export investigation report as HTML.

**Response** (200 OK):
- Content-Type: `text/html`
- Body: HTML content with embedded graph

---

#### Export to Markdown

**Endpoint**: `GET /api/export/markdown/{session_id}`

**Description**: Export investigation report as Markdown.

**Response** (200 OK):
- Content-Type: `text/markdown`
- Body: Markdown content

---

## Error Handling

### Standard Error Response

All errors follow this format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "timestamp": "2025-11-16T10:30:00Z",
  "path": "/api/chat/message",
  "request_id": "req-uuid"
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PUT, POST |
| 201 | Created | Resource created (new session) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing or invalid token |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | LLM API down |

### Error Codes

| Code | Description |
|------|-------------|
| `SESSION_NOT_FOUND` | Session ID doesn't exist |
| `INVALID_TOKEN_FORMAT` | API token format invalid |
| `TOKEN_NOT_CONFIGURED` | No token saved for provider |
| `MODEL_NOT_FOUND` | Model ID not available |
| `INVESTIGATION_INCOMPLETE` | Can't generate prompt yet |
| `LLM_API_ERROR` | External LLM API failed |
| `RAG_SERVICE_ERROR` | Vector store operation failed |
| `VALIDATION_ERROR` | Input validation failed |
| `RATE_LIMIT_EXCEEDED` | Too many requests |

---

## Rate Limiting (Future)

**Planned Limits**:
- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour
- LLM calls: 50 per session

**Headers**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1699876543
```

---

## Webhooks (Future)

Webhooks for asynchronous events:

**Events**:
- `investigation.completed`
- `prompt.generated`
- `session.saved`

**Payload**:
```json
{
  "event": "investigation.completed",
  "timestamp": "2025-11-16T10:30:00Z",
  "data": {
    "session_id": "session-uuid",
    "message_count": 12
  }
}
```

---

## SDK Examples

### Python

```python
import requests

class ProductInvestigatorClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def start_investigation(self):
        response = requests.post(f"{self.base_url}/api/chat/start")
        return response.json()
    
    def send_message(self, session_id, message):
        response = requests.post(
            f"{self.base_url}/api/chat/message",
            json={"session_id": session_id, "message": message}
        )
        return response.json()
    
    def generate_prompt(self, session_id):
        response = requests.get(
            f"{self.base_url}/api/prompt/generate/{session_id}"
        )
        return response.json()

# Usage
client = ProductInvestigatorClient()
session = client.start_investigation()
print(session['question']['text'])

answer = input("Your answer: ")
next_q = client.send_message(session['session_id'], answer)
print(next_q['question']['text'])
```

### JavaScript

```javascript
class ProductInvestigatorClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async startInvestigation() {
    const response = await fetch(`${this.baseUrl}/api/chat/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return response.json();
  }

  async sendMessage(sessionId, message) {
    const response = await fetch(`${this.baseUrl}/api/chat/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message })
    });
    return response.json();
  }

  async generatePrompt(sessionId) {
    const response = await fetch(
      `${this.baseUrl}/api/prompt/generate/${sessionId}`
    );
    return response.json();
  }
}

// Usage
const client = new ProductInvestigatorClient();
const session = await client.startInvestigation();
console.log(session.question.text);

const answer = prompt('Your answer:');
const nextQ = await client.sendMessage(session.session_id, answer);
console.log(nextQ.question.text);
```

---

## Testing with curl

### Full Investigation Flow

```bash
#!/bin/bash

# 1. Start investigation
RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat/start)
SESSION_ID=$(echo $RESPONSE | jq -r '.session_id')
echo "Session: $SESSION_ID"
echo $(echo $RESPONSE | jq -r '.question.text')

# 2. Answer first question
read -p "Your answer: " ANSWER
RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"$ANSWER\"}")
echo $(echo $RESPONSE | jq -r '.question.text')

# 3. Continue until complete...

# 4. Generate prompt
curl -s http://localhost:8000/api/prompt/generate/$SESSION_ID | jq -r '.prompt'
```

---

*Last Updated: November 16, 2025*
*Version: 1.0*
*Document Owner: API Team*
