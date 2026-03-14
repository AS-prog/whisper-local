#!/bin/bash
# Script de validación de configuración
# Verifica que todas las variables necesarias estén configuradas

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Validando configuración de whisper-local..."
echo ""

# Verificar que .env existe
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ ERROR: Archivo .env no encontrado${NC}"
    echo "   Copia .env.example a .env y configura las variables:"
    echo "   cp .env.example .env"
    echo ""
    exit 1
fi

# Cargar variables
set -a
source .env
set +a

ERRORS=0
WARNINGS=0

# Función para verificar variable requerida
check_required() {
    local var_name=$1
    local var_value=$2
    
    if [ -z "$var_value" ]; then
        echo -e "${RED}❌ ERROR: $var_name no está configurado${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    else
        echo -e "${GREEN}✅ $var_name configurado${NC}"
        return 0
    fi
}

# Función para verificar variable opcional
check_optional() {
    local var_name=$1
    local var_value=$2
    
    if [ -z "$var_value" ]; then
        echo -e "${YELLOW}⚠️  WARNING: $var_name no está configurado (opcional)${NC}"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "${GREEN}✅ $var_name configurado${NC}"
    fi
}

echo "📋 Variables requeridas:"
echo "─────────────────────────"
check_required "WHISPER_HOST" "$WHISPER_HOST"
check_required "WHISPER_PORT" "$WHISPER_PORT"
check_required "DATABASE_PATH" "$DATABASE_PATH"

echo ""
echo "📋 Variables opcionales:"
echo "─────────────────────────"
check_optional "TELEGRAM_BOT_TOKEN" "$TELEGRAM_BOT_TOKEN"
check_optional "DISCORD_BOT_TOKEN" "$DISCORD_BOT_TOKEN"

echo ""
echo "📋 Configuración de procesamiento:"
echo "───────────────────────────────────"
if [ -n "$MAX_FILE_SIZE_MB" ]; then
    echo -e "${GREEN}✅ MAX_FILE_SIZE_MB: $MAX_FILE_SIZE_MB MB${NC}"
else
    echo -e "${YELLOW}⚠️  MAX_FILE_SIZE_MB: usando default (40 MB)${NC}"
fi

if [ -n "$CHUNK_DURATION_SECONDS" ]; then
    echo -e "${GREEN}✅ CHUNK_DURATION_SECONDS: $CHUNK_DURATION_SECONDS segundos${NC}"
else
    echo -e "${YELLOW}⚠️  CHUNK_DURATION_SECONDS: usando default (600 segundos)${NC}"
fi

echo ""
echo "─────────────────────────────────────────────"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ Configuración válida. $WARNINGS advertencias.${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Configuración inválida. $ERRORS errores, $WARNINGS advertencias.${NC}"
    echo ""
    echo "Por favor, edita el archivo .env y configura las variables faltantes."
    echo ""
    exit 1
fi
