#!/bin/bash
# ============================================
# TactoFlow Production Deployment Script
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  TactoFlow Production Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo -e "${RED}Error: .env.production file not found!${NC}"
    echo -e "${YELLOW}Copy .env.production.example to .env.production and fill in the values.${NC}"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env.production | xargs)

# Validate required variables
REQUIRED_VARS=("SECRET_KEY" "DB_PASSWORD" "TACTO_CLIENT_SECRET" "JOIN_TOKEN_CLIENTE" "GOOGLE_API_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}Error: Required variable $var is not set!${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓ Environment variables validated${NC}"

# Build the production image
echo -e "${YELLOW}Building production Docker image...${NC}"
docker-compose -f docker-compose.prod.yml build --no-cache api

echo -e "${GREEN}✓ Docker image built${NC}"

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose -f docker-compose.prod.yml down

# Start services
echo -e "${YELLOW}Starting services...${NC}"
docker-compose -f docker-compose.prod.yml up -d postgres redis

# Wait for database to be ready
echo -e "${YELLOW}Waiting for database to be ready...${NC}"
sleep 10

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
docker-compose -f docker-compose.prod.yml run --rm api python -m alembic upgrade head

echo -e "${GREEN}✓ Migrations completed${NC}"

# Start API
echo -e "${YELLOW}Starting API service...${NC}"
docker-compose -f docker-compose.prod.yml up -d api

# Wait for API to be healthy
echo -e "${YELLOW}Waiting for API to be healthy...${NC}"
sleep 5

# Health check
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:${API_PORT:-8000}/health > /dev/null; then
        echo -e "${GREEN}✓ API is healthy${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}Waiting for API... (attempt $RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 3
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}Error: API failed to start!${NC}"
    docker-compose -f docker-compose.prod.yml logs api
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "API URL: http://localhost:${API_PORT:-8000}"
echo -e "Health: http://localhost:${API_PORT:-8000}/health"
echo -e "Docs: http://localhost:${API_PORT:-8000}/docs"
echo -e ""
echo -e "To view logs: docker-compose -f docker-compose.prod.yml logs -f api"
