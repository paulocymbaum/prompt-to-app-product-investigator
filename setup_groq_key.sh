#!/bin/bash

echo "🔑 Groq API Key Setup Helper"
echo "============================"
echo ""

cd "$(dirname "$0")/backend"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "This script will help you configure your Groq API key."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo ""
fi

# Get current key
CURRENT_KEY=$(grep "^GROQ_API_KEY=" .env | cut -d '=' -f2 | tr -d "'\"")

if [ -n "$CURRENT_KEY" ] && [ "$CURRENT_KEY" != "your-groq-api-key-here" ]; then
    echo -e "${BLUE}ℹ️  You already have a Groq API key configured.${NC}"
    echo ""
    echo "Options:"
    echo "  1. Keep current key"
    echo "  2. Replace with new key"
    echo "  3. View configuration status"
    echo ""
    read -p "Choose (1-3): " choice
    
    case $choice in
        1)
            echo -e "${GREEN}✓ Keeping current configuration${NC}"
            ./validate_env.sh
            exit 0
            ;;
        2)
            echo "Proceeding to replace key..."
            ;;
        3)
            ./validate_env.sh
            exit 0
            ;;
        *)
            echo "Invalid choice. Exiting."
            exit 1
            ;;
    esac
fi

echo ""
echo "📝 Steps to get your Groq API key:"
echo "   1. Go to: https://console.groq.com/keys"
echo "   2. Sign up or log in (free, no credit card)"
echo "   3. Click 'Create API Key'"
echo "   4. Copy the key (starts with 'gsk_')"
echo ""

read -p "Do you have your Groq API key ready? (y/n): " has_key

if [ "$has_key" != "y" ] && [ "$has_key" != "Y" ]; then
    echo ""
    echo -e "${YELLOW}Please get your API key first:${NC}"
    echo "   → https://console.groq.com/keys"
    echo ""
    echo "Then run this script again: ./setup_groq_key.sh"
    exit 0
fi

echo ""
read -p "Paste your Groq API key (starts with gsk_): " api_key

# Validate format
if [[ ! $api_key == gsk_* ]]; then
    echo ""
    echo -e "${RED}❌ Invalid key format!${NC}"
    echo "   Groq API keys must start with 'gsk_'"
    echo "   Please check your key and try again."
    exit 1
fi

# Validate length
if [ ${#api_key} -lt 30 ]; then
    echo ""
    echo -e "${RED}❌ Key seems too short!${NC}"
    echo "   Groq API keys are typically longer than 30 characters."
    echo "   Please make sure you copied the complete key."
    exit 1
fi

echo ""
echo -e "${BLUE}Saving your API key...${NC}"

# Update .env file
if grep -q "^GROQ_API_KEY=" .env; then
    # Key exists, update it
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^GROQ_API_KEY=.*|GROQ_API_KEY=$api_key|" .env
    else
        # Linux
        sed -i "s|^GROQ_API_KEY=.*|GROQ_API_KEY=$api_key|" .env
    fi
else
    # Key doesn't exist, add it
    echo "GROQ_API_KEY=$api_key" >> .env
fi

# Set active provider
if grep -q "^ACTIVE_PROVIDER=" .env; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^ACTIVE_PROVIDER=.*|ACTIVE_PROVIDER=groq|" .env
    else
        sed -i "s|^ACTIVE_PROVIDER=.*|ACTIVE_PROVIDER=groq|" .env
    fi
else
    echo "ACTIVE_PROVIDER=groq" >> .env
fi

# Set default model
if grep -q "^GROQ_SELECTED_MODEL=" .env; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^GROQ_SELECTED_MODEL=.*|GROQ_SELECTED_MODEL=llama-3.3-70b-versatile|" .env
    else
        sed -i "s|^GROQ_SELECTED_MODEL=.*|GROQ_SELECTED_MODEL=llama-3.3-70b-versatile|" .env
    fi
else
    echo "GROQ_SELECTED_MODEL=llama-3.3-70b-versatile" >> .env
fi

echo -e "${GREEN}✓ API key saved successfully!${NC}"
echo ""

# Validate configuration
echo -e "${BLUE}Validating configuration...${NC}"
echo ""

if ./validate_env.sh; then
    echo ""
    echo "=========================================="
    echo -e "${GREEN}✅ Configuration Complete!${NC}"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Start the backend:"
    echo "   ${YELLOW}python -m uvicorn app:app --reload${NC}"
    echo ""
    echo "2. Start the frontend (in another terminal):"
    echo "   ${YELLOW}cd ../frontend && npm run dev${NC}"
    echo ""
    echo "3. Open your browser:"
    echo "   ${YELLOW}http://localhost:5173${NC}"
    echo ""
    echo "4. Start investigating!"
    echo ""
    echo "Or test the integration first:"
    echo "   ${YELLOW}./test_groq_integration.sh${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}⚠️  Configuration validation failed.${NC}"
    echo "Please check the errors above and try again."
    exit 1
fi
