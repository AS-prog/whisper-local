# Plan: Sistema de Transcripción whisper-local v2.1

## Visión General

Sistema de transcripción de audio que se ejecuta bajo demanda o automáticamente. Procesa notas de voz recibidas por Telegram/Discord y archivos locales, levantando el servidor whisper solo durante el procesamiento.

**Cambios Clave v2.1:**
- Procesamiento asíncrono con sistema de colas (SQLite)
- Soporte para archivos grandes mediante chunking
- Sistema de lock para evitar race conditions
- Notificaciones de progreso en tiempo real
- Seguridad mejorada (tokens en .env)
- Docker-compose para infraestructura

## Requisitos

- **Mensajería**: Telegram + Discord (bots)
- **Ejecución**: Bajo demanda (manual) o schedule (nocturno)
- **Servidor**: Levantar → procesar → apagar (no deja servidor corriendo)
- **Archivos grandes**: > 40MB → procesamiento por chunks
- **Progreso**: Notificaciones de % cada 10%

---

## Estructura de Directorios Objetivo

```
whisper-local/
├── .env                       # Variables de entorno sensibles (NO git)
├── .env.example              # Template de variables
├── docker-compose.yml        # Servicios whisper + worker
├── .git/
├── .gitignore
├── README.md
├── AGENTS.md
├── docs/
│   ├── plan.md              # Este documento
│   └── tasks.md             # Documento detallado de tareas
├── venv/
├── src/
│   ├── __init__.py
│   ├── database.py          # SQLite: jobs, cache, metrics
│   ├── whisper_client.py    # Cliente HTTP + healthcheck
│   ├── audio_processor.py   # FFmpeg + chunking
│   ├── file_manager.py      # Gestor + lock mechanism
│   ├── job_queue.py         # Cola priorizada
│   ├── telegram_bot.py      # Bot asíncrono con progreso
│   ├── discord_bot.py       # Bot asíncrono
│   ├── worker.py            # Procesador asíncrono de jobs
│   └── cli.py               # CLI con subcomandos
├── scripts/
│   ├── worker.sh            # Inicia worker
│   └── nightly.sh           # Cron job
├── migrations/              # SQL para schema
│   └── 001_init.sql
├── inputs/
│   ├── pending/            # Archivos sin procesar
│   ├── processing/         # Archivos en proceso
│   ├── processed/          # Ya transcritos
│   └── big_size/          # Archivos > 40MB (temporal)
├── transcriptions/         # (no trackear en git)
│   └── cache/             # Cache de hashes SHA256
└── whisper.cpp/
```

---

## Archivos a Trackear en Git

| Tipo | Archivos |
|------|----------|
| Código | `src/*.py` |
| Config | `.env.example`, `docker-compose.yml` |
| Scripts | `scripts/*.sh` |
| Docs | `README.md`, `AGENTS.md`, `docs/*.md` |
| SQL | `migrations/*.sql` |

| No Trackear | Razón |
|-------------|--------|
| `.env` | Tokens y secrets |
| `inputs/` | Audios originales |
| `transcriptions/*.json` | Transcripciones generadas |
| `transcriptions/cache/` | Cache de hashes |
| `whisper.cpp/` | Repositorio externo |
| `venv/` | Entorno virtual |

---

## Fases de Implementación

### Fase 0: Infraestructura Segura (1-2 días)

**Objetivo:** Establecer base segura y reproducible

#### 0.1 Seguridad y Configuración
- Crear `.env.example` con todas las variables necesarias
- Actualizar `.gitignore` para excluir `.env`
- Documentar variables requeridas en README

#### 0.2 Docker y Base de Datos
- Crear `docker-compose.yml` con servicio whisper
- Crear `migrations/001_init.sql` para schema SQLite
- Definir tablas: jobs, cache, metrics, rate_limits

#### 0.3 Estructura de Proyecto
- Crear carpetas `src/`, `scripts/`, `migrations/`
- Crear archivos `__init__.py` vacíos
- Mover código existente a backup

---

### Fase 1: Core Asíncrono (2-3 días)

**Objetivo:** Sistema de colas robusto con persistencia

#### 1.1 Base de Datos (database.py)
- Wrapper SQLite con context managers
- Métodos CRUD para tabla jobs
- Métodos para cache de transcripciones
- Métodos para métricas y rate limiting

#### 1.2 Sistema de Colas (job_queue.py)
- Colas: pending, big_files, processing
- Priorización: pending > big_files
- Estados del job: pending → processing → completed/failed
- Reintentos con backoff exponencial

#### 1.3 Gestión de Archivos (file_manager.py)
- Mover archivos entre carpetas
- Calcular SHA256 para cache
- Sistema de lock con archivo `.whisper.lock`
- Timeout y cleanup de locks huérfanos

