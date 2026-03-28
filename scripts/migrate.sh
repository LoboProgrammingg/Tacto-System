#!/bin/bash
# ============================================
# TactoFlow Database Migration Script
# ============================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Running database migrations...${NC}"

# Check if running in Docker or locally
if [ -f "/.dockerenv" ]; then
    # Inside Docker
    python -m alembic upgrade head
else
    # Local development
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
    fi
    python -m alembic upgrade head
fi

echo -e "${GREEN}✓ Migrations completed${NC}"
