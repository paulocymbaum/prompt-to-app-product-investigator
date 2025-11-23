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
