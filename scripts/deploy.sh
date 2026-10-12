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
elif [ "$ENV" = "dev" ]; then
    APP_DIR="/root/Tacto-System-dev"
    COMPOSE_FILE="docker-compose.dev.yml"
    ENV_FILE=".env.dev"
    CONTAINER_API="tactoflow_api_dev"
    CONTAINER_DB="tactoflow_postgres_dev"
    CONTAINER_REDIS="tactoflow_redis_dev"
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

# Imagem em uso antes do deploy (vazio se a API ainda não existe)
PREV_IMAGE=$(docker inspect "$CONTAINER_API" --format '{{.Image}}' 2>/dev/null || true)

echo ">>> Build da imagem Docker..."
# Via compose: a imagem construída é exatamente a que o `up` abaixo usa
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build api

echo ">>> Subindo infra (postgres + redis)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d postgres redis

echo ">>> Aguardando postgres ficar pronto..."
for i in $(seq 1 30); do
    if docker exec "$CONTAINER_DB" pg_isready -U tacto -d tacto_db -q 2>/dev/null; then
        echo ">>> Postgres pronto após ${i}s"
        break
    fi
    if [ "$i" = "30" ]; then
        echo "ERRO: Postgres não ficou pronto em 30s"
        exit 1
    fi
    sleep 1
done

echo ">>> Rodando migrations Alembic..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm --no-deps api \
    python -m alembic upgrade head

echo ">>> Subindo API..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-deps api

# O prune no fim apaga a imagem anterior; esta tag preserva a última que rodou
CURR_IMAGE=$(docker inspect "$CONTAINER_API" --format '{{.Image}}' 2>/dev/null || true)
if [ -n "$PREV_IMAGE" ] && [ "$PREV_IMAGE" != "$CURR_IMAGE" ]; then
    docker tag "$PREV_IMAGE" "tacto-system-api:rollback-$ENV" \
        && echo ">>> Imagem anterior preservada em tacto-system-api:rollback-$ENV" \
        || echo ">>> AVISO: não foi possível criar a tag de rollback"
fi

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
