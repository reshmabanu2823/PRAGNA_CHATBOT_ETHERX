#!/bin/bash
# ===================================================================
# EtherXChatBot Backend - Health Check Script
# ===================================================================
# This script verifies the backend is running correctly
# Usage: bash scripts/health-check.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_URL="${BACKEND_URL:-http://localhost:5001}"
TIMEOUT=5
EXIT_CODE=0

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}EtherXChatBot Health Check${NC}"
echo -e "${BLUE}Backend URL: $BACKEND_URL${NC}"
echo -e "${BLUE}========================================${NC}"

# ===========================
# Function: Check Health
# ===========================
check_health() {
    local endpoint="$1"
    local description="$2"
    
    echo -n "Checking $description... "
    
    if response=$(curl -s -f -m $TIMEOUT "$BACKEND_URL$endpoint" 2>/dev/null); then
        echo -e "${GREEN}✅${NC}"
        return 0
    else
        echo -e "${RED}❌${NC}"
        return 1
    fi
}

# ===========================
# Check Endpoints
# ===========================
echo ""
echo -e "${YELLOW}Endpoint Checks:${NC}"

check_health "/api/health" "General health" || EXIT_CODE=1
check_health "/api/test-ollama" "Ollama integration" || EXIT_CODE=1
check_health "/api/models/catalog" "Models endpoint" || EXIT_CODE=1

# ===========================
# Check Ollama Connection
# ===========================
echo ""
echo -e "${YELLOW}Ollama Connection:${NC}"
echo -n "Checking Ollama availability... "

if response=$(curl -s -f -m $TIMEOUT "http://localhost:11434/api/tags" 2>/dev/null); then
    echo -e "${GREEN}✅${NC}"
    MODEL_COUNT=$(echo "$response" | jq '.models | length' 2>/dev/null || echo 0)
    echo "  Models available: $MODEL_COUNT"
else
    echo -e "${RED}❌${NC}"
    echo "  ${RED}Ollama not reachable at http://localhost:11434${NC}"
    EXIT_CODE=1
fi

# ===========================
# Detailed Status
# ===========================
echo ""
echo -e "${YELLOW}Detailed Status:${NC}"

if response=$(curl -s -f -m $TIMEOUT "$BACKEND_URL/api/health" 2>/dev/null); then
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
else
    echo -e "${RED}Could not retrieve detailed status${NC}"
    EXIT_CODE=1
fi

# ===========================
# Summary
# ===========================
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}⚠️  Some checks failed${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "1. Verify backend is running: curl $BACKEND_URL/api/health"
    echo "2. Verify Ollama is running: ollama serve"
    echo "3. Check logs: docker-compose logs backend"
    echo "4. Test Ollama directly: curl http://localhost:11434/api/tags"
    echo ""
fi

exit $EXIT_CODE
