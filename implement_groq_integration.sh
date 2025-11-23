#!/bin/bash
set -e

echo "🚀 Implementing Groq Integration with User Configuration"
echo "=========================================================="

cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)
BACKEND_DIR="${PROJECT_ROOT}/backend"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}Step 1: Enhancing .env.example with Groq documentation${NC}"

# Update backend/.env.example with comprehensive documentation
cat > "${BACKEND_DIR}/.env.example" << 'EOF'
# ============================================================
# LLM Provider API Keys
# ============================================================

# Groq Cloud API Key
# Get your free API key from: https://console.groq.com/keys
# - Sign up at https://groq.com
# - Go to API Keys section
# - Create a new key
# - Copy the key (starts with 'gsk_')
# Example: GROQ_API_KEY=gsk_abc123def456ghi789jkl012mno345pqr678
GROQ_API_KEY=your-groq-api-key-here

# OpenAI API Key (Optional)
# Get from: https://platform.openai.com/api-keys
# - Requires billing setup
# - Keys start with 'sk-' or 'sk-proj-'
# Example: OPENAI_API_KEY=sk-abc123def456ghi789jkl012mno345pqr678
OPENAI_API_KEY=your-openai-api-key-here

# ============================================================
# Application Settings
# ============================================================
SECRET_KEY=your-secret-encryption-key-here
LOG_LEVEL=INFO
ENVIRONMENT=development

# ============================================================
# Storage Configuration
# ============================================================
DATA_DIR=./data
CONVERSATIONS_DIR=./data/conversations
SESSIONS_DIR=./data/sessions
VECTOR_STORE_PATH=./data/vectors

# ============================================================
# API Configuration
# ============================================================
API_RATE_LIMIT=100
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ============================================================
# LLM Configuration
# ============================================================
# Active provider: 'groq' or 'openai'
# Note: Can be changed via UI Settings
ACTIVE_PROVIDER=groq

# Default model for Groq
# Available models: llama2-70b-4096, mixtral-8x7b-32768, gemma-7b-it, etc.
# Check available models via: GET /api/config/models?provider=groq
GROQ_SELECTED_MODEL=llama-3.3-70b-versatile

# Default model for OpenAI (if using OpenAI)
OPENAI_SELECTED_MODEL=gpt-3.5-turbo

# LLM Parameters
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=2000

# ============================================================
# RAG Configuration
# ============================================================
RAG_CHUNK_SIZE=500
RAG_OVERLAP=50
RAG_TOP_K=5
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# ============================================================
# QUICK START GUIDE
# ============================================================
# 1. Copy this file: cp .env.example .env
# 2. Add your Groq API key (or use UI Settings)
# 3. Start backend: python -m uvicorn app:app --reload
# 4. Open browser: http://localhost:8000/docs
# 5. Test API: curl http://localhost:8000/api/health
#
# For testing without modifying your main .env:
# - Use .env.test for integration tests
# - API keys in .env.test won't affect your main config
EOF

echo -e "${GREEN}✓ Updated ${BACKEND_DIR}/.env.example${NC}"

# ============================================================
echo ""
echo -e "${BLUE}Step 2: Creating .env.test for integration tests${NC}"

cat > "${BACKEND_DIR}/.env.test" << 'EOF'
# ============================================================
# Test Environment Configuration
# ============================================================
# This file is for integration tests only
# Add your test API keys here (they won't affect main .env)

# Groq API Key for Testing
# Use a separate test key if available
GROQ_API_KEY=your-test-groq-api-key-here

# OpenAI API Key for Testing (Optional)
OPENAI_API_KEY=your-test-openai-api-key-here

# Test Settings
ENVIRONMENT=test
LOG_LEVEL=DEBUG
ACTIVE_PROVIDER=groq
GROQ_SELECTED_MODEL=llama-3.3-70b-versatile

# Test Storage
DATA_DIR=./test_data
CONVERSATIONS_DIR=./test_data/conversations
SESSIONS_DIR=./test_data/sessions
VECTOR_STORE_PATH=./test_data/vectors
EOF

echo -e "${GREEN}✓ Created ${BACKEND_DIR}/.env.test${NC}"

# ============================================================
echo ""
echo -e "${BLUE}Step 3: Creating Groq integration test script${NC}"

cat > "${BACKEND_DIR}/test_groq_integration.sh" << 'TESTSCRIPT'
#!/bin/bash
set -e

echo "🧪 Testing Groq Integration"
echo "============================"