#### 1.4 Procesamiento de Audio (audio_processor.py)
- Conversión a WAV 16kHz mono
- Validación de formato y tamaño
- **Chunking:** Dividir archivos >40MB en segments de 10 min
- Overlap de 2 segundos entre chunks para contexto

---

### Fase 2: Worker y Cliente Whisper (2 días)

**Objetivo:** Procesador asíncrono con healthcheck

#### 2.1 Cliente Whisper (whisper_client.py)
- Conexión HTTP al servidor
- Healthcheck con retry
- Método `transcribe()` con timeout
- Manejo de errores de red

#### 2.2 Worker (worker.py)
- Loop principal que consume cola
- Adquirir lock antes de procesar
- Levantar servidor whisper si es necesario
- Procesar chunks y concatenar resultados
- Actualizar progreso en base de datos
- Liberar lock al terminar

#### 2.3 Scripts de Ejecución
- `scripts/worker.sh`: Inicia worker en background
- `scripts/nightly.sh`: Solo encola archivos (no procesa)
- Configurar cron para nightly.sh

---

### Fase 3: Bots con Progreso (2-3 días)

**Objetivo:** Interfaz de usuario con feedback en tiempo real

#### 3.1 Bot Telegram (telegram_bot.py)
- Framework: `python-telegram-bot` v20+ (async)
- Comandos: /start, /transcribe, /status
- Descarga de notas de voz a pending/
- Notificaciones de progreso cada 10%
- Rate limiting por usuario (5 archivos/hora)

#### 3.2 Bot Discord (discord_bot.py)
- Framework: `discord.py` v2+ (async)
- Listeners: mensajes de voz, archivos adjuntos
- Comandos slash: /transcribe, /status
- Embeds con barras de progreso
- Rate limiting global (10 simultáneos)

#### 3.3 Manejo de Errores y UX
- Mensajes claros de error
- Soporte para archivos >40MB (notificación de chunking)
- Cancelación de jobs en curso
- Comando /status muestra colas

---

### Fase 4: CLI y Tooling (1-2 días)

**Objetivo:** Interfaz de línea de comandos completa

#### 4.1 CLI (cli.py)
- Framework: `click` o `typer`
- Subcomandos:
  - `process`: Encola y/o procesa archivos
  - `status`: Muestra estado de colas y jobs
  - `config`: Gestiona configuración
  - `worker`: Inicia/detiene worker

#### 4.2 Logging y Métricas
- Logging estructurado (JSON opcional)
- Métricas: tiempo promedio, tasa de éxito, archivos procesados
- Export a CSV o visualización simple

#### 4.3 Utilidades
- Comando para limpiar cache antiguo
- Comando para reintentar jobs fallidos
- Comando para estadísticas

---

### Fase 5: Testing y Optimización (2 días)

**Objetivo:** Sistema estable y performante

#### 5.1 Testing
- Tests unitarios para database, queue, lock
- Tests de integración worker + whisper
- Tests e2e para bots (mock)

#### 5.2 Optimizaciones
- Cache de transcripciones por SHA256
- Compresión de audio antes de enviar
- Batch processing de múltiples archivos pequeños
- Graceful shutdown con cleanup

#### 5.3 Documentación
- Actualizar README.md
- Guía de instalación
- Guía de troubleshooting
- Ejemplos de uso

---

## Orden de Implementación Sugerido

| Paso | Fase | Descripción | Estimado |
|------|------|-------------|----------|
| 1 | Fase 0 | Infraestructura: .env, docker, migrations | 1-2 días |
| 2 | Fase 1 | Database y sistema de colas | 2 días |
| 3 | Fase 1 | File manager y audio processor | 1 día |
| 4 | Fase 2 | Whisper client y worker | 2 días |
| 5 | Fase 2 | Scripts de ejecución | 0.5 días |
| 6 | Fase 3 | Telegram bot | 1.5 días |
| 7 | Fase 3 | Discord bot | 1.5 días |
| 8 | Fase 4 | CLI y logging | 1-2 días |
| 9 | Fase 5 | Tests y docs | 2 días |

**Total estimado:** 12-14 días de trabajo

---

## Notas Técnicas

### Sistema de Lock
```
Archivo: inputs/.whisper.lock
Contenido: {"pid": 1234, "started": "2024-01-01T10:00:00Z"}
Timeout: 30 minutos (configurable)
```

### Estados de Job
```
pending → processing → completed
              ↓
           failed → pending (retry)
```

### Rate Limiting
- **Por usuario:** 5 archivos/hora (Telegram user_id, Discord user_id)
- **Global:** 10 procesos simultáneos máximo
- **Ventana:** Sliding window de 1 hora

### Chunking
- **Tamaño de chunk:** 10 minutos (600 segundos)
- **Overlap:** 2 segundos al final de cada chunk
- **Concatenación:** Unir transcripciones eliminando duplicados del overlap

