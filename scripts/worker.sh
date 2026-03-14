#!/bin/bash
# Worker script - Inicia el worker en background

set -e

# Obtener ruta del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$PROJECT_DIR/venv"
LOG_FILE="$PROJECT_DIR/logs/worker.log"
PID_FILE="$PROJECT_DIR/logs/worker.pid"

# Verificar que el entorno virtual existe
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Error: Entorno virtual no encontrado en $VENV_PATH"
    exit 1
fi

# Activar entorno virtual
source "$VENV_PATH/bin/activate"
cd "$PROJECT_DIR"

# Verificar que no haya otro worker corriendo
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️  Worker ya está corriendo (PID: $PID)"
        exit 0
    fi
fi

echo "🚀 Iniciando worker..."
nohup python -m src.worker >> "$LOG_FILE" 2>&1 &
WORKER_PID=$!
echo $WORKER_PID > "$PID_FILE"

echo "✅ Worker iniciado con PID $WORKER_PID"
echo "📝 Logs: $LOG_FILE"
