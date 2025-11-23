#!/bin/bash

# Script to run GraphService tests

cd /Users/paulocymbaum/lovable_prompt_generator/backend

echo "Running GraphService tests..."
echo ""

/Users/paulocymbaum/lovable_prompt_generator/.venv/bin/python -m pytest \
    tests/test_graph_service.py \
    -v \
    --cov=services.graph_service \
    --cov-report=term-missing \
    --tb=short \
    -x

echo ""
echo "Test execution complete!"
