#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# TACTOFLOW — Deployment Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   ./scripts/deploy/deploy.sh staging     # Deploy to staging
#   ./scripts/deploy/deploy.sh production  # Deploy to production
#
# Requirements:
#   - Docker and Docker Compose installed
#   - Environment-specific .env file configured
#   - SSH access to target server (for remote deployments)
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

ENVIRONMENT="${1:-}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/${ENVIRONMENT}_${TIMESTAMP}"

# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

validate_environment() {
    case "$ENVIRONMENT" in
        staging|stg)
            ENVIRONMENT="staging"
            PROFILE="staging"
            API_SERVICE="api-staging"
            ;;
        production|prod)
            ENVIRONMENT="production"
            PROFILE="prod"
            API_SERVICE="api-prod"
            ;;
        *)
            echo -e "${RED}❌ Invalid environment: $ENVIRONMENT${NC}"
            echo "Usage: $0 <staging|production>"
            exit 1
            ;;
    esac
    
    export ENVIRONMENT
    export COMPOSE_PROJECT_NAME="tactoflow_${ENVIRONMENT}"
}

check_env_file() {
    ENV_FILE="config/environments/.env.${ENVIRONMENT}"
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}❌ Environment file not found: $ENV_FILE${NC}"
        echo "Please create it from the template:"
        echo "  cp config/environments/.env.${ENVIRONMENT}.example $ENV_FILE"
        exit 1
    fi
    
    # Validate required variables
    source "$ENV_FILE"
    
    local required_vars=(
        "SECRET_KEY"
        "DB_PASSWORD"
        "GOOGLE_API_KEY"
    )
    
    if [ "$ENVIRONMENT" = "production" ]; then
        required_vars+=("JOIN_WEBHOOK_SECRET" "CORS_ORIGINS")
    fi
    
    local missing=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ] || [ "${!var}" = "" ]; then
            missing+=("$var")
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${RED}❌ Missing required environment variables:${NC}"
        printf '   - %s\n' "${missing[@]}"
        exit 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Deployment Steps
# ─────────────────────────────────────────────────────────────────────────────

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           TACTOFLOW — Deployment to ${ENVIRONMENT^^}                  ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "Timestamp: ${TIMESTAMP}"
    echo -e "Git Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'N/A')"
    echo -e "Git Commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
    echo ""
}

confirm_deployment() {
    if [ "$ENVIRONMENT" = "production" ]; then
        echo -e "${RED}⚠️  WARNING: You are about to deploy to PRODUCTION!${NC}"
        echo ""
        read -p "Type 'deploy-production' to confirm: " confirmation
        if [ "$confirmation" != "deploy-production" ]; then
            echo -e "${YELLOW}Deployment cancelled.${NC}"
            exit 0
        fi
    else
        echo -e "${YELLOW}Deploying to ${ENVIRONMENT}...${NC}"
        read -p "Press Enter to continue or Ctrl+C to cancel..."
    fi
}

backup_database() {
    echo -e "${BLUE}📦 Creating database backup...${NC}"
    mkdir -p "$BACKUP_DIR"
    
    # Check if postgres container is running
    if docker ps --format '{{.Names}}' | grep -q "tactoflow_postgres"; then
        docker exec tactoflow_postgres_${ENVIRONMENT} \
            pg_dump -U tacto tacto_db > "${BACKUP_DIR}/database.sql" 2>/dev/null || true
        echo -e "${GREEN}   ✅ Database backup created: ${BACKUP_DIR}/database.sql${NC}"
    else
        echo -e "${YELLOW}   ⚠️  No running database container found, skipping backup${NC}"
    fi
}

pull_latest() {
    echo -e "${BLUE}📥 Pulling latest changes...${NC}"
    git pull origin "$(git rev-parse --abbrev-ref HEAD)" || true
}

build_images() {
    echo -e "${BLUE}🔨 Building Docker images...${NC}"
    docker compose -f docker-compose.unified.yml --profile "$PROFILE" build --no-cache
}

run_migrations() {
    echo -e "${BLUE}🗄️  Running database migrations...${NC}"
    docker compose -f docker-compose.unified.yml --profile "$PROFILE" \
        run --rm "$API_SERVICE" alembic upgrade head
}

deploy_services() {
    echo -e "${BLUE}🚀 Deploying services...${NC}"
    docker compose -f docker-compose.unified.yml --profile "$PROFILE" up -d
}

health_check() {
    echo -e "${BLUE}🏥 Running health checks...${NC}"
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf http://localhost:${API_PORT:-8000}/health > /dev/null 2>&1; then
            echo -e "${GREEN}   ✅ API is healthy!${NC}"
            return 0
        fi
        echo -e "   Waiting for API... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}   ❌ Health check failed after $max_attempts attempts${NC}"
    return 1
}

cleanup_old_images() {
    echo -e "${BLUE}🧹 Cleaning up old images...${NC}"
    docker image prune -f --filter "until=24h" || true
}

print_summary() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ✅ Deployment Successful!                        ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Environment: ${CYAN}${ENVIRONMENT}${NC}"
    echo -e "API URL:     ${CYAN}http://localhost:${API_PORT:-8000}${NC}"
    echo -e "Backup:      ${CYAN}${BACKUP_DIR}${NC}"
    echo ""
    echo -e "View logs: docker compose -f docker-compose.unified.yml --profile $PROFILE logs -f"
}

rollback() {
    echo -e "${YELLOW}🔄 Rolling back to previous version...${NC}"
    
    if [ -f "${BACKUP_DIR}/database.sql" ]; then
        echo "Restoring database backup..."
        docker exec -i tactoflow_postgres_${ENVIRONMENT} \
            psql -U tacto tacto_db < "${BACKUP_DIR}/database.sql"
    fi
    
    docker compose -f docker-compose.unified.yml --profile "$PROFILE" down
    echo -e "${GREEN}✅ Rollback complete.${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

main() {
    validate_environment
    print_banner
    check_env_file
    confirm_deployment
    
    # Trap errors for rollback
    trap 'echo -e "${RED}❌ Deployment failed!${NC}"; exit 1' ERR
    
    backup_database
    pull_latest
    build_images
    run_migrations
    deploy_services
    
    if health_check; then
        cleanup_old_images
        print_summary
    else
        echo -e "${RED}❌ Deployment failed health check!${NC}"
        read -p "Do you want to rollback? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rollback
        fi
        exit 1
    fi
}

# Run main function
main "$@"
