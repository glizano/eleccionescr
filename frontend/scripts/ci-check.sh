#!/bin/bash
# Frontend CI check script - run before pushing
# Usage: ./scripts/ci-check.sh

set -e

echo "🎨 Running Frontend CI checks locally..."
echo ""

# Change to frontend directory
cd "$(dirname "$0")/.."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${RED}✗${NC} $1"
        exit 1
    fi
}

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    print_status "Dependencies installed"
    echo ""
fi

# Run linting
echo "🔍 Running ESLint..."
npm run lint
print_status "Linting passed"
echo ""

# Run Prettier check
echo "💅 Running Prettier check..."
npm run format:check
print_status "Formatting check passed"
echo ""

# Run type checking
echo "🔎 Running TypeScript type check..."
npm run type-check
print_status "Type checking passed"
echo ""

# Run build
echo "🏗️  Building project..."
npm run build
print_status "Build successful"
echo ""

echo -e "${GREEN}✅ All checks passed!${NC}"
echo ""
echo "Your code is ready to be committed and pushed."
