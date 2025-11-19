#!/usr/bin/env bash
# COMPASS Demo Environment Launcher
#
# Usage:
#   ./scripts/run-demo.sh          # Start demo environment
#   ./scripts/run-demo.sh stop     # Stop demo environment
#   ./scripts/run-demo.sh restart  # Restart demo environment
#   ./scripts/run-demo.sh logs     # View logs

set -e

COMPOSE_FILE="docker-compose.observability.yml"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ ERROR: Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi

case "${1:-start}" in
  start)
    echo "🚀 Starting COMPASS demo environment..."
    docker-compose -f "$COMPOSE_FILE" up -d

    echo ""
    echo "✅ Demo environment starting..."
    echo ""
    echo "📊 Access points:"
    echo "  - Grafana:    http://localhost:3000 (anonymous Admin access)"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Jaeger:     http://localhost:16686"
    echo "  - Loki:       http://localhost:3100"
    echo "  - Tempo:      http://localhost:3200"
    echo "  - Sample App: http://localhost:8000"
    echo ""
    echo "⏳ Wait ~30 seconds for all services to be healthy"
    echo ""
    echo "🔍 Check status:  docker-compose -f $COMPOSE_FILE ps"
    echo "📋 View logs:     ./scripts/run-demo.sh logs"
    echo "🎯 Trigger incident: ./scripts/trigger-incident.sh missing_index"
    ;;

  stop)
    echo "🛑 Stopping COMPASS demo environment..."
    docker-compose -f "$COMPOSE_FILE" down
    echo "✅ Demo environment stopped"
    ;;

  restart)
    echo "🔄 Restarting COMPASS demo environment..."
    docker-compose -f "$COMPOSE_FILE" restart
    echo "✅ Demo environment restarted"
    ;;

  logs)
    docker-compose -f "$COMPOSE_FILE" logs -f
    ;;

  clean)
    echo "🧹 Stopping and removing all data..."
    docker-compose -f "$COMPOSE_FILE" down -v
    echo "✅ Demo environment cleaned (all data removed)"
    ;;

  *)
    echo "Usage: $0 {start|stop|restart|logs|clean}"
    exit 1
    ;;
esac
