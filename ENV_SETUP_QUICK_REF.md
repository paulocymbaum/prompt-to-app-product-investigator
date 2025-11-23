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
