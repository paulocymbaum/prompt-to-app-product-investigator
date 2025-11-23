#!/bin/bash

# Chat Routes API Test Script
# Tests all chat endpoints with curl commands

BASE_URL="http://localhost:8000/api/chat"
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Chat Routes API Test Script${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Test 1: Start Investigation (Default Provider)
echo -e "${BLUE}Test 1: POST /api/chat/start (default provider)${NC}"
RESPONSE=$(curl -s -X POST "$BASE_URL/start" \
  -H "Content-Type: application/json" \
  -d '{}')

echo "$RESPONSE" | python3 -m json.tool
SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null)

if [ -n "$SESSION_ID" ]; then
  echo -e "${GREEN}✓ Start investigation successful. Session ID: $SESSION_ID${NC}\n"
else
  echo -e "${RED}✗ Failed to start investigation${NC}\n"
  exit 1
fi

# Test 2: Start Investigation (Specific Provider)
echo -e "${BLUE}Test 2: POST /api/chat/start (with provider config)${NC}"
RESPONSE2=$(curl -s -X POST "$BASE_URL/start" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "groq",
    "model_id": "llama2-70b-4096"
  }')

echo "$RESPONSE2" | python3 -m json.tool
SESSION_ID2=$(echo "$RESPONSE2" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null)

if [ -n "$SESSION_ID2" ]; then
  echo -e "${GREEN}✓ Start investigation with provider successful. Session ID: $SESSION_ID2${NC}\n"
else
  echo -e "${RED}✗ Failed to start investigation with provider${NC}\n"
fi

# Test 3: Send Message
echo -e "${BLUE}Test 3: POST /api/chat/message${NC}"
RESPONSE3=$(curl -s -X POST "$BASE_URL/message" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"message\": \"I want to build a task management application for remote teams.\"
  }")

echo "$RESPONSE3" | python3 -m json.tool

if echo "$RESPONSE3" | grep -q '"complete"'; then
  echo -e "${GREEN}✓ Send message successful${NC}\n"
else
  echo -e "${RED}✗ Failed to send message${NC}\n"
fi

# Test 4: Get Conversation History
echo -e "${BLUE}Test 4: GET /api/chat/history/${SESSION_ID}${NC}"
RESPONSE4=$(curl -s -X GET "$BASE_URL/history/$SESSION_ID")

echo "$RESPONSE4" | python3 -m json.tool

if echo "$RESPONSE4" | grep -q '"messages"'; then
  echo -e "${GREEN}✓ Get history successful${NC}\n"
else
  echo -e "${RED}✗ Failed to get history${NC}\n"
fi

# Test 5: Get Session Status
echo -e "${BLUE}Test 5: GET /api/chat/status/${SESSION_ID}${NC}"
RESPONSE5=$(curl -s -X GET "$BASE_URL/status/$SESSION_ID")

echo "$RESPONSE5" | python3 -m json.tool

if echo "$RESPONSE5" | grep -q '"exists"'; then
  echo -e "${GREEN}✓ Get session status successful${NC}\n"
else
  echo -e "${RED}✗ Failed to get session status${NC}\n"
fi

# Test 6: Get Status for Non-existent Session
echo -e "${BLUE}Test 6: GET /api/chat/status/invalid-session-id${NC}"
RESPONSE6=$(curl -s -X GET "$BASE_URL/status/invalid-session-id")

echo "$RESPONSE6" | python3 -m json.tool

if echo "$RESPONSE6" | grep -q '"exists": false'; then
  echo -e "${GREEN}✓ Non-existent session check successful${NC}\n"
else
  echo -e "${RED}✗ Failed non-existent session check${NC}\n"
fi

# Test 7: Send Message to Non-existent Session
echo -e "${BLUE}Test 7: POST /api/chat/message (invalid session)${NC}"
RESPONSE7=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$BASE_URL/message" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "invalid-session",
    "message": "This should fail"
  }')

BODY=$(echo "$RESPONSE7" | sed -e 's/HTTP_STATUS\:.*//g')
STATUS=$(echo "$RESPONSE7" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"

if [ "$STATUS" = "404" ]; then
  echo -e "${GREEN}✓ Invalid session correctly returned 404${NC}\n"
else
  echo -e "${RED}✗ Expected 404, got $STATUS${NC}\n"
fi

# Test 8: Validation Error Test (missing required field)
echo -e "${BLUE}Test 8: POST /api/chat/message (validation error)${NC}"
RESPONSE8=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$BASE_URL/message" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session"
  }')

BODY=$(echo "$RESPONSE8" | sed -e 's/HTTP_STATUS\:.*//g')
STATUS=$(echo "$RESPONSE8" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"

if [ "$STATUS" = "422" ]; then
  echo -e "${GREEN}✓ Validation error correctly returned 422${NC}\n"
else
  echo -e "${RED}✗ Expected 422, got $STATUS${NC}\n"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}WebSocket Test Instructions${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "To test WebSocket endpoint, use a WebSocket client like 'websocat':"
echo -e "  ${GREEN}websocat ws://localhost:8000/api/chat/ws/$SESSION_ID${NC}"
echo -e "\nOr use JavaScript in the browser console:"
echo -e "  ${GREEN}const ws = new WebSocket('ws://localhost:8000/api/chat/ws/$SESSION_ID');${NC}"
echo -e "  ${GREEN}ws.onmessage = (e) => console.log(JSON.parse(e.data));${NC}"
echo -e "  ${GREEN}ws.send(JSON.stringify({message: 'Hello'}));${NC}\n"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}All REST API Tests Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
