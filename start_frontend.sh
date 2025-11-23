#!/bin/bash

echo "🔍 Checking for existing frontend process on port 5173..."
lsof -ti:5173 | xargs kill -9 2>/dev/null && echo "✅ Killed existing frontend process" || echo "✅ Port 5173 is free"

echo ""
echo "🚀 Starting frontend server..."
sleep 1

cd /Users/paulocymbaum/lovable_prompt_generator/frontend
npm run dev
