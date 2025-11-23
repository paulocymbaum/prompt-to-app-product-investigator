#!/bin/bash

# Comprehensive API Endpoint Test Script
# Tests all backend endpoints to ensure routes are properly configured

echo "=========================================="
echo "🧪 TESTING ALL API ENDPOINTS"
echo "=========================================="
echo ""

BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:5173"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASS=0
FAIL=0

# Test function
test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected_status=$3
    local description=$4
    
    echo -n "Testing: $description... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL$endpoint")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{}' "$BACKEND_URL$endpoint")
    fi
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $response)"
        ((PASS++))
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_status, got $response)"
        ((FAIL++))
    fi
}

echo "=== Core Health Endpoints ==="
test_endpoint "GET" "/health" "200" "Health check"
test_endpoint "GET" "/" "200" "Root endpoint"
echo ""

echo "=== Config Routes (should be /api/config/*) ==="
test_endpoint "GET" "/api/config" "405" "Config root (GET not allowed)"
test_endpoint "GET" "/api/config/status" "200" "Get config status"
test_endpoint "GET" "/api/config/models" "422" "Get models (missing params)"
echo ""

echo "=== Chat Routes (should be /api/chat/*) ==="
test_endpoint "POST" "/api/chat/start" "422" "Start chat (missing data)"
test_endpoint "POST" "/api/chat/message" "422" "Send message (missing data)"
echo ""

echo "=== Session Routes (should be /api/session/*) ==="
test_endpoint "GET" "/api/session/list" "200" "List sessions"
test_endpoint "POST" "/api/session/save" "422" "Save session (missing data)"
echo ""

echo "=== Prompt Routes (should be /api/prompt/*) ==="
test_endpoint "GET" "/api/prompt/generate/test-session" "404" "Generate prompt (session not found)"
echo ""

echo "=== Graph Routes (should be /api/graph/*) ==="
test_endpoint "GET" "/api/graph/test-session" "404" "Get graph (session not found)"
echo ""

echo "=== Graph Viewer Routes (should be /api/graph/viewer/*) ==="
test_endpoint "GET" "/api/graph/viewer/test-session" "404" "Get graph viewer (session not found)"
echo ""

echo "=== Export Routes (should be /api/export/*) ==="
test_endpoint "GET" "/api/export/markdown/test-session" "404" "Export markdown (session not found)"
echo ""

echo ""
echo "=========================================="
echo "📊 TEST RESULTS"
echo "=========================================="
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check routes configuration.${NC}"
    exit 1
fi
