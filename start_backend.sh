#!/bin/bash

echo "🔍 Checking for existing backend process on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✅ Killed existing backend process" || echo "✅ Port 8000 is free"

echo ""
echo "🚀 Starting backend server..."
sleep 1

# Set library path for WeasyPrint dependencies
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"

cd /Users/paulocymbaum/lovable_prompt_generator/backend
/Users/paulocymbaum/lovable_prompt_generator/.venv/bin/python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
