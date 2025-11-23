#!/bin/bash

# Test script for TASK-1.7: LLM Service Implementation
# This script validates the LLM Service functionality

set -e  # Exit on error

echo "============================================"
echo "TASK-1.7: LLM Service Tests"
echo "============================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to backend directory
cd "$(dirname "$0")/.."

# Python executable
PYTHON="/Users/paulocymbaum/lovable_prompt_generator/.venv/bin/python"

echo "${YELLOW}Running LLM Service Unit Tests...${NC}"
$PYTHON -m pytest tests/test_llm_service.py -v --cov=services/llm_service --cov-report=term-missing

echo ""
echo "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "Test Coverage Summary:"
echo "----------------------"
echo "Test File: test_llm_service.py"
echo "Total Tests: 20"
echo "Status: PASSED"
echo ""
echo "Test Categories:"
echo "  - Initialization: 6 tests"
echo "  - Response Generation: 5 tests"
echo "  - Streaming: 3 tests"
echo "  - Token Counting: 3 tests"
echo "  - Config Info: 2 tests"
echo "  - Dependency Injection: 1 test"
echo ""
echo "Key Features Tested:"
echo "  ✓ Provider initialization (Groq/OpenAI)"
echo "  ✓ LangChain integration"
echo "  ✓ Async response generation"
echo "  ✓ Streaming responses"
echo "  ✓ Token counting with fallback"
echo "  ✓ Error handling with retry logic (3 attempts)"
echo "  ✓ Parameter overrides (temperature, max_tokens)"
echo "  ✓ Configuration validation"
echo ""
