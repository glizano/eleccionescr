#!/bin/bash
# Script para ejecutar checks de CI localmente antes de hacer push
# Uso: ./scripts/ci-check.sh

set -e  # Exit on error

echo "🔍 Running CI checks locally..."
echo ""

# Change to backend-py directory
cd "$(dirname "$0")/.."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1 passed${NC}"
    else
        echo -e "${RED}❌ $1 failed${NC}"
        exit 1
    fi
}

# 1. Lint check
echo -e "${YELLOW}📝 Running ruff linter...${NC}"
uv run ruff check .
print_status "Linting"

# 2. Format check
echo ""
echo -e "${YELLOW}🎨 Checking code formatting...${NC}"
uv run ruff format --check .
print_status "Format check"

# 3. Type checking (optional, if you add mypy)
# echo ""
# echo -e "${YELLOW}🔍 Running type checker...${NC}"
# uv run mypy app/
# print_status "Type checking"

# 4. Run tests
echo ""
echo -e "${YELLOW}🧪 Running tests...${NC}"

# Check if Qdrant is running
if ! curl -s http://localhost:6333/health > /dev/null 2>&1; then
    echo -e "${RED}⚠️  Qdrant is not running!${NC}"
    echo "Start it with: docker run -p 6333:6333 qdrant/qdrant"
    exit 1
fi

uv run pytest tests/ -v
print_status "Tests"

# 5. Import validation
echo ""
echo -e "${YELLOW}📦 Validating imports...${NC}"
uv run python -c "from app.main import app; print('Imports OK')"
print_status "Import validation"

# 6. Dependency check
echo ""
echo -e "${YELLOW}📋 Checking dependencies...${NC}"
uv pip check
print_status "Dependency check"

echo ""
echo -e "${GREEN}🎉 All checks passed! Ready to push.${NC}"
