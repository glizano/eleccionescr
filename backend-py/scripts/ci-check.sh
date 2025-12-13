#!/bin/bash
# Script para ejecutar checks de CI localmente antes de hacer push
# Uso: ./scripts/ci-check.sh [--fix]
#   --fix: Auto-fix linting and formatting issues when possible

set -e  # Exit on error

# Parse arguments
FIX_MODE=false
if [[ "$1" == "--fix" ]]; then
    FIX_MODE=true
    echo "🔧 Running in FIX mode - will auto-fix issues when possible"
fi

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

# 1. Ruff linting
echo -e "${YELLOW}📝 Running ruff linter...${NC}"
if [ "$FIX_MODE" = true ]; then
    uv run ruff check --fix .
else
    uv run ruff check .
fi
print_status "Linting"

# 2. Ruff formatting (apply)
echo ""
echo -e "${YELLOW}🎨 Applying code formatting...${NC}"
uv run ruff format .
print_status "Formatting"

# 3. Bandit security check
echo ""
echo -e "${YELLOW}🔒 Running security checks (bandit)...${NC}"
uv pip install bandit[toml]
# Skip B110 (try-except-pass in retry logic) and B104 (bind to 0.0.0.0 for Docker)
uv run bandit --skip B110,B104 -r app/ || echo "⚠️  Bandit warnings (non-blocking)"

# 4. Run tests
echo ""
echo -e "${YELLOW}🧪 Running tests...${NC}"

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
