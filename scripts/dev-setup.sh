#!/bin/bash
set -e

echo "🚀 COMPASS Development Environment Setup"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Python 3.11+
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3.11+ required but not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✅ Python found: $PYTHON_VERSION${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker not found. Development services won't be available.${NC}"
else
    echo -e "${GREEN}✅ Docker found${NC}"
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker Compose not found. Development services won't be available.${NC}"
else
    echo -e "${GREEN}✅ Docker Compose found${NC}"
fi

echo ""

# Install Poetry if not present
if ! command -v poetry &> /dev/null; then
    echo "📦 Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
    echo -e "${GREEN}✅ Poetry installed${NC}"
else
    echo -e "${GREEN}✅ Poetry already installed${NC}"
fi

echo ""

# Install dependencies
echo "📦 Installing Python dependencies..."
poetry install
echo -e "${GREEN}✅ Dependencies installed${NC}"

echo ""

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
poetry run pre-commit install --hook-type pre-commit --hook-type commit-msg
echo -e "${GREEN}✅ Pre-commit hooks installed${NC}"

echo ""

# Start Docker services if available
if command -v docker-compose &> /dev/null; then
    echo "🐳 Starting Docker services..."
    docker-compose -f docker-compose.dev.yml up -d

    # Wait for services to be healthy
    echo "⏳ Waiting for services to be healthy..."
    timeout 60 bash -c 'until docker-compose -f docker-compose.dev.yml ps | grep -q "healthy" 2>/dev/null; do sleep 2; done' || echo -e "${YELLOW}⚠️  Some services may not be healthy${NC}"

    echo -e "${GREEN}✅ Docker services started${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping Docker services (Docker Compose not available)${NC}"
fi

echo ""

# Run database migrations (when they exist)
# echo "🗄️ Running database migrations..."
# poetry run alembic upgrade head

echo ""
echo -e "${GREEN}✅ Development environment ready!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Quick commands:"
echo "  make help          # Show all available commands"
echo "  make test          # Run all tests"
echo "  make ci-local      # Simulate CI locally"
echo "  make validate-all  # Run everything before push"
echo "  make dev-down      # Stop Docker services"
echo "  make dev-logs      # View Docker logs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 Documentation: docs/"
echo "🐛 Issues: https://github.com/IvanMerrill/compass/issues"
echo ""
