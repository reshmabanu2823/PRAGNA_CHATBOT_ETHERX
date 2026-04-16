#!/bin/bash
# ===================================================================
# EtherXChatBot Backend - Production Startup Script
# ===================================================================
# This script ensures the backend is properly initialized before running
# Usage: bash scripts/startup.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}EtherXChatBot Backend - Startup${NC}"
echo -e "${YELLOW}========================================${NC}"

# ===========================
# 1. Check Python Version
# ===========================
echo -e "\n${YELLOW}[1/5] Checking Python version...${NC}"
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.11"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo -e "${RED}❌ Python 3.11+ required, found: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python version: $PYTHON_VERSION${NC}"

# ===========================
# 2. Check Virtual Environment
# ===========================
echo -e "\n${YELLOW}[2/5] Checking virtual environment...${NC}"
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python -m venv venv
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
fi

# ===========================
# 3. Install Dependencies
# ===========================
echo -e "\n${YELLOW}[3/5] Installing dependencies...${NC}"
if pip install -r requirements.txt; then
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install dependencies${NC}"
    exit 1
fi

# ===========================
# 4. Check Configuration
# ===========================
echo -e "\n${YELLOW}[4/5] Checking configuration...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}Copying .env.example to .env${NC}"
        cp .env.example .env
        echo -e "${YELLOW}⚠️  Edit .env with your configuration!${NC}"
    else
        echo -e "${RED}❌ .env.example not found${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✅ Configuration file exists${NC}"

# ===========================
# 5. Validate API Configuration
# ===========================
echo -e "\n${YELLOW}[5/5] Validating API configuration...${NC}"
python -c "
import config
print(f'✅ LLM Provider: {config.LLM_PROVIDER}')
print(f'✅ Ollama Enabled: {config.OLLAMA_ENABLED}')
print(f'✅ Debug Mode: {config.DEBUG}')
print(f'✅ Development Mode: {config.DEVELOPMENT_MODE}')
" || {
    echo -e "${RED}❌ Configuration validation failed${NC}"
    exit 1
}

# ===========================
# 6. Ready to Run
# ===========================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Backend Ready to Start!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}To start the backend:${NC}"
echo ""
echo -e "${GREEN}Development (Flask built-in):${NC}"
echo "  python app.py"
echo ""
echo -e "${GREEN}Production (Gunicorn):${NC}"
echo "  gunicorn -c gunicorn_config.py wsgi:app"
echo ""
echo -e "${YELLOW}To test the backend:${NC}"
echo "  curl http://localhost:5001/api/health | jq ."
echo "  curl -X POST http://localhost:5001/api/test-ollama | jq ."
echo ""
