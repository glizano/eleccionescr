#!/bin/bash
# Master CI check script - runs all project checks
# Usage: ./scripts/ci-check.sh

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         EleccionesCR 2026 - Full CI Check                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

FAILED=0

# Backend checks
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🐍 BACKEND CHECKS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "backend-py/scripts/ci-check.sh" ]; then
    if bash backend-py/scripts/ci-check.sh; then
        echo -e "\n${GREEN}✅ Backend checks passed${NC}\n"
    else
        echo -e "\n${RED}❌ Backend checks failed${NC}\n"
        FAILED=1
    fi
else
    echo -e "${RED}❌ Backend ci-check script not found${NC}\n"
    FAILED=1
fi

# Frontend checks
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🎨 FRONTEND CHECKS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "frontend/scripts/ci-check.sh" ]; then
    if bash frontend/scripts/ci-check.sh; then
        echo -e "\n${GREEN}✅ Frontend checks passed${NC}\n"
    else
        echo -e "\n${RED}❌ Frontend checks failed${NC}\n"
        FAILED=1
    fi
else
    echo -e "${RED}❌ Frontend ci-check script not found${NC}\n"
    FAILED=1
fi

# Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ ALL CHECKS PASSED - Ready to commit and push!            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ❌ SOME CHECKS FAILED - Fix errors before committing         ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
