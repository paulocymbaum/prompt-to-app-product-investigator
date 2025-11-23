# Product Investigator Chatbot - Backend

LLM-powered chatbot backend for investigating product ideas and generating comprehensive development prompts using LangChain, FastAPI, and RAG.

## Features

- 🤖 Multi-provider LLM support (Groq Cloud, OpenAI)
- 💬 Conversational product investigation
- 🧠 RAG-based conversation memory
- 📝 Comprehensive prompt generation
- 📊 LangGraph visualization
- 💾 Session management and persistence
- 🔒 Secure API token encryption
- 🚀 FastAPI with async support

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Virtual environment (recommended)
- Groq Cloud or OpenAI API key

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd lovable_prompt_generator/backend
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
GROQ_API_KEY=your-groq-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
SECRET_KEY=your-secret-encryption-key-here
```

## Running the Application

### Development Mode

```bash
python app.py
```

Or with uvicorn directly:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# Stop
docker-compose down
```

### Production Mode

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Project Structure

```
backend/
├── app.py                  # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── .env.example           # Environment variables template
├── models/                # Pydantic data models
│   ├── __init__.py
│   ├── conversation.py   # Conversation models
│   └── provider.py       # Provider models
├── routes/                # API route handlers
│   └── __init__.py
├── services/              # Business logic services
│   └── __init__.py
├── utils/                 # Utility functions
│   └── __init__.py
├── tests/                 # Unit and integration tests
│   ├── __init__.py
│   └── conftest.py       # Pytest fixtures
└── data/                  # Data storage (gitignored)
    ├── conversations/    # Markdown conversation files
    ├── sessions/         # Session state files
    └── vectors/          # FAISS vector store
```

## API Endpoints

### System
- `GET /` - Root endpoint
- `GET /health` - Health check

### Configuration (Coming Soon)
- `POST /api/config/token` - Set API token
- `GET /api/config/models` - List available models
- `POST /api/config/model/select` - Select model

### Chat (Coming Soon)
- `POST /api/chat/start` - Start investigation
- `POST /api/chat/message` - Send message
- `GET /api/chat/history/:sessionId` - Get history

### Prompts (Coming Soon)
- `GET /api/prompt/generate/:sessionId` - Generate prompt

### Sessions (Coming Soon)
- `POST /api/session/save` - Save session
- `GET /api/session/load/:sessionId` - Load session

## Testing

### Run all tests

```bash
pytest
```

### Run with coverage

```bash
pytest --cov=. --cov-report=html
```

### Run specific test file

```bash
pytest tests/test_config_service.py
```

## Development Guidelines

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings (Google style)
- Keep functions small and focused

### SOLID Principles

- **S**ingle Responsibility: Each service has one clear purpose
- **O**pen/Closed: Extend via inheritance, not modification
- **L**iskov Substitution: Derived classes maintain base contracts
- **I**nterface Segregation: Small, focused interfaces
- **D**ependency Inversion: Depend on abstractions

### DRY Principle

- Avoid code duplication
- Use utility functions for common operations
- Create reusable components

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq Cloud API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `SECRET_KEY` | Encryption secret | - |
| `LOG_LEVEL` | Logging level | INFO |
| `ENVIRONMENT` | Environment (development/production) | development |
| `DATA_DIR` | Data storage directory | ./data |
| `API_RATE_LIMIT` | Rate limit (req/min) | 100 |
| `DEFAULT_PROVIDER` | Default LLM provider | groq |
| `DEFAULT_TEMPERATURE` | LLM temperature | 0.7 |
| `RAG_TOP_K` | RAG retrieval count | 5 |

## Troubleshooting

### Import Errors

Make sure virtual environment is activated and dependencies are installed:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Port Already in Use

Change the port in `.env` or kill the process:

```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Docker Issues

```bash
# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

## Contributing

1. Create a feature branch
2. Make changes following code style guidelines
3. Write/update tests
4. Run tests and ensure >80% coverage
5. Submit pull request

## License

[Your License Here]

## Support

For issues and questions, please open a GitHub issue or contact the maintainers.
