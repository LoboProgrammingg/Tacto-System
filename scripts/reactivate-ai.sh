#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# TACTOFLOW — Reativar IA para número específico
# ═══════════════════════════════════════════════════════════════════════════════
#
# Uso:
#   ./scripts/reactivate-ai.sh 5565992540370
#   ./scripts/reactivate-ai.sh 5565992540370 --all-restaurants
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

PHONE_INPUT="${1:-}"
ALL_RESTAURANTS="${2:-}"

if [ -z "$PHONE_INPUT" ]; then
    echo -e "${RED}❌ Uso: $0 <telefone> [--all-restaurants]${NC}"
    echo ""
    echo "Exemplos:"
    echo "  $0 5565992540370                    # Reativa para restaurante padrão"
    echo "  $0 5565992540370 --all-restaurants  # Reativa para TODOS os restaurantes"
    echo "  $0 92540370                         # Busca por últimos dígitos"
    exit 1
fi

# Extrair últimos 8 dígitos para busca flexível
PHONE_SUFFIX="${PHONE_INPUT: -8}"

# Configurações do banco
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5433}"
DB_USER="${DB_USER:-tacto}"
DB_PASSWORD="${DB_PASSWORD:-tacto}"
DB_NAME="${DB_NAME:-tacto_db}"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          TACTOFLOW — Reativar IA para Cliente                 ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Telefone: ${YELLOW}$PHONE_INPUT${NC} (buscando por: *$PHONE_SUFFIX)"

# Verificar conexão com o banco
if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}❌ Não foi possível conectar ao banco de dados${NC}"
    echo "Verifique se o PostgreSQL está rodando: docker ps | grep postgres"
    exit 1
fi

# Mostrar status atual
echo ""
echo -e "${BLUE}Status atual das conversas:${NC}"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    c.id,
    r.name as restaurante,
    c.customer_phone as telefone,
    c.is_ai_active as ia_ativa,
    c.ai_disabled_until as desabilitada_ate,
    c.ai_disabled_reason as motivo
FROM conversations c
JOIN restaurants r ON c.restaurant_id = r.id
WHERE c.customer_phone LIKE '%$PHONE_SUFFIX'
ORDER BY c.created_at DESC;
"

# Executar a reativação
if [ "$ALL_RESTAURANTS" = "--all-restaurants" ]; then
    echo -e "${YELLOW}🔄 Reativando IA para TODOS os restaurantes...${NC}"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    UPDATE conversations 
    SET is_ai_active = true, 
        ai_disabled_until = NULL,
        ai_disabled_reason = NULL
    WHERE customer_phone LIKE '%$PHONE_SUFFIX';
    "
else
    echo -e "${YELLOW}🔄 Reativando IA para a conversa mais recente...${NC}"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    UPDATE conversations 
    SET is_ai_active = true, 
        ai_disabled_until = NULL,
        ai_disabled_reason = NULL
    WHERE customer_phone LIKE '%$PHONE_SUFFIX'
    AND id = (
        SELECT id FROM conversations 
        WHERE customer_phone LIKE '%$PHONE_SUFFIX'
        ORDER BY created_at DESC 
        LIMIT 1
    );
    "
fi

# Mostrar novo status
echo ""
echo -e "${GREEN}✅ IA reativada! Novo status:${NC}"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    c.id,
    r.name as restaurante,
    c.customer_phone as telefone,
    c.is_ai_active as ia_ativa
FROM conversations c
JOIN restaurants r ON c.restaurant_id = r.id
WHERE c.customer_phone LIKE '%$PHONE_SUFFIX'
ORDER BY c.created_at DESC;
"

echo ""
echo -e "${GREEN}✅ Pronto! O cliente pode enviar mensagens e a IA responderá.${NC}"
