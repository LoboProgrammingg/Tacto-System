#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# TACTOFLOW — Environment Setup Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# Creates environment-specific .env files from templates.
# Run this when setting up a new environment or after cloning the repo.
#
# Usage:
#   ./scripts/deploy/setup-env.sh development
#   ./scripts/deploy/setup-env.sh staging
#   ./scripts/deploy/setup-env.sh production
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

ENVIRONMENT="${1:-development}"
ENV_DIR="config/environments"
ENV_FILE="${ENV_DIR}/.env.${ENVIRONMENT}"

echo -e "${BLUE}Setting up ${ENVIRONMENT} environment...${NC}"

# Check if file already exists
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  $ENV_FILE already exists.${NC}"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Create directory if needed
mkdir -p "$ENV_DIR"

# Copy template
case "$ENVIRONMENT" in
    development|dev)
        ENVIRONMENT="development"
        ;;
    staging|stg)
        ENVIRONMENT="staging"
        ;;
    production|prod)
        ENVIRONMENT="production"
        ;;
    *)
        echo -e "${RED}Invalid environment: $ENVIRONMENT${NC}"
        echo "Valid options: development, staging, production"
        exit 1
        ;;
esac

ENV_FILE="${ENV_DIR}/.env.${ENVIRONMENT}"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Template not found: $ENV_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment file ready: $ENV_FILE${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit $ENV_FILE with your credentials"
echo "  2. Run: ./scripts/dev.sh up (for development)"
echo "  3. Or:  ./scripts/deploy/deploy.sh $ENVIRONMENT (for deployment)"
