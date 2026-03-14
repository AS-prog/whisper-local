#!/bin/bash
# Nightly script - Encola archivos pendientes para procesamiento nocturno

set -e

# Obtener ruta del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$PROJECT_DIR/venv"
LOG_FILE="$PROJECT_DIR/logs/nightly.log"

# Verificar que el entorno virtual existe
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Error: Entorno virtual no encontrado en $VENV_PATH" >> "$LOG_FILE"
    exit 1
fi

# Activar entorno virtual
source "$VENV_PATH/bin/activate"
cd "$PROJECT_DIR"

echo "🌙 Iniciando procesamiento nocturno..." >> "$LOG_FILE"
date >> "$LOG_FILE"

# Encolar archivos pendientes sin procesar
python -m src.cli process --enqueue-only >> "$LOG_FILE" 2>&1

echo "✅ Procesamiento nocturno completado" >> "$LOG_FILE"
