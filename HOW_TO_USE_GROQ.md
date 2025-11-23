# How to Use Groq - Quick Start for Users 🚀

**TL;DR**: Get your free Groq API key → Add it to Settings → Start chatting!

---

## 1️⃣ Get Your Free Groq API Key (2 minutes)

### Step 1: Sign Up
Go to: **https://console.groq.com**

- Click "Sign Up" (or "Get Started")
- Use your email or Google/GitHub account
- ✅ **No credit card required**
- ✅ **Free tier included**

### Step 2: Create API Key
Once logged in:

1. Click on **"API Keys"** in the left sidebar
   - Or go directly to: https://console.groq.com/keys
2. Click **"Create API Key"** button
3. Give it a name (e.g., "Product Investigator")
4. Click **"Create"**
5. **Copy the key** (it starts with `gsk_`)

⚠️ **Important**: Save this key somewhere safe! You won't be able to see it again.

---

## 2️⃣ Add Your Key to the Application

You have **2 options**. Choose the one you prefer:

### Option A: Using the Web Interface (Easiest)

1. **Start the application**:
   ```bash
   # Open 2 terminals
   
   # Terminal 1 - Backend
   cd backend
   python -m uvicorn app:app --reload
   
   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

2. **Open your browser**:
   - Go to: http://localhost:5173

3. **Configure your API key**:
   - Click the **⚙️ Settings** icon (top right)
   - Select **"Groq"** as your provider
   - Paste your API key (starts with `gsk_`)
   - Click **"Save Token"** button
   - You should see: ✅ "Token saved successfully"

4. **Select a model**:
   - Click **"Fetch Models"** button
   - Wait for the list to load (~2 seconds)
   - Choose **"llama-3.3-70b-versatile"** (recommended)
   - Click **"Select Model"**
   - You should see: ✅ "Model selected"

5. **You're ready!**
   - Go back to the Chat interface
   - Click **"Start Investigation"**
   - Begin answering questions about your product! 🎉

### Option B: Using Environment Variables

1. **Create your environment file**:
   ```bash
   cd backend
   cp .env.example .env
   ```

2. **Edit the file**:
   ```bash
   # Use your favorite editor
   nano .env
   # or
   code .env
   # or
   vim .env
   ```

3. **Add your API key**:
   Find this line:
   ```bash
   GROQ_API_KEY=your-groq-api-key-here
   ```
   
   Replace with your actual key:
   ```bash
   GROQ_API_KEY=gsk_abc123def456...  # Your real key here
   ```

4. **Save the file** (Ctrl+O in nano, Cmd+S in VS Code)

5. **Start the backend**:
   ```bash
   python -m uvicorn app:app --reload
   ```

6. **Verify it's working**:
   - Go to: http://localhost:8000/api/config/status
   - You should see: `"has_groq_token": true`

---

## 3️⃣ Start Using the Application

### Your First Investigation

1. **Open the application**: http://localhost:5173

2. **Click "Start Investigation"**

3. **Answer the questions**:
   - The AI will ask about your product idea
   - Type your answers naturally
   - The AI adapts based on your responses
   - Usually 8-12 questions total

4. **Generate your prompt**:
   - After answering all questions
   - Click "Generate Prompt"
   - Get a comprehensive development prompt
   - Export as PDF or Markdown

### Example First Question

**AI**: "What problem does your product aim to solve?"

**You**: "I want to build a task management app for remote teams that integrates with Slack and includes AI-powered priority suggestions."

**AI**: (Asks relevant follow-up about your remote team features)

---

## 🔍 Verify Everything is Working

### Quick Health Check

```bash
# Test 1: Backend health
curl http://localhost:8000/api/health

# Expected: {"status":"healthy", ...}

# Test 2: Configuration status
curl http://localhost:8000/api/config/status