---

## Agentes Disponibles

Este proyecto puede utilizar los siguientes agentes especializados ubicados en `~/.config/opencode/agentes/`:

### Agente Principal (Orquestador)

| Agente | Modelo | Descripción | Ruta |
|--------|--------|-------------|------|
| **data-engineer** | kimi-k2.5 | Ingeniero de Datos Senior que coordina workflows completos de desarrollo, orquestando subagentes según necesidad | `~/.config/opencode/agentes/data-engineer.md` |

### Subagentes Especializados

| Agente | Modelo | Descripción | Ruta | Uso Recomendado |
|--------|--------|-------------|------|-----------------|
| **tdd-architect** | kimi-k2.5 | Diseña suites de pruebas con TDD, asegurando documentación detallada en cada caso de prueba | `~/.config/opencode/agentes/tdd-architect.md` | Fase 5: Testing - Diseñar tests unitarios e integración |
| **python-coder** | qwen3-coder-next | Especialista en desarrollo Python que cumple estrictamente PEP 8 y estándares de tipado | `~/.config/opencode/agentes/python-coder.md` | Implementación de módulos src/*.py |
| **sql-specialist** | qwen3-coder-plus | Especialista en SQL que diseña, optimiza y ejecuta queries de alta performance | `~/.config/opencode/agentes/sql-specialist.md` | Fase 0.4: Schema de Base de Datos |
| **code-reviewer** | glm-5 | Revisa código Python buscando defectos, anti-patrones y oportunidades de mejora | `~/.config/opencode/agentes/code-reviewer.md` | Revisión final de cada módulo implementado |
| **git-manager** | MiniMax-M2.5 | Especialista en control de versiones, gestión de ramas y mensajes de commit semánticos | `~/.config/opencode/agentes/git-manager.md` | Gestión de commits y ramas durante el desarrollo |
| **config-guardian** | qwen3.5-plus | Agente especializado en automatización de PRs y monitoreo de repositorios | `~/.config/opencode/agentes/config-guardian.md` | Monitoreo de cambios en develop |

### Flujo de Uso de Agentes por Fase

**Fase 0 (Infraestructura):**
- `data-engineer` → Análisis y coordinación
- `sql-specialist` → Diseño del schema SQLite (Tarea 0.4)
- `git-manager` → Commits iniciales

**Fase 1 (Core Asíncrono):**
- `data-engineer` → Orquestación
- `tdd-architect` → Diseño de tests (Tarea 5.1)
- `python-coder` → Implementación de database.py, job_queue.py, file_manager.py, audio_processor.py
- `code-reviewer` → Revisión de cada módulo

**Fase 2 (Worker y Cliente):**
- `data-engineer` → Coordinación
- `python-coder` → Implementación de whisper_client.py, worker.py
- `code-reviewer` → Revisión

**Fase 3 (Bots):**
- `data-engineer` → Arquitectura de bots
- `python-coder` → Implementación de telegram_bot.py, discord_bot.py, progress_notifier.py
- `code-reviewer` → Revisión

**Fase 4 (CLI y Tooling):**
- `python-coder` → Implementación de cli.py, logger.py
- `code-reviewer` → Revisión

**Fase 5 (Testing y Optimización):**
- `tdd-architect` → Diseño completo de suite de tests
- `python-coder` → Implementación de tests/
- `code-reviewer` → Revisión final de cobertura

### Convenciones de Uso

1. **Invocación**: Usar `@nombre-agente` para invocar un agente específico
2. **Contexto**: Proporcionar el contexto completo del proyecto y la tarea actual
3. **Secuencia**: Seguir el orden TDD → Implementación → Revisión
4. **Commits**: Usar `git-manager` para todos los commits con mensajes semánticos
5. **Documentación**: Todos los agentes generan salida en español

---

## Decisiones Técnicas

### ¿Por qué SQLite y no Redis?
- Menor complejidad para self-hosting
- Single-node architecture (no necesitamos escalabilidad)
- Backup simple (archivo único)

### ¿Por qué Chunking y no Modelo más Grande?
- ggml-large-v3-turbo ya es óptimo en español
- Chunking mantiene calidad con overlap
- Evita cargar modelos múltiples en memoria

### ¿Por qué Docker Compose?
- Servidor whisper aislado y reproducible
- Healthcheck nativo
- Fácil reinicio en caso de crash

### ¿Por qué Progreso cada 10%?
- Balance entre UX y overhead de red
- Telegram/Discord soportan edición de mensajes
- No saturar al usuario ni la API

---

## Registro de Sesiones

| Fecha | Archivo | Descripción |
|-------|---------|-------------|
| 2026-03-13 | [20260313.md](20260313.md) | Revisión y reestructuración del documento de tareas. Análisis de asignación de agentes. Separación en ficheros independientes por fases. |
