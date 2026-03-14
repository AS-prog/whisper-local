#!/bin/bash
# Detener worker de forma graceful

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/logs/worker.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  No hay archivo PID. Worker posiblemente no está corriendo."
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Worker no está corriendo (PID: $PID)"
    rm -f "$PID_FILE"
    exit 0
fi

echo "🛑 Deteniendo worker (PID: $PID)..."
kill -TERM "$PID"

# Esperar a que termine
for i in {1..30}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Worker detenido"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

echo "⚠️  Worker no respondió a SIGTERM, enviando SIGKILL..."
kill -KILL "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "✅ Worker forzado a detenerse"
