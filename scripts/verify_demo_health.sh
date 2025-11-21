#!/bin/bash
# Health check script for COMPASS demo environment
# Verifies all services are running before manual testing

set -e

echo "🔍 COMPASS Demo Environment Health Check"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

# Function to check service health
check_service() {
    local service=$1
    local url=$2
    local expected=$3

    echo -n "Checking $service... "

    if response=$(curl -s -f "$url" 2>&1); then
        if [[ "$response" == *"$expected"* ]]; then
            echo -e "${GREEN}✅ OK${NC}"
            return 0
        else
            echo -e "${RED}❌ FAIL${NC} (unexpected response)"
            echo "  Expected: $expected"
            echo "  Got: $response"
            FAILED=$((FAILED + 1))
            return 1
        fi
    else
        echo -e "${RED}❌ FAIL${NC} (not responding)"
        echo "  URL: $url"
        echo "  Error: $response"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Check Docker Compose services are up
echo "1. Checking Docker Compose services..."
echo ""

if docker-compose -f docker-compose.observability.yml ps --format json > /dev/null 2>&1; then
    # Count running services
    RUNNING=$(docker-compose -f docker-compose.observability.yml ps --format json | jq -r '. | select(.State=="running") | .Name' | wc -l | tr -d ' ')
    TOTAL=$(docker-compose -f docker-compose.observability.yml ps --format json | jq -r '.Name' | wc -l | tr -d ' ')

    if [ "$RUNNING" -eq "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
        echo -e "${GREEN}✅ All $RUNNING services running${NC}"
    else
        echo -e "${YELLOW}⚠️  Only $RUNNING/$TOTAL services running${NC}"
        echo ""
        echo "Service status:"
        docker-compose -f docker-compose.observability.yml ps
        echo ""
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${RED}❌ FAIL${NC} - Cannot read docker-compose status"
    echo "  Run: docker-compose -f docker-compose.observability.yml up -d"
    exit 1
fi

echo ""
echo "2. Checking service endpoints..."
echo ""

# Check each service
check_service "Sample App" "http://localhost:8000/health" "healthy"
check_service "Grafana" "http://localhost:3000/api/health" "ok"
check_service "Loki" "http://localhost:3100/ready" "ready"
check_service "Prometheus" "http://localhost:9090/-/ready" "Prometheus Server is Ready"

# Tempo doesn't have a simple ready endpoint, check if port responds
echo -n "Checking Tempo... "
if nc -z localhost 3200 2>/dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAIL${NC} (port 3200 not responding)"
    FAILED=$((FAILED + 1))
fi

# Check Postgres
echo -n "Checking Postgres... "
if nc -z localhost 5432 2>/dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAIL${NC} (port 5432 not responding)"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "3. Checking critical ports available..."
echo ""

# Check no port conflicts
PORTS=(3000 3100 3200 4317 5432 8000 9090)
CONFLICTS=0

for port in "${PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} Port $port in use (expected)"
    else
        echo -e "${YELLOW}⚠️${NC}  Port $port not in use (service may not be running)"
        CONFLICTS=$((CONFLICTS + 1))
    fi
done

if [ $CONFLICTS -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  $CONFLICTS ports not in use - some services may not be running${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "=========================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All health checks passed!${NC}"
    echo ""
    echo "Demo environment is ready for testing."
    echo ""
    echo "Next steps:"
    echo "  1. Configure LLM provider: cp .env.example .env && nano .env"
    echo "  2. Run investigation: poetry run compass investigate INC-001 --budget 10.00 --affected-services payment-service --severity high"
    exit 0
else
    echo -e "${RED}❌ $FAILED health check(s) failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  - Check logs: docker-compose -f docker-compose.observability.yml logs"
    echo "  - Restart services: docker-compose -f docker-compose.observability.yml restart"
    echo "  - Full restart: docker-compose -f docker-compose.observability.yml down && docker-compose -f docker-compose.observability.yml up -d"
    echo ""
    echo "For more help, see TROUBLESHOOTING.md"
    exit 1
fi
