# Whisper Transcription Processor

Procesador de transcripciones de audio usando el servidor local de whisper.cpp.

## Requisitos

- Python 3.14+
- ffmpeg (`brew install ffmpeg`)
- Servidor whisper.cpp ejecutándose en `localhost:8080`

## Instalación

```bash
cd ~/projects/whisper-local/transcriptions
~/projects/whisper-local/venv/bin/pip install -r requirements.txt
```

## Uso

### 1. Iniciar el servidor whisper

```bash
cd ~/projects/whisper-local/whisper.cpp
./build/bin/whisper-server -m models/ggml-large-v3-turbo.bin --port 8080 --host 0.0.0.0
```

### 2. Iniciar el procesador

```bash
~/projects/whisper-local/venv/bin/python ~/projects/whisper-local/transcriptions/app.py
```

## Estructura

```
~/projects/whisper-local/
├── whisper.cpp/           # Repositorio de whisper.cpp
├── venv/                 # Entorno virtual Python
├── inputs/               # Archivos de audio a procesar
│   └── processed/       # Archivos procesados
└── transcriptions/       # Este repositorio
    ├── app.py           # Procesador principal
    ├── requirements.txt # Dependencias
    └── <transcripciones>.json
```

## Workflow

1. Copiar/mover archivos de audio a `~/projects/whisper-local/inputs/`
2. Formatos soportados: `.mp3`, `.wav`, `.ogg`, `.m4a`, `.flac`
3. El procesador detecta automáticamente el archivo, lo convierte a WAV, lo transcribe y guarda el resultado JSON en `transcriptions/`
4. El archivo original se mueve a `inputs/processed/`

## Formato de salida

```json
{
  "filename": "audio.m4a",
  "timestamp": "2026-03-01T14:48:44.345772",
  "text": "Transcripción en español...",
  "language": "es"
}
```

## Límites

- **Recomendado**: < 50 MB por archivo (~30-40 min de audio)
- **Timeout**: 5 minutos por archivo

## Enviar archivos por SCP

```bash
# Archivo individual
scp ~/Downloads/audio.m4a localhost:~/projects/whisper-local/inputs/

# Múltiples archivos
scp ~/Downloads/*.m4a localhost:~/projects/whisper-local/inputs/

# Carpeta completa
scp -r ~/Downloads/carpeta_audio/ localhost:~/projects/whisper-local/inputs/
```
