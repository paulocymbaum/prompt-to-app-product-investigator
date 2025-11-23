#!/bin/bash

# Test Script for Epic 1: Project Setup & Infrastructure
# This script tests TASK-1.1 and TASK-1.2

echo "=========================================="
echo "Testing Epic 1: Project Setup & Infrastructure"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to print test result
print_result() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

echo "=========================================="
echo "TASK-1.1: Backend Project Structure"
echo "=========================================="
echo ""

# Test 1: Check if backend directory exists
test -d backend
print_result $? "Backend directory exists"

# Test 2: Check if requirements.txt exists
test -f backend/requirements.txt
print_result $? "requirements.txt exists"

# Test 3: Check if app.py exists
test -f backend/app.py
print_result $? "app.py exists"

# Test 4: Check if .env.example exists
test -f backend/.env.example
print_result $? ".env.example exists"

# Test 5: Check if .env exists
test -f backend/.env
print_result $? ".env file created"

# Test 6: Check if Dockerfile exists
test -f backend/Dockerfile
print_result $? "Dockerfile exists"

# Test 7: Check if docker-compose.yml exists
test -f backend/docker-compose.yml
print_result $? "docker-compose.yml exists"

# Test 8: Check if README exists
test -f backend/README.md
print_result $? "README.md exists"

# Test 9: Check models directory
test -d backend/models
print_result $? "models/ directory exists"

# Test 10: Check services directory
test -d backend/services
print_result $? "services/ directory exists"

# Test 11: Check routes directory
test -d backend/routes
print_result $? "routes/ directory exists"

# Test 12: Check utils directory
test -d backend/utils
print_result $? "utils/ directory exists"

# Test 13: Check tests directory
test -d backend/tests
print_result $? "tests/ directory exists"

# Test 14: Check if data directories are created
test -d backend/data
print_result $? "data/ directory exists or will be created on startup"

# Test 15: Check if FastAPI imports work
cd backend
../.venv/bin/python -c "import app; print('FastAPI imports successfully')" > /dev/null 2>&1
print_result $? "FastAPI application imports successfully"
cd ..

# Test 16: Check if Pydantic models import
cd backend
../.venv/bin/python -c "from models.conversation import Message, Question, Session; from models.provider import Provider, Model; print('Models import successfully')" > /dev/null 2>&1
print_result $? "Pydantic models import successfully"
cd ..

echo ""
echo "=========================================="
echo "TASK-1.2: Frontend Project Structure"
echo "=========================================="
echo ""

# Test 17: Check if frontend directory exists
test -d frontend
print_result $? "Frontend directory exists"

# Test 18: Check if package.json exists
test -f frontend/package.json
print_result $? "package.json exists"

# Test 19: Check if vite.config.js exists
test -f frontend/vite.config.js
print_result $? "vite.config.js exists"

# Test 20: Check if tailwind.config.js exists
test -f frontend/tailwind.config.js
print_result $? "tailwind.config.js exists"

# Test 21: Check if postcss.config.js exists
test -f frontend/postcss.config.js
print_result $? "postcss.config.js exists"

# Test 22: Check if .env.example exists
test -f frontend/.env.example
print_result $? ".env.example exists"

# Test 23: Check if .env exists
test -f frontend/.env
print_result $? ".env file created"

# Test 24: Check if App.jsx exists
test -f frontend/src/App.jsx
print_result $? "App.jsx exists"

# Test 25: Check if api service exists
test -f frontend/src/services/api.js
print_result $? "API service layer exists"

# Test 26: Check if Tailwind directives are in index.css
grep -q "@tailwind base" frontend/src/index.css
print_result $? "Tailwind CSS configured in index.css"

# Test 27: Check if node_modules exists (dependencies installed)
test -d frontend/node_modules
print_result $? "Frontend dependencies installed"

# Test 28: Check if key dependencies are in package.json
grep -q "\"react\"" frontend/package.json && grep -q "\"tailwindcss\"" frontend/package.json && grep -q "\"axios\"" frontend/package.json
print_result $? "Key dependencies (React, Tailwind, Axios) in package.json"

echo ""
echo "=========================================="
echo "Integration Tests"
echo "=========================================="
echo ""

# Test 29: Check if virtual environment exists
test -d .venv
print_result $? "Python virtual environment exists"

# Test 30: Check if Python packages are installed
../.venv/bin/python -c "import fastapi, langchain, cryptography, pytest" > /dev/null 2>&1
cd backend
print_result $? "Core Python packages installed"
cd ..

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "✓ All tests passed!"
    echo "Epic 1 implementation is complete."
    echo "==========================================${NC}"
    exit 0
else
    echo -e "${RED}=========================================="
    echo "✗ Some tests failed."
    echo "Please review the failures above."
    echo "==========================================${NC}"
    exit 1
fi
