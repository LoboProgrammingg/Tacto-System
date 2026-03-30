#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# TACTOFLOW — Development Environment Script
# ═══════════════════════════════════════════════════════════════════════════════
# 
# Usage:
#   ./scripts/dev.sh up        # Start development environment
#   ./scripts/dev.sh down      # Stop development environment
#   ./scripts/dev.sh restart   # Restart API only
#   ./scripts/dev.sh logs      # View logs
#   ./scripts/dev.sh shell     # Open shell in API container
#   ./scripts/dev.sh migrate   # Run database migrations
#   ./scripts/dev.sh test      # Run tests
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Environment
export ENVIRONMENT=development
export COMPOSE_PROJECT_NAME=tactoflow_dev

# Docker compose command
COMPOSE="docker compose -f docker-compose.unified.yml --profile dev"

# ─────────────────────────────────────────────────────────────────────────────
# Functions
# ─────────────────────────────────────────────────────────────────────────────

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║          TACTOFLOW — Development Environment                 ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_env_file() {
    if [ ! -f "config/environments/.env.development" ]; then
        echo -e "${YELLOW}⚠️  .env.development not found. Creating from template...${NC}"
        cp config/environments/.env.development config/environments/.env.development 2>/dev/null || true
    fi
}

cmd_up() {
    print_banner
    check_env_file
    echo -e "${GREEN}🚀 Starting development environment...${NC}"
    $COMPOSE up -d
    echo ""
    echo -e "${GREEN}✅ Development environment started!${NC}"
    echo -e "   API:      http://localhost:8100"
    echo -e "   Postgres: localhost:5433"
    echo -e "   Redis:    localhost:6380"
    echo ""
    echo -e "${BLUE}View logs: ./scripts/dev.sh logs${NC}"
}

cmd_down() {
    echo -e "${YELLOW}🛑 Stopping development environment...${NC}"
    $COMPOSE down
    echo -e "${GREEN}✅ Development environment stopped.${NC}"
}

cmd_restart() {
    echo -e "${YELLOW}🔄 Restarting API...${NC}"
    $COMPOSE restart api-dev
    echo -e "${GREEN}✅ API restarted.${NC}"
}

cmd_logs() {
    $COMPOSE logs -f "${2:-api-dev}"
}

cmd_shell() {
    echo -e "${BLUE}Opening shell in API container...${NC}"
    docker exec -it tactoflow_api_dev /bin/bash
}

cmd_migrate() {
    echo -e "${BLUE}Running database migrations...${NC}"
    docker exec tactoflow_api_dev alembic upgrade head
    echo -e "${GREEN}✅ Migrations complete.${NC}"
}

cmd_test() {
    echo -e "${BLUE}Running tests...${NC}"
    docker exec tactoflow_api_dev pytest tests/ -v "$@"
}

cmd_status() {
    echo -e "${BLUE}Environment Status:${NC}"
    $COMPOSE ps
}

cmd_clean() {
    echo -e "${RED}⚠️  This will remove all containers, volumes and networks!${NC}"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $COMPOSE down -v --remove-orphans
        echo -e "${GREEN}✅ Cleaned up.${NC}"
    fi
}

cmd_help() {
    echo "Usage: ./scripts/dev.sh <command>"
    echo ""
    echo "Commands:"
    echo "  up        Start development environment"
    echo "  down      Stop development environment"
    echo "  restart   Restart API service"
    echo "  logs      View logs (default: api-dev)"
    echo "  shell     Open shell in API container"
    echo "  migrate   Run database migrations"
    echo "  test      Run tests"
    echo "  status    Show container status"
    echo "  clean     Remove all containers and volumes"
    echo "  help      Show this help message"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

case "${1:-help}" in
    up)       cmd_up ;;
    down)     cmd_down ;;
    restart)  cmd_restart ;;
    logs)     cmd_logs "$@" ;;
    shell)    cmd_shell ;;
    migrate)  cmd_migrate ;;
    test)     shift; cmd_test "$@" ;;
    status)   cmd_status ;;
    clean)    cmd_clean ;;
    help|*)   cmd_help ;;
esac
