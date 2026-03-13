# Plan: Sistema de Transcripción whisper-local v2

## Visión General

Sistema de transcripción de audio que se ejecuta bajo demanda o automáticamente. Procesa notas de voz recibidas por Telegram/Discord y archivos locales, levantando el servidor whisper solo durante el procesamiento.

## Requisitos

- **Mensajería**: Telegram + Discord (bots)
- **Ejecución**: Bajo demanda (manual) o schedule (nocturno)
- **Servidor**: Levantar → procesar → apagar (no deja servidor corriendo)
- **Archivos grandes**: > 40MB → aislar en carpeta `big_size/`

---

## Estructura de Directorios Objetivo

```
whisper-local/
├── .git/
├── .gitignore
├── README.md
├── AGENTS.md
├── docs/
│   └── plan.md
├── venv/
├── src/
│   ├── __init__.py
│   ├── whisper_client.py     # Cliente para servidor whisper
│   ├── audio_processor.py    # Conversión y manejo de archivos
│   ├── file_manager.py      # Gestor de carpetas
│   ├── batch_processor.py  # Procesador por lotes
│   ├── telegram_bot.py     # Bot de Telegram
│   ├── discord_bot.py      # Bot de Discord
│   └── cli.py              # Interfaz de línea de comandos
├── config.yaml              # Configuraciones
├── requirements.txt
├── inputs/
│   ├── pending/            # Archivos sin procesar
│   ├── processing/         # Archivos en proceso
│   ├── processed/          # Ya transcritos
│   └── big_size/          # Archivos > 40MB
├── transcriptions/         # (no trackear en git)
└── whisper.cpp/
```

---

## Archivos a Trackear en Git

| Tipo | Archivos |
|------|----------|
| Código | `src/*.py` |
| Config | `config.yaml`, `requirements.txt` |
| Docs | `README.md`, `AGENTS.md`, `docs/plan.md` |

| No Trackear | Razón |
|-------------|--------|
| `inputs/` | Audios originales |
| `transcriptions/*.json` | Transcripciones generadas |
| `whisper.cpp/` | Repositorio externo |
| `venv/` | Entorno virtual |

---

## Fases de Implementación

### Fase 1: Reestructuración del Proyecto

**Objetivo:** Organizar el código en módulos reutilizables

#### 1.1 Crear estructura de carpetas
- Crear `src/` con módulos Python
- Crear subcarpetas en `inputs/`:
  - `inputs/pending/` - Archivos sin procesar
  - `inputs/processing/` - Archivos en proceso
  - `inputs/processed/` - Ya transcritos
  - `inputs/big_size/` - Archivos > 40MB

#### 1.2 Separar `app.py` en módulos

| Módulo | Responsabilidad |
|--------|-----------------|
| `whisper_client.py` | Comunicar con servidor whisper (HTTP) |
| `audio_processor.py` | Conversión de audio (ffmpeg), validación |
| `file_manager.py` | Mover, copiar, listar archivos |
| `batch_processor.py` | Orquestar todo el flujo |

#### 1.3 Actualizar requirements.txt
- Añadir dependencias necesarias

#### 1.4 Crear config.yaml
- Rutas configurables
- Límites (tamaño máximo, timeouts)
- Configuración de bots (tokens)
- Horarios

---

### Fase 2: Batch Processor

**Objetivo:** Procesador que levanta/tumba el servidor whisper

#### 2.1 Implementar file_manager.py
- `scan_pending()`: Lista archivos en `inputs/pending/`
- `move_to_big_size()`: Mueve archivos > 40MB
- `move_to_processed()`: Mueve archivos ya transcritos
- `move_to_processing()`: Prepara archivo para procesar

#### 2.2 Implementar whisper_client.py
- `start_server()`: Levanta servidor whisper en background
- `stop_server()`: Apaga servidor
- `transcribe(audio_path)`: Envía archivo y retorna texto
- `wait_until_ready()`: Espera a que el servidor esté disponible

#### 2.3 Implementar audio_processor.py
- `convert_to_wav(input_path)`: Convierte a WAV 16kHz mono
- `validate_audio(path)`: Verifica formato y tamaño
- `get_file_size_mb(path)`: Retorna tamaño en MB

#### 2.4 Implementar batch_processor.py
```python
def process_batch():
    # 1. Escanear inputs/pending/
    # 2. Por cada archivo:
    #    a. Si > 40MB → mover a inputs/big_size/
    #    b. Si <= 40MB → procesar
    # 3. Si hay archivos pendientes:
    #    a. Levantar servidor whisper
    #    b. Por cada archivo <= 40MB:
    #       - Mover a processing/
    #       - Convertir a WAV
    #       - Enviar a whisper
    #       - Guardar JSON en transcriptions/
    #       - Mover a processed/
    #    c. Apagar servidor
```

#### 2.5 Crear script nocturnal
- `scripts/nightly_transcribe.sh`
- Ejecutable via cron
- Logging a archivo

---

### Fase 3: Integración Telegram

**Objetivo:** Recibir notas de voz por Telegram

#### 3.1 Crear telegram_bot.py
- Usar `python-telegram-bot` o `aiogram`
- Comandos:
  - `/start`: Saludo
  - `/transcribe`: Forzar procesamiento batch
  - `/status`: Ver archivos pendientes
  - Voice message: Descarga y guarda en `inputs/pending/`

#### 3.2 Flujo de trabajo
1. Usuario envía nota de voz
2. Bot descarga audio → `inputs/pending/`
3. Bot ejecuta `batch_processor.process_batch()`
4. Bot envía transcripción de vuelta al usuario

#### 3.3 Manejo de errores
- Si archivo > 40MB: Notificar al usuario
- Si error de procesamiento: Notificar con mensaje

---

### Fase 4: Integración Discord

**Objetivo:** Recibir notas de voz por Discord

#### 4.1 Crear discord_bot.py
- Usar `discord.py`
- Listeners:
  - Mensajes de voz en canales
  - Archivos de audio adjuntos
  - Comandos slash (/)

#### 4.2 Flujo de trabajo
1. Usuario envía archivo de audio o mensaje de voz
2. Bot descarga → `inputs/pending/`
3. Bot ejecuta `batch_processor.process_batch()`
4. Bot envía transcripción al canal

---

### Fase 5: CLI Unificada

**Objetivo:** Interfaz de línea de comandos completa

#### 5.1 Crear cli.py con argparse/click
```bash
# Procesar batch actual
whisper-local process

# Ver estado
whisper-local status

# Iniciar bot Telegram
whisper-local telegram

# Iniciar bot Discord
whisper-local discord

# Configuración
whisper-local config init
```

#### 5.2 Mejoras adicionales
- Colored output
- Progress bars
- Verbose mode

---

## Orden de Implementación Sugerido

| Paso | Fase | Descripción |
|------|------|-------------|
| 1 | Fase 1 | Crear estructura y mover código |
| 2 | Fase 1 | Crear config.yaml |
| 3 | Fase 2 | Implementar módulos core |
| 4 | Fase 2 | Implementar batch processor |
| 5 | Fase 2 | Script nocturnal |
| 6 | Fase 3 | Telegram bot |
| 7 | Fase 4 | Discord bot |
| 8 | Fase 5 | CLI final |

---

## Notas Técnicas

- **Servidor whisper**: Se levanta con `nohup` y se mata por PID
- **Timeout por archivo**: 5 minutos (configurable)
- **Tamaño máximo**: 40MB (configurable)
- **Formatos audio**: mp3, wav, ogg, m4a, flac
- **Logs**: En `inputs/whisper_processor.log` y stdout
