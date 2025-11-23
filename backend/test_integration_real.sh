#!/bin/bash
set -e

echo "🧪 Running Real LLM Integration Tests"
echo "======================================"

# Check for API keys
if [ -z "$GROQ_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    # Try to load from .env if not set
    if [ -f .env ]; then
        echo "Loading from .env..."
        export $(grep -v '^#' .env | xargs)
    fi
fi

if [ -z "$GROQ_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: No API keys found"
    echo "Please set GROQ_API_KEY or OPENAI_API_KEY environment variable"
    echo "Or create a .env file in the backend directory with these keys."
    exit 1
fi

echo ""
if [ -n "$GROQ_API_KEY" ]; then
    echo "✅ GROQ_API_KEY found"
fi
if [ -n "$OPENAI_API_KEY" ]; then
    echo "✅ OPENAI_API_KEY found"
fi

echo ""
echo "Running integration tests..."
echo ""

# Ensure we are in the backend directory
cd "$(dirname "$0")"

# Run tests with integration marker
# We need to make sure we are in the backend directory or python path is set correctly
export PYTHONPATH=$PYTHONPATH:.

python3 -m pytest tests/integration/test_real_llm_integration.py \
    -m integration \
    -v \
    --tb=short \
    --maxfail=1

echo ""
echo "✅ Integration tests passed!"
