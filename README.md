# Product Investigator Chatbot with Groq Integration

A conversational AI system that investigates product ideas through interactive questioning, maintains conversation context using RAG, and generates comprehensive prompts following best practices in software engineering.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Groq API Key (free at [console.groq.com](https://console.groq.com))

### 1. Get Your Groq API Key (2 minutes)

1. Sign up at [https://console.groq.com](https://console.groq.com) (free, no credit card)
2. Go to [API Keys](https://console.groq.com/keys)
3. Click "Create API Key"
4. Copy your key (starts with `gsk_`)

### 2. Install & Configure

```bash
# Clone repository
git clone <your-repo-url>
cd lovable_prompt_generator

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Quick configuration (interactive)
cd ..
./setup_groq_key.sh

# OR manual configuration
cd backend
cp .env.example .env
nano .env  # Add: GROQ_API_KEY=gsk_your_key_here
```

### 3. Run the Application

```bash
# Terminal 1 - Backend
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev
```

### 4. Start Investigating!

- Open: http://localhost:5173
- Click "Start Investigation"
- Answer questions about your product
- Generate comprehensive prompt
- Export as PDF or Markdown

---

## 📖 Documentation

### For Users
- **[HOW_TO_USE_GROQ.md](./HOW_TO_USE_GROQ.md)** - Quick start guide
- **[GROQ_SETUP_GUIDE.md](./GROQ_SETUP_GUIDE.md)** - Comprehensive setup guide
- **[ENV_SETUP_QUICK_REF.md](./ENV_SETUP_QUICK_REF.md)** - Environment reference

### For Developers
- **[GROQ_INTEGRATION_COMPLETE.md](./GROQ_INTEGRATION_COMPLETE.md)** - Technical details
- **[system_design.md](./system_design.md)** - System architecture
- **[requirements.md](./requirements.md)** - Business requirements
- **API Docs**: http://localhost:8000/docs (when running)

---

## ✨ Features

### Core Functionality
- 🤖 **AI-Powered Investigation**: Contextual questions adapt to your answers
- 💾 **RAG Memory System**: Conversation context preserved using vector storage
- 📊 **LangGraph Visualization**: Visual representation of conversation flow
- 📝 **Prompt Generation**: Comprehensive prompts following SOLID/DRY principles
- 📄 **Export Options**: PDF and Markdown export
- 🔄 **Session Management**: Save and resume investigations

### LLM Integration
- ⚡ **Groq Cloud**: Ultra-fast inference with free tier
- 🤖 **OpenAI**: Support for GPT models
- 🔀 **Provider Switching**: Easy switching between providers
- 📊 **Model Selection**: Choose from multiple models
- 🔒 **Secure Storage**: Encrypted API key storage

### Technical Features
- 🔐 **Token Encryption**: Fernet encryption for API keys
- ✅ **Format Validation**: Automatic token format checking
- 🔄 **Retry Logic**: Exponential backoff for reliability
- 📡 **Streaming Responses**: Real-time response streaming
- 🎨 **Modern UI**: Clean, responsive interface
- 🧪 **Comprehensive Testing**: Integration test suite included

---

## 🛠️ Configuration

### Environment Variables

Create `backend/.env` with:

```bash
# Required: At least one API key
GROQ_API_KEY=gsk_your_key_here
OPENAI_API_KEY=sk_your_key_here  # Optional

# Provider configuration
ACTIVE_PROVIDER=groq
GROQ_SELECTED_MODEL=llama-3.3-70b-versatile

# Application settings
ENVIRONMENT=development
LOG_LEVEL=INFO
```

See `backend/.env.example` for all options.

### Available Models

| Model | Description | Context | Best For |
|-------|-------------|---------|----------|
| `llama-3.3-70b-versatile` | Latest Llama 3.3 | 8K | General purpose ⭐ |
| `llama-3.1-8b-instant` | Fast, lightweight | 8K | Quick responses |
| `mixtral-8x7b-32768` | Large context | 32K | Long conversations |
| `gemma-7b-it` | Efficient | 8K | Balanced |

---

## 🧪 Testing

### Validate Configuration
```bash
cd backend
./validate_env.sh
```

### Run Integration Tests
```bash
cd backend
./test_groq_integration.sh
```

Tests cover:
- ✅ API key validation
- ✅ Model fetching
- ✅ Chat session creation
- ✅ Message sending
- ✅ LLM response generation

### Run Unit Tests
```bash
cd backend
pytest tests/ -v --cov=.
```

---

## 🏗️ Architecture

### Backend
- **Framework**: FastAPI
- **LLM Integration**: LangChain (ChatGroq, ChatOpenAI)
- **Memory**: RAG with FAISS vector store
- **Storage**: File-based (Markdown conversations)
- **Security**: Fernet encryption for API keys

### Frontend
- **Framework**: React 18 with Vite
- **UI**: Tailwind CSS + shadcn/ui
- **State Management**: React Context API
- **Graph Visualization**: React Flow

### Data Flow
```
User → Frontend → FastAPI Routes → Services
  ↓
ConfigService (Token management)
  ↓
ModelChecker (Validation)
  ↓
LLMService (LangChain)
  ↓
ChatGroq/ChatOpenAI
  ↓
Groq/OpenAI API
```

---

## 🔒 Security

### Best Practices
- ✅ API keys encrypted at rest (Fernet)
- ✅ Token format validation
- ✅ Secure storage in `.env` (gitignored)
- ✅ No logging of sensitive data
- ✅ HTTPS support for API calls

### Recommendations
- Use different keys for dev/staging/prod
- Rotate keys regularly
- Monitor usage in provider dashboards
- Never commit `.env` to version control

---

## 📊 Project Structure

```
lovable_prompt_generator/
├── backend/
│   ├── app.py                      # FastAPI application
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Configuration template
│   ├── services/
│   │   ├── config_service.py       # Token management
│   │   ├── llm_service.py          # LLM integration
│   │   ├── model_checker.py        # Model validation
│   │   ├── conversation_service.py # Chat orchestration
│   │   └── rag_service.py          # Memory & context
│   ├── routes/
│   │   ├── config_routes.py        # Configuration API
│   │   └── chat_routes.py          # Chat API
│   ├── tests/                      # Test suite
│   ├── validate_env.sh             # Environment validator
│   └── test_groq_integration.sh    # Integration tests
├── frontend/
│   ├── src/
│   │   ├── components/             # React components
│   │   ├── services/               # API clients
│   │   └── hooks/                  # Custom hooks
│   └── package.json
├── docs/                           # Documentation
├── setup_groq_key.sh               # Interactive setup
├── show_groq_summary.sh            # Implementation summary
├── GROQ_SETUP_GUIDE.md             # User guide
├── HOW_TO_USE_GROQ.md              # Quick start
└── GROQ_INTEGRATION_COMPLETE.md    # Technical details
```

---

## 🚀 Deployment

### Docker (Recommended)

```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

### Manual Deployment

```bash
# Backend
cd backend
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker

# Frontend
cd frontend
npm run build
# Serve build/ with your web server
```

---

## 🐛 Troubleshooting

### "No API token configured"
**Solution**: Run `./setup_groq_key.sh` or add key via Settings UI

### "Invalid token format"
**Problem**: Key doesn't match expected format
**Solution**: 
- Groq keys must start with `gsk_`
- OpenAI keys start with `sk-` or `sk-proj-`
- Generate new key if needed

### "Failed to fetch models"
**Causes**: Invalid key, network issue, or provider issue
**Solution**:
```bash
# Test your key directly
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Backend won't start
**Solution**:
```bash
# Check dependencies
pip install -r requirements.txt

# Check port
lsof -i :8000  # Kill if needed

# Check logs
tail -f app.log
```

### More Help
- Run diagnostics: `cd backend && ./validate_env.sh`
- Test integration: `cd backend && ./test_groq_integration.sh`
- Check API docs: http://localhost:8000/docs
- Read full guide: [GROQ_SETUP_GUIDE.md](./GROQ_SETUP_GUIDE.md)

---

## 🤝 Contributing

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
cd frontend && npm install

# Run tests
cd backend
pytest tests/ -v

# Run with test configuration
export $(grep -v '^#' .env.test | xargs)
./test_groq_integration.sh
```

### Code Quality

- Follow SOLID principles
- Apply DRY (Don't Repeat Yourself)
- Write tests for new features
- Document public APIs
- Use type hints (Python)

---

## 📜 License

[Your License Here]

---

## 🙏 Acknowledgments

- **Groq**: Ultra-fast LLM inference
- **LangChain**: LLM orchestration framework
- **FastAPI**: Modern Python web framework
- **React**: UI framework

---

## 📞 Support

### Resources
- **Groq Console**: https://console.groq.com
- **API Keys**: https://console.groq.com/keys
- **Groq Docs**: https://console.groq.com/docs
- **Status Page**: https://status.groq.com

### Local Documentation
- Setup Guide: `GROQ_SETUP_GUIDE.md`
- Quick Start: `HOW_TO_USE_GROQ.md`
- API Docs: http://localhost:8000/docs

### Community
- [Issues](your-repo-url/issues)
- [Discussions](your-repo-url/discussions)

---

## 🎯 Roadmap

- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Team collaboration features
- [ ] Advanced RAG with hybrid search
- [ ] Integration with project management tools
- [ ] AI-powered code generation
- [ ] Prompt optimization engine

---

**Ready to start?** Run `./setup_groq_key.sh` and begin investigating! 🚀

---

*Last Updated: November 17, 2025*
*Version: 1.0.0*
*Status: ✅ Production Ready*
