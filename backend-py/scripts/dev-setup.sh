#!/bin/bash
# Quick setup script for security and development tools
# Run this after cloning the repository

set -e

echo "🔧 EleccionesCR - Development Setup"
echo "===================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from backend-py directory"
    exit 1
fi

# Install pre-commit
echo "📦 Installing pre-commit..."
if ! command -v pre-commit &> /dev/null; then
    pip install pre-commit
fi

# Install pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
cd .. && pre-commit install && cd backend-py

# Run pre-commit on all files (optional, but recommended)
read -r -p "🔍 Run pre-commit checks on all files? (y/N) " REPLY
echo
if [ "$REPLY" = "y" ] || [ "$REPLY" = "Y" ]; then
    cd .. && pre-commit run --all-files && cd backend-py
fi

# Install development dependencies
echo "📚 Installing development dependencies..."
uv sync

# Install security tools
echo "🔒 Installing security scanning tools..."
uv pip install bandit[toml] safety pip-audit

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Copy .env.example to .env and fill in your API keys"
echo "  2. Run tests: uv run pytest tests/ -v"
echo "  3. Start development: uv run uvicorn app.main:app --reload"
echo ""
echo "🔐 Security tools installed:"
echo "  - Pre-commit hooks (runs automatically on git commit)"
echo "  - Bandit (Python security linter)"
echo "  - Safety (dependency vulnerability scanner)"
echo "  - pip-audit (alternative dependency scanner)"
echo ""
echo "🧪 Run security checks manually:"
echo "  ./scripts/ci-check.sh          # Full CI checks"
echo "  uv run bandit -r app/          # Security linting"
echo "  uv run safety check            # Dependency vulnerabilities"
echo "  uv run pip-audit               # Dependency security audit"
echo ""
