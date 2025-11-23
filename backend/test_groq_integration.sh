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
