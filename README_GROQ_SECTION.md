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
