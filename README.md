# Whisper Local

Procesador de transcripciones de audio usando Whisper CPP con servidor local.

## Estructura del Proyecto

```
whisper-local/
├── whisper.cpp/           # Repositorio de whisper.cpp (submodulo)
├── venv/                  # Entorno virtual Python 3.14
├── inputs/                # Archivos de audio a procesar
│   └── processed/        # Archivos ya procesados
├── transcriptions/        # Codigo y transcripciones
│   ├── app.py            # Procesador principal
│   ├── requirements.txt  # Dependencias Python
│   └── *.json            # Archivos de transcripcion
└── README.md             # Este archivo
```

## Requisitos

- Python 3.14+
- ffmpeg (`brew install ffmpeg`)
- whisper.cpp compilado con servidor

## Uso

### 1. Iniciar servidor whisper

```bash
cd whisper.cpp
./build/bin/whisper-server -m models/ggml-large-v3-turbo.bin --port 8080 --host 0.0.0.0
```

### 2. Ejecutar procesador

```bash
venv/bin/python transcriptions/app.py
```

## Workflow

1. Copiar archivos de audio a `inputs/`
2. Formatos: `.mp3`, `.wav`, `.ogg`, `.m4a`, `.flac`
3. El procesador convierte a WAV, transcribe y guarda JSON en `transcriptions/`
4. Archivo movido a `inputs/processed/`

## Formato de Salida JSON

```json
{
  "filename": "audio.m4a",
  "timestamp": "2026-03-01T14:48:44",
  "text": "Transcripcion...",
  "language": "es"
}
```

## Limites

- Recomendado: < 50 MB (~30-40 min audio)
- Timeout: 5 minutos por archivo
