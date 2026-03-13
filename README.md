# Whisper Local

Procesador de transcripciones de audio usando whisper.cpp con servidor REST local. Utiliza el modelo `ggml-large-v3-turbo` para transcribir audio a texto en español.

## Estructura del Proyecto

```
whisper-local/
├── whisper.cpp/           # Repositorio de whisper.cpp
│   └── models/           # Modelos descargados
│       └── ggml-large-v3-turbo.bin
├── venv/                 # Entorno virtual Python
├── inputs/               # Archivos de audio a procesar
│   └── processed/       # Archivos ya transcritos
└── transcriptions/       # Procesador y transcripciones
    ├── app.py           # Procesador principal
    └── requirements.txt # Dependencias
```

## Requisitos

- Python 3.14+
- ffmpeg (`brew install ffmpeg`)
- macOS (optimizado para Apple Silicon)

## Instalación

### 1. Clonar y compilar whisper.cpp

```bash
cd whisper.cpp
make -j8
```

### 2. Descargar modelo (ya descargado)

```bash
# Large v3 turbo (1.5GB) - ya presente en models/
curl -L -o models/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

### 3. Instalar dependencias Python

```bash
./venv/bin/pip install -r transcriptions/requirements.txt
```

## Uso

### Paso 1: Iniciar el servidor whisper

```bash
cd whisper.cpp
./build/bin/whisper-server -m models/ggml-large-v3-turbo.bin --port 8080 --host 0.0.0.0
```

### Paso 2: Iniciar el procesador

```bash
./venv/bin/python transcriptions/app.py
```

### Paso 3: Agregar archivos de audio

Copiar archivos de audio a `inputs/`

**Formatos soportados:** `.mp3`, `.wav`, `.ogg`, `.m4a`, `.flac`

El procesador:
1. Detecta el nuevo archivo automáticamente
2. Convierte a WAV (16kHz, mono) si es necesario
3. Envía al servidor whisper
4. Guarda la transcripción en JSON
5. Mueve el archivo original a `inputs/processed/`

## Modelo Disponible

| Modelo | Tamaño | Velocidad | Notas |
|--------|--------|-----------|-------|
| ggml-large-v3-turbo | 1.5GB | Medio | **Activo** - Mejor calidad |
| ggml-medium | ~1.5GB | Rápido | Alternativo |
| ggml-small | ~500MB | Rápido | Más rápido |
| ggml-base | ~150MB | Muy rápido | Menor calidad |
| ggml-tiny | ~75MB | Muy rápido | Solo pruebas |

**Ubicación:** `whisper.cpp/models/`

## Formato de Salida

```json
{
  "filename": "audio.m4a",
  "timestamp": "2026-03-01T14:48:44.345772",
  "text": "Transcripción en español...",
  "language": "es"
}
```

## Rutas

| Recurso | Ruta |
|---------|------|
| Proyecto | `~/projects/whisper-local/` |
| whisper.cpp | `~/projects/whisper-local/whisper.cpp/` |
| Servidor | `localhost:8080` |
| Entrada audio | `~/projects/whisper-local/inputs/` |
| Salida JSON | `~/projects/whisper-local/transcriptions/` |
| Procesados | `~/projects/whisper-local/inputs/processed/` |
| Logs | `~/projects/whisper-local/inputs/whisper_processor.log` |

## Verificar Estado

### ¿Servidor activo?

```bash
curl -s http://localhost:8080/health
```

### ¿Hay archivos pendientes?

```bash
ls -lh inputs/
```

### Ver logs

```bash
tail -f inputs/whisper_processor.log
```

## Administración del Servidor

### Iniciar servidor

```bash
cd whisper.cpp
nohup ./build/bin/whisper-server -m models/ggml-large-v3-turbo.bin --port 8080 --host 0.0.0.0 > /tmp/whisper-server.log 2>&1 &
```

### Apagar servidor

```bash
pkill -f "whisper-server"
```

### Verificar estado

```bash
curl -s http://localhost:8080/health
# {"status":"ok"}
```

### Ver logs

```bash
tail -f /tmp/whisper-server.log
```

### Mantener servidor funcionando con screen

```bash
# Crear sesión
screen -S whisper

# Levantar servidor
./build/bin/whisper-server -m models/ggml-large-v3-turbo.bin --port 8080 --host 0.0.0.0

# Detachar: Ctrl+A, D

# Reactivar sesión
screen -r whisper
```

### Si el servidor se cae

```bash
# Verificar si está caído
curl -s http://localhost:8080/health || echo "Servidor caído"

# Si está caído, levantar de nuevo
cd whisper.cpp && nohup ./build/bin/whisper-server -m models/ggml-large-v3-turbo.bin --port 8080 --host 0.0.0.0 > /tmp/whisper-server.log 2>&1 &
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| "ffmpeg no encontrado" | `brew install ffmpeg` |
| "No se pudo conectar al servidor" | Iniciar servidor: `cd whisper.cpp && ./build/bin/whisper-server ...` |
| Timeout en archivo grande | El límite es ~50MB por archivo (~30-40 min audio) |
| Modelo no encontrado | Verificar que `ggml-large-v3-turbo.bin` existe en `models/` |

## API del Servidor

**Endpoint:** `http://localhost:8080/inference`

```bash
curl -X POST http://localhost:8080/inference \
  -F "file=@audio.wav" \
  -F "response_format=json" \
  -F "language=es"
```

## Límites

- Recomendado: < 50 MB (~30-40 min audio)
- Timeout: 5 minutos por archivo