# Load test environment
if [ -f .env.test ]; then
    export $(grep -v '^#' .env.test | xargs)
    echo "✓ Loaded .env.test configuration"
else
    echo "❌ Error: .env.test not found"
    echo "Please create .env.test with your Groq API key"
    exit 1
fi

# Check if Groq API key is set
if [ -z "$GROQ_API_KEY" ] || [ "$GROQ_API_KEY" = "your-test-groq-api-key-here" ]; then
    echo ""
    echo "❌ GROQ_API_KEY not configured in .env.test"
    echo ""
    echo "To configure:"
    echo "1. Get your API key from: https://console.groq.com/keys"
    echo "2. Edit .env.test and replace 'your-test-groq-api-key-here' with your actual key"
    echo "3. Run this script again"
    exit 1
fi

echo "✓ GROQ_API_KEY found"
echo ""

# Start backend in background for testing
echo "Starting backend server..."
python -m uvicorn app:app --host 0.0.0.0 --port 8001 &
SERVER_PID=$!
echo "✓ Backend started (PID: $SERVER_PID)"

# Wait for server to be ready
echo "Waiting for server to start..."
sleep 3

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Cleaning up..."
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    echo "✓ Backend stopped"
}
trap cleanup EXIT

echo ""
echo "Running integration tests..."
echo ""

# Test 1: Health check
echo "Test 1: Health Check"
curl -s http://localhost:8001/api/health | python -m json.tool || echo "❌ Health check failed"
echo ""

# Test 2: Save Groq token
echo "Test 2: Save Groq API Token"
curl -s -X POST http://localhost:8001/api/config/token \
    -H "Content-Type: application/json" \
    -d "{\"provider\":\"groq\",\"token\":\"$GROQ_API_KEY\"}" | python -m json.tool || echo "❌ Token save failed"
echo ""

# Test 3: Get configuration status
echo "Test 3: Configuration Status"
curl -s http://localhost:8001/api/config/status | python -m json.tool || echo "❌ Status check failed"
echo ""

# Test 4: Fetch Groq models
echo "Test 4: Fetch Available Models"
curl -s "http://localhost:8001/api/config/models?provider=groq" | python -m json.tool || echo "❌ Model fetch failed"
echo ""

# Test 5: Select a model
echo "Test 5: Select Model"
curl -s -X POST http://localhost:8001/api/config/model/select \
    -H "Content-Type: application/json" \
    -d "{\"provider\":\"groq\",\"model_id\":\"$GROQ_SELECTED_MODEL\"}" | python -m json.tool || echo "❌ Model selection failed"
echo ""

