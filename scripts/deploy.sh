#!/bin/bash
# =============================================================
# TactoFlow Deploy Script
# Uso: bash deploy.sh [prod|dev]
# =============================================================

set -e

ENV=${1:-prod}

if [ "$ENV" = "prod" ]; then
    APP_DIR="/root/Tacto-System"
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_FILE=".env.prod"
    CONTAINER_API="tactoflow_api_prod"
    CONTAINER_DB="tactoflow_postgres_prod"
    CONTAINER_REDIS="tactoflow_redis_prod"
    IMAGE_TAG="tacto-system-api:prod"
elif [ "$ENV" = "dev" ]; then
    APP_DIR="/root/Tacto-System-dev"
    COMPOSE_FILE="docker-compose.dev.yml"
    ENV_FILE=".env.dev"
    CONTAINER_API="tactoflow_api_dev"
    CONTAINER_DB="tactoflow_postgres_dev"
    CONTAINER_REDIS="tactoflow_redis_dev"
    IMAGE_TAG="tacto-system-api:dev"
else
    echo "Uso: bash deploy.sh [prod|dev]"
    exit 1
fi

echo ">>> Ambiente: $ENV"
echo ">>> Diretório: $APP_DIR"

cd "$APP_DIR"

# Valida que o .env existe
if [ ! -f "$ENV_FILE" ]; then
    echo "ERRO: $ENV_FILE não encontrado em $APP_DIR"
    exit 1
fi

echo ">>> Build da imagem Docker..."
docker build \
    -f Dockerfile.prod \
    -t "$IMAGE_TAG" \
    .

echo ">>> Parando API para rodar migrations..."
docker stop "$CONTAINER_API" 2>/dev/null || true

echo ">>> Rodando migrations Alembic..."
docker run --rm \
    --env-file "$ENV_FILE" \
    --network "$(docker network ls --filter name=tactoflow --format '{{.Name}}' | grep "$ENV" | head -1 || echo tactoflow_network)" \
    "$IMAGE_TAG" \
    python -m alembic upgrade head

echo ">>> Subindo containers..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-build

echo ">>> Atualizando imagem da API..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-deps api

echo ">>> Aguardando health check..."
for i in $(seq 1 30); do
    if docker inspect "$CONTAINER_API" --format '{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
        echo ">>> Container healthy após ${i}s"
        break
    fi
    if [ "$i" = "30" ]; then
        echo "ERRO: Container não ficou healthy em 30s"
        docker logs "$CONTAINER_API" --tail=20
        exit 1
    fi
    sleep 1
done

echo ">>> Limpando imagens antigas..."
docker image prune -f

echo ""
echo "Deploy [$ENV] concluído com sucesso!"
docker ps --filter name=tactoflow --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
