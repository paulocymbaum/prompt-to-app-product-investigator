#!/bin/bash

# Master Startup Script - Start both frontend and backend
echo "=========================================="
echo "🚀 STARTING LOVABLE PROMPT GENERATOR"
echo "=========================================="
echo ""

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
sleep 2
echo "✅ Ports cleared"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Start backend
echo "🔧 Starting backend..."
cd "$SCRIPT_DIR/backend"
source "$SCRIPT_DIR/.venv/bin/activate"
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
sleep 8

# Check backend started
if lsof -ti:8000 > /dev/null; then
    echo "✅ Backend started successfully on http://localhost:8000"
else
    echo "❌ Backend failed to start. Check /tmp/backend.log"
    tail -20 /tmp/backend.log
    exit 1
fi
echo ""

# Start frontend
echo "🎨 Starting frontend..."
cd "$SCRIPT_DIR/frontend"
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"
sleep 5

# Check frontend started
if lsof -ti:5173 > /dev/null; then
    echo "✅ Frontend started successfully on http://localhost:5173"
else
    echo "❌ Frontend failed to start. Check /tmp/frontend.log"
    tail -20 /tmp/frontend.log
    exit 1
fi
echo ""

# Final status
echo "=========================================="
echo "✅ ALL SERVICES RUNNING"
echo "=========================================="
echo ""
echo "🌐 Frontend: http://localhost:5173"
echo "🔧 Backend:  http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Process IDs:"
echo "   Backend:  $BACKEND_PID"
echo "   Frontend: $FRONTEND_PID"
echo ""
echo "📝 Logs:"
echo "   Backend:  /tmp/backend.log"
echo "   Frontend: /tmp/frontend.log"
echo ""
echo "🛑 To stop: lsof -ti:8000 | xargs kill -9; lsof -ti:5173 | xargs kill -9"
echo ""