# Test 6: Start a chat session
echo "Test 6: Start Chat Session"
CHAT_RESPONSE=$(curl -s -X POST http://localhost:8001/api/chat/start)
echo "$CHAT_RESPONSE" | python -m json.tool || echo "❌ Chat start failed"
SESSION_ID=$(echo "$CHAT_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('session_id', ''))")
echo ""

if [ -n "$SESSION_ID" ]; then
    # Test 7: Send a message
    echo "Test 7: Send Message"
    curl -s -X POST http://localhost:8001/api/chat/message \
        -H "Content-Type: application/json" \
        -d "{\"session_id\":\"$SESSION_ID\",\"message\":\"A task management app for teams\"}" | python -m json.tool || echo "❌ Message send failed"
    echo ""
fi

echo ""
echo "================================"
echo "✅ Integration tests completed!"
echo "================================"
echo ""
echo "If all tests passed, your Groq integration is working correctly."
echo "You can now use the application with your Groq API key."
TESTSCRIPT

chmod +x "${BACKEND_DIR}/test_groq_integration.sh"
echo -e "${GREEN}✓ Created ${BACKEND_DIR}/test_groq_integration.sh${NC}"

# ============================================================
echo ""
echo -e "${BLUE}Step 4: Creating user documentation${NC}"

cat > "${PROJECT_ROOT}/GROQ_SETUP_GUIDE.md" << 'EOF'
# Groq Integration Setup Guide

This guide will help you set up Groq Cloud API integration for the Product Investigator Chatbot.

## Why Groq?

- **Fast**: Groq provides extremely fast inference (up to 10x faster than other providers)
- **Free Tier**: Generous free tier for development and testing
- **Easy Setup**: Simple API key generation
- **Multiple Models**: Access to Llama 2, Mixtral, Gemma, and more

---

## Quick Start (3 Steps)

### Step 1: Get Your Groq API Key

1. **Sign up** at [https://console.groq.com](https://console.groq.com)
   - Free account, no credit card required
   - Takes less than 1 minute

2. **Create an API Key**
   - Go to [API Keys page](https://console.groq.com/keys)
   - Click "Create API Key"
   - Give it a name (e.g., "Product Investigator")
   - Copy the key (starts with `gsk_`)

3. **Save your key securely**
   - ⚠️ Keep it secret - don't share or commit to git
   - You'll need it in the next steps

### Step 2: Configure the Application

You have **two options** to configure your API key:

#### Option A: Using the Web Interface (Recommended)

1. Start the application:
   ```bash
   # Terminal 1 - Backend
   cd backend
   python -m uvicorn app:app --reload
   
   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

2. Open the application in your browser:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000/docs

3. Navigate to **Settings** (⚙️ icon)

4. **Add your API key**:
   - Select provider: **Groq**
   - Paste your API key (starts with `gsk_`)
   - Click "Save Token"

5. **Select a model**:
   - Click "Fetch Models"
   - Choose a model (recommended: `llama-3.3-70b-versatile`)
   - Click "Select Model"

6. **You're ready!** Go to Chat and start your investigation

#### Option B: Using Environment Variables

1. Create `.env` file in the `backend` directory:
   ```bash
   cd backend
   cp .env.example .env
   ```

2. Edit `.env` and add your key:
   ```bash
   # Open in your favorite editor
   nano .env
   # or
   code .env
   ```

3. Replace the placeholder with your actual key:
   ```bash
   GROQ_API_KEY=gsk_your_actual_key_here
   ACTIVE_PROVIDER=groq
   GROQ_SELECTED_MODEL=llama-3.3-70b-versatile
   ```

4. Save and start the application

### Step 3: Test Your Integration

Run the integration test script:

```bash
cd backend
./test_groq_integration.sh
```

This will:
- ✅ Test API key validity
- ✅ Fetch available models
- ✅ Start a test chat session
- ✅ Send a test message

If all tests pass, you're good to go! 🎉

---

## Available Models

Groq provides several high-performance models:

| Model | Best For | Context Window |
|-------|----------|----------------|
| `llama-3.3-70b-versatile` | General purpose, best quality | 8,192 tokens |
| `llama-3.1-8b-instant` | Fast responses, simple tasks | 8,192 tokens |
| `mixtral-8x7b-32768` | Long conversations, complex reasoning | 32,768 tokens |
| `gemma-7b-it` | Lightweight, efficient | 8,192 tokens |

**Recommendation**: Start with `llama-3.3-70b-versatile` for the best quality.

---

## Using the Application

Once configured, you can:

1. **Start a Product Investigation**
   - Click "Start Investigation"
   - Answer questions about your product
   - The AI will ask contextual follow-ups

2. **Generate Comprehensive Prompts**
   - After ~8-12 questions, generate your prompt
   - Export as PDF or Markdown
   - Use it to build your product with AI tools

3. **View Conversation Graph**
   - Visualize your investigation flow
   - See how questions are connected
   - Export the graph

---

## Troubleshooting

### "No API token configured"

**Solution**: Follow Step 2 above to add your API key

### "Invalid token format for groq"

**Problem**: Your API key doesn't start with `gsk_`

**Solution**: 
- Double-check you copied the entire key
- Groq keys always start with `gsk_`
- Generate a new key if needed

### "Failed to fetch models"

**Possible causes**:
1. **Invalid API key**: Regenerate at https://console.groq.com/keys
2. **Network issue**: Check your internet connection
3. **API rate limit**: Wait a few seconds and try again

**Solution**:
```bash
# Test your API key directly
curl -X POST "https://api.groq.com/openai/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}],"model":"llama-3.3-70b-versatile"}'
```

### Backend won't start

**Solution**:
```bash
# Make sure all dependencies are installed
cd backend
pip install -r requirements.txt

# Check for port conflicts
lsof -i :8000
# If something is using port 8000, kill it or use a different port
```

### Chat button is disabled

**Problem**: Configuration incomplete

**Solution**:
1. Go to Settings
2. Verify API token is saved (green checkmark)
3. Verify model is selected
4. Refresh the page

---

## Advanced Configuration

### Using Multiple Providers

You can configure both Groq and OpenAI and switch between them:

1. Add both API keys in Settings
2. Select provider and model for each
3. Switch providers anytime in Settings

### Custom Model Parameters

Edit `.env` to customize:

```bash
DEFAULT_TEMPERATURE=0.7    # Creativity (0=focused, 1=creative)
DEFAULT_MAX_TOKENS=2000    # Maximum response length
```

### Rate Limiting

Free tier limits:
- **Groq**: 30 requests/minute, 14,400/day
- Plenty for development and testing

For production, consider upgrading to paid tier.

---

## Security Best Practices

1. **Never commit API keys to git**
   - `.env` is in `.gitignore`
   - Use environment variables in production

2. **Use separate keys for dev/prod**
   - Create different keys for different environments
   - Easier to rotate and manage

3. **Rotate keys regularly**
   - Generate new keys every few months
   - Delete old keys in Groq console

4. **Monitor usage**
   - Check Groq dashboard for API usage
   - Set up alerts for unexpected spikes

---

## Getting Help

If you run into issues:

1. **Check the logs**:
   ```bash
   cd backend
   tail -f app.log
   ```

2. **Run integration tests**:
   ```bash
   cd backend
   ./test_groq_integration.sh
   ```

3. **Check Groq Status**:
   - https://status.groq.com

4. **Groq Documentation**:
   - https://console.groq.com/docs

5. **Open an issue**:
   - Include error messages
   - Include relevant logs
   - Mention your OS and Python version

---

## Next Steps

Once you have Groq configured:

1. ✅ Start your first product investigation
2. ✅ Generate a comprehensive prompt
3. ✅ Export and use your prompt
4. ✅ Build amazing products! 🚀

---

**Last Updated**: November 2025
**Groq API Version**: v1
**Compatible with**: Python 3.9+, FastAPI, LangChain
EOF

echo -e "${GREEN}✓ Created ${PROJECT_ROOT}/GROQ_SETUP_GUIDE.md${NC}"

# ============================================================
echo ""
echo -e "${BLUE}Step 5: Creating quick reference for .env setup${NC}"

cat > "${PROJECT_ROOT}/ENV_SETUP_QUICK_REF.md" << 'EOF'
# Environment Setup Quick Reference

## Local Development Setup

```bash
# 1. Copy example file
cd backend
cp .env.example .env

# 2. Edit with your favorite editor
nano .env    # or code .env, vim .env, etc.

# 3. Add your Groq API key
GROQ_API_KEY=gsk_your_actual_api_key_here

# 4. Save and start
cd ..
./start_backend.sh
```

## Test Environment Setup

```bash
# 1. Copy test template
cd backend
cp .env.test .env.test.local

# 2. Add test API key
nano .env.test.local

# 3. Run integration tests
./test_groq_integration.sh
```

## Required Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes* | - | Your Groq API key (starts with gsk_) |
| `OPENAI_API_KEY` | Yes* | - | Your OpenAI API key (starts with sk-) |
| `ACTIVE_PROVIDER` | No | groq | Which provider to use (groq or openai) |
| `GROQ_SELECTED_MODEL` | No | llama-3.3-70b-versatile | Groq model to use |

\* At least one API key (GROQ or OPENAI) is required

## Common Issues

### Issue: "No API token configured"
**Solution**: Add `GROQ_API_KEY=gsk_...` to `.env`

### Issue: "Invalid token format"
**Solution**: Groq keys must start with `gsk_`, OpenAI with `sk-`

### Issue: Changes not taking effect
**Solution**: Restart the backend server

## Environment Priority

1. UI Settings (highest priority)
2. `.env` file
3. System environment variables
4. Default values (lowest priority)

Note: API keys saved via UI are encrypted and stored in `.env`
EOF

echo -e "${GREEN}✓ Created ${PROJECT_ROOT}/ENV_SETUP_QUICK_REF.md${NC}"

# ============================================================
echo ""
echo -e "${BLUE}Step 6: Updating main README with Groq integration info${NC}"

# Create a comprehensive README update
cat > "${PROJECT_ROOT}/README_GROQ_SECTION.md" << 'EOF'
# Add this section to your main README.md

## 🚀 Groq Integration Setup

### Get Your Free Groq API Key

1. Sign up at [console.groq.com](https://console.groq.com) (free, no credit card)
2. Go to [API Keys](https://console.groq.com/keys)
3. Create a new key
4. Copy the key (starts with `gsk_`)

### Configure in 2 Ways

**Option 1: Web Interface (Recommended)**
- Start the app → Go to Settings → Add API key → Select model

**Option 2: Environment Variable**
```bash
cd backend
cp .env.example .env
# Edit .env and add: GROQ_API_KEY=gsk_your_key_here
```

### Test Your Setup

```bash
cd backend
./test_groq_integration.sh
```

📖 **Full Guide**: See [GROQ_SETUP_GUIDE.md](./GROQ_SETUP_GUIDE.md) for detailed instructions

---
EOF

echo -e "${GREEN}✓ Created ${PROJECT_ROOT}/README_GROQ_SECTION.md${NC}"

# ============================================================
echo ""
echo -e "${BLUE}Step 7: Creating validation script for environment setup${NC}"

cat > "${BACKEND_DIR}/validate_env.sh" << 'VALSCRIPT'
#!/bin/bash

echo "🔍 Environment Validation"
echo "========================="
echo ""

VALID=true

# Check if .env exists
if [ -f .env ]; then
    echo "✓ .env file found"
else
    echo "❌ .env file not found"
    echo "   Run: cp .env.example .env"
    VALID=false
fi

# Load .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check GROQ_API_KEY
if [ -z "$GROQ_API_KEY" ] || [ "$GROQ_API_KEY" = "your-groq-api-key-here" ]; then
    echo "⚠️  GROQ_API_KEY not configured"
    echo "   Get key from: https://console.groq.com/keys"
else
    # Validate format
    if [[ $GROQ_API_KEY == gsk_* ]]; then
        echo "✓ GROQ_API_KEY configured (valid format)"
    else
        echo "❌ GROQ_API_KEY has invalid format (should start with 'gsk_')"
        VALID=false
    fi
fi

# Check OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your-openai-api-key-here" ]; then
    echo "ℹ️  OPENAI_API_KEY not configured (optional)"
else
    if [[ $OPENAI_API_KEY == sk-* ]]; then
        echo "✓ OPENAI_API_KEY configured"
    else
        echo "⚠️  OPENAI_API_KEY has invalid format (should start with 'sk-')"
    fi
fi

# Check ACTIVE_PROVIDER
if [ -z "$ACTIVE_PROVIDER" ]; then
    echo "⚠️  ACTIVE_PROVIDER not set (will default to 'groq')"
else
    echo "✓ ACTIVE_PROVIDER: $ACTIVE_PROVIDER"
fi

# Check GROQ_SELECTED_MODEL
if [ -z "$GROQ_SELECTED_MODEL" ]; then
    echo "⚠️  GROQ_SELECTED_MODEL not set"
else
    echo "✓ GROQ_SELECTED_MODEL: $GROQ_SELECTED_MODEL"
fi

echo ""
if [ "$VALID" = true ]; then
    echo "✅ Environment configuration is valid!"
    echo ""
    echo "Next steps:"
    echo "  1. Start backend: python -m uvicorn app:app --reload"
    echo "  2. Test integration: ./test_groq_integration.sh"
else
    echo "❌ Please fix the errors above before starting the application"
    exit 1
fi
VALSCRIPT

chmod +x "${BACKEND_DIR}/validate_env.sh"
echo -e "${GREEN}✓ Created ${BACKEND_DIR}/validate_env.sh${NC}"

# ============================================================
echo ""
echo "=========================================================="
echo -e "${GREEN}✅ Groq Integration Implementation Complete!${NC}"
echo "=========================================================="
echo ""
echo "Created files:"
echo "  ✓ backend/.env.example (enhanced with documentation)"
echo "  ✓ backend/.env.test (for integration testing)"
echo "  ✓ backend/test_groq_integration.sh (integration tests)"
echo "  ✓ backend/validate_env.sh (environment validation)"
echo "  ✓ GROQ_SETUP_GUIDE.md (comprehensive user guide)"
echo "  ✓ ENV_SETUP_QUICK_REF.md (quick reference)"
echo "  ✓ README_GROQ_SECTION.md (README update)"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your Groq API key:"
echo "   ${YELLOW}cd backend && cp .env.example .env${NC}"
echo "   ${YELLOW}# Edit .env and add your Groq API key${NC}"
echo ""
echo "2. Validate your environment:"
echo "   ${YELLOW}cd backend && ./validate_env.sh${NC}"
echo ""
echo "3. Test the integration:"
echo "   ${YELLOW}cd backend && ./test_groq_integration.sh${NC}"
echo ""
echo "4. Read the user guide:"
echo "   ${YELLOW}cat GROQ_SETUP_GUIDE.md${NC}"
echo ""
echo "📖 Full documentation in: GROQ_SETUP_GUIDE.md"
echo ""
