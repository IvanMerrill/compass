#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.dev.yml"

usage() {
    echo "Usage: $0 {start|stop|status|reset|logs}"
    echo ""
    echo "Commands:"
    echo "  start   - Start development environment"
    echo "  stop    - Stop development environment"
    echo "  status  - Show status of services"
    echo "  reset   - Reset development data (stops, removes volumes, restarts)"
    echo "  logs    - Show logs from all services"
    exit 1
}

start() {
    echo "Starting COMPASS development environment..."
    docker-compose -f "$COMPOSE_FILE" up -d
    echo "Waiting for services to be healthy..."
    sleep 5
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    echo "✅ Development environment started!"
    echo ""
    echo "Services available at:"
    echo "  Redis:      localhost:6379"
    echo "  PostgreSQL: localhost:5432 (db: compass, user: compass, pass: compass_dev)"
    echo "  Grafana:    http://localhost:3000 (user: admin, pass: admin)"
}

stop() {
    echo "Stopping COMPASS development environment..."
    docker-compose -f "$COMPOSE_FILE" down
    echo "✅ Development environment stopped!"
}

status() {
    echo "COMPASS development environment status:"
    docker-compose -f "$COMPOSE_FILE" ps
}

reset() {
    echo "Resetting COMPASS development environment..."
    echo "⚠️  This will delete all data in Redis and PostgreSQL!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f "$COMPOSE_FILE" down -v
        echo "Starting fresh environment..."
        start
        echo "✅ Development environment reset complete!"
    else
        echo "Reset cancelled."
    fi
}

logs() {
    docker-compose -f "$COMPOSE_FILE" logs -f
}

case "${1:-}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    reset)
        reset
        ;;
    logs)
        logs
        ;;
    *)
        usage
        ;;
esac
