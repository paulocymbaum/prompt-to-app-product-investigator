#!/bin/bash

# Frontend API Path Verification Script
# Checks that frontend is calling the correct backend endpoints

echo "=========================================="
echo "🔍 VERIFYING FRONTEND API PATHS"
echo "=========================================="
echo ""

FRONTEND_DIR="/Users/paulocymbaum/lovable_prompt_generator/frontend/src"

echo "Searching for API endpoint calls in frontend..."
echo ""

# Find all /api/ references
echo "=== All /api/ references found in frontend code ==="
grep -r "/api/" "$FRONTEND_DIR" --include="*.js" --include="*.jsx" --include="*.ts" --include="*.tsx" -n | head -50

echo ""
echo "=========================================="
echo "📋 EXPECTED API PATHS (Backend)"
echo "=========================================="
echo ""
echo "Config Routes:"
echo "  - POST /api/config/token"
echo "  - GET  /api/config/models"
echo "  - POST /api/config/model/select"
echo "  - GET  /api/config/status"
echo "  - DELETE /api/config/token/{provider}"
echo ""
echo "Chat Routes:"
echo "  - POST /api/chat/start"
echo "  - POST /api/chat/message"
echo "  - GET  /api/chat/history/{session_id}"
echo "  - GET  /api/chat/status/{session_id}"
echo ""
echo "Session Routes:"
echo "  - GET  /api/session/list"
echo "  - POST /api/session/save"
echo "  - GET  /api/session/load/{session_id}"
echo "  - GET  /api/session/{session_id}"
echo "  - DELETE /api/session/{session_id}"
echo ""
echo "Prompt Routes:"
echo "  - GET  /api/prompt/generate/{session_id}"
echo "  - GET  /api/prompt/download/{session_id}"
echo "  - POST /api/prompt/regenerate/{session_id}"
echo ""
echo "Graph Routes:"
echo "  - GET  /api/graph/{session_id}"
echo "  - GET  /api/graph/viewer/{session_id}"
echo ""
echo "Export Routes:"
echo "  - GET  /api/export/markdown/{session_id}"
echo "  - GET  /api/export/html/{session_id}"
echo "  - GET  /api/export/pdf/{session_id}"
echo ""

echo "=========================================="
echo "✅ Verification Complete"
echo "=========================================="
echo ""
echo "Check that frontend calls match the expected paths above."
