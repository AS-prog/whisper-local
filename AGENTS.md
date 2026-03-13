# Whisper Local - AGENTS.md

Este documento proporciona contexto para agentes IA sobre la estructura y propósito del proyecto.

## Propósito del Proyecto

Procesador de transcripciones de audio usando whisper.cpp con servidor REST local. Convierte archivos de audio a texto en español utilizando el modelo `ggml-large-v3-turbo`.

## Estructura de Directorios

```
whisper-local/
├── .git/                    # Repositorio Git
├── .gitignore               # Archivos ignorados por Git
├── README.md                # Documentación del proyecto
├── venv/                    # Entorno virtual Python
├── inputs/                  # Archivos de audio de entrada
│   ├── processed/           # Audios ya transcritos
│   └── whisper_processor.log # Log del procesador
├── transcriptions/          # Código y transcripciones
│   ├── app.py              # Procesador principal
│   ├── requirements.txt    # Dependencias Python
│   └── *.json              # Archivos de transcripción
└── whisper.cpp/            # Repositorio de whisper.cpp
    └── models/             # Modelos Whisper GGML
        └── ggml-large-v3-turbo.bin  # Modelo activo (1.5GB)
```

## Descripción de Cada Carpeta

### `venv/`

Entorno virtual Python que contiene las dependencias instaladas del proyecto. Se usa para ejecutar el procesador de transcripciones.

### `inputs/`

Directorio de entrada para archivos de audio. Aquí se copian los archivos de audio a transcribir.

- **Formatos soportados:** `.mp3`, `.wav`, `.ogg`, `.m4a`, `.flac`
- **Límite recomendado:** < 50MB (~30-40 min audio)

### `inputs/processed/`

Contiene los archivos de audio que ya han sido transcritos. El procesador mueve automáticamente los archivos procesados a esta carpeta.

### `inputs/whisper_processor.log`

Log de ejecución del procesador. Útil para debugging y seguimiento de transcripciones.

### `transcriptions/`

Contiene el código fuente del procesador y los archivos de transcripción generados.

- `app.py`: Procesador principal que detecta archivos, convierte a WAV, envía al servidor y guarda transcripciones
- `requirements.txt`: Dependencias Python del proyecto
- `*.json`: Archivos de transcripción generados (formato: `{filename}.json`)

### `whisper.cpp/`

Repositorio clonado de [whisper.cpp](https://github.com/ggerganov/whisper.cpp). Contiene el código fuente y binarios compilados.

### `whisper.cpp/models/`

Modelos Whisper en formato GGML. Contiene:

- `ggml-large-v3-turbo.bin`: Modelo activo (1.5GB) - mejor calidad
- Modelos de prueba para desarrollo

## Comandos Útiles

```bash
# Iniciar servidor whisper
cd whisper.cpp && ./build/bin/whisper-server -m models/ggml-large-v3-turbo.bin --port 8080 --host 0.0.0.0

# Ejecutar procesador
./venv/bin/python transcriptions/app.py

# Verificar estado del servidor
curl -s http://localhost:8080/health

# Ver logs del procesador
tail -f inputs/whisper_processor.log

# Apagar servidor
pkill -f "whisper-server"
```

## Notas Importantes

- La carpeta `inputs/` NO debe subirse a Git (contiene audios originales)
- Solo trackear: código fuente, configuraciones, modelos (si es necesario), transcripciones JSON
- El servidor whisper debe estar corriendo antes de ejecutar el procesador
