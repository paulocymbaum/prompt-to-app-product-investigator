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