# Expected: {"has_groq_token":true, "active_provider":"groq", ...}
```

### Run Integration Tests

```bash
cd backend
./test_groq_integration.sh
```

This will test:
- ✅ API key validation
- ✅ Model fetching
- ✅ Chat session creation
- ✅ Message sending and LLM responses

---

## 🎯 Recommended Settings

### Best Model for Product Investigation

**Model**: `llama-3.3-70b-versatile`

**Why?**
- ✅ Most capable model on Groq
- ✅ Great for complex reasoning
- ✅ Generates high-quality questions
- ✅ Still very fast (Groq's hardware advantage)

### Alternative Models

| Model | When to Use |
|-------|-------------|
| `llama-3.1-8b-instant` | Quick prototyping, simple products |
| `mixtral-8x7b-32768` | Very complex products, long conversations |
| `gemma-7b-it` | Lightweight testing |

You can switch models anytime in Settings!

---

## ❓ Troubleshooting

### "No API token configured"

**Problem**: You haven't added your Groq API key yet.

**Solution**: Follow Step 2 above to add your key.

### "Invalid token format for groq"

**Problem**: Your API key doesn't start with `gsk_`.

**Solution**: 
- Check you copied the complete key
- Groq keys always start with `gsk_`
- Go to https://console.groq.com/keys and create a new key

### "Failed to fetch models"

**Possible causes**:
1. Invalid API key → Create a new one at console.groq.com
2. No internet connection → Check your network
3. Groq service issue → Check https://status.groq.com

**Debug**:
```bash
# Test your API key directly with Groq
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Chat button is disabled

**Problem**: Configuration is incomplete.

**Solution**:
1. Go to Settings
2. Verify: ✅ Token saved (green checkmark)
3. Verify: ✅ Model selected
4. Refresh the page
5. Try again

### Backend won't start

**Solution**:
```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Check for port conflicts
lsof -i :8000

# If port 8000 is in use, kill it or use different port:
python -m uvicorn app:app --reload --port 8001
```

---

## 🔒 Security Notes

### Keep Your API Key Safe

❌ **Don't**:
- Share your API key publicly
- Commit it to git
- Post it in Discord/Slack
- Use it in client-side code

✅ **Do**:
- Keep it in `.env` file (already in `.gitignore`)
- Use different keys for dev/prod
- Rotate keys regularly
- Monitor usage in Groq dashboard

### Monitor Your Usage

- Go to: https://console.groq.com
- Check "Usage" tab
- See API calls and token usage
- Free tier limits: 30 requests/minute

---

## 💡 Pro Tips

### Get Better Results

1. **Be specific**: "Build a mobile app for fitness tracking with social features" is better than "Make an app"

2. **Answer thoroughly**: The more context you provide, the better the final prompt will be

3. **Use the graph**: Check the conversation graph to see how topics are connected

4. **Iterate**: You can edit previous answers if you think of something better

### Save Time

1. **Save sessions**: Your investigations are auto-saved

2. **Load sessions**: Continue where you left off

3. **Export prompts**: Save as PDF or Markdown for later

4. **Switch models**: Try different models for different use cases

---

## 📚 Additional Resources

### Documentation
- **Full Setup Guide**: `GROQ_SETUP_GUIDE.md`
- **Quick Reference**: `ENV_SETUP_QUICK_REF.md`
- **API Docs**: http://localhost:8000/docs (when running)

### Groq Resources
- **Console**: https://console.groq.com
- **Docs**: https://console.groq.com/docs
- **Status**: https://status.groq.com
- **Community**: https://groq.com/community

### Support
- Check backend logs: `cd backend && tail -f app.log`
- Run diagnostics: `./validate_env.sh`
- Test integration: `./test_groq_integration.sh`

---

## ✅ Success Checklist

Before starting your first investigation, make sure:

- [ ] You have a Groq account
- [ ] You created an API key (starts with `gsk_`)
- [ ] You added the key (via UI or `.env`)
- [ ] You selected a model
- [ ] Backend is running (port 8000)
- [ ] Frontend is running (port 5173)
- [ ] Configuration status shows ✅ tokens configured
- [ ] Health check returns "healthy"

**All checked?** → You're ready to start investigating! 🚀

---

## 🎉 You're All Set!

Now you can:
1. ✅ Start product investigations
2. ✅ Get AI-powered contextual questions
3. ✅ Generate comprehensive development prompts
4. ✅ Export and use your prompts
5. ✅ Build amazing products!

**Questions?** Check `GROQ_SETUP_GUIDE.md` for detailed troubleshooting.

**Ready?** Click "Start Investigation" and let's go! 🚀
