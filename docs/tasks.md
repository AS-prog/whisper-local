# Documento de Tareas - whisper-local v2.1

**Fecha de creación:** 2026-03-13  
**Versión:** 2.1  
**Estado:** Planificación

---

## Índice de Fases

1. [Fase 0: Infraestructura Segura](#fase-0-infraestructura-segura)
2. [Fase 1: Core Asíncrono](#fase-1-core-asíncrono)
3. [Fase 2: Worker y Cliente Whisper](#fase-2-worker-y-cliente-whisper)
4. [Fase 3: Bots con Progreso](#fase-3-bots-con-progreso)
5. [Fase 4: CLI y Tooling](#fase-4-cli-y-tooling)
6. [Fase 5: Testing y Optimización](#fase-5-testing-y-optimización)

---

## Fase 0: Infraestructura Segura

### Tarea 0.1: Configuración de Seguridad

**Objetivo:** Migrar secrets a variables de entorno

- [ ] **0.1.1** Crear archivo `.env.example`
  - [ ] Añadir todas las variables documentadas
  - [ ] Incluir comentarios explicativos
  - [ ] Dejar valores vacíos o placeholder
  
- [ ] **0.1.2** Actualizar `.gitignore`
  - [ ] Añadir `.env`
  - [ ] Añadir `transcriptions/cache/`
  - [ ] Añadir `*.db` y `*.db-journal`
  
- [ ] **0.1.3** Crear script de validación
  - [ ] Verificar que `.env` existe
  - [ ] Verificar que variables obligatorias están seteadas
  - [ ] Salir con error code si falta configuración

**Archivos:** `.env.example`, `.gitignore`  
**Dependencias:** Ninguna  
**Tiempo estimado:** 30 minutos

---

### Tarea 0.2: Docker Compose

**Objetivo:** Contenerizar servidor whisper

- [ ] **0.2.1** Crear `docker-compose.yml`
  - [ ] Servicio `whisper` basado en imagen ubuntu:22.04
  - [ ] Volumen compartido para inputs/
  - [ ] Mapeo de puerto 8080
  - [ ] Healthcheck cada 30 segundos
  - [ ] Restart policy: unless-stopped
  - [ ] Resource limits (memory: 4GB, cpus: 2)
  
- [ ] **0.2.2** Crear Dockerfile (opcional, si whisper.cpp necesita build)
  - [ ] Clonar whisper.cpp
  - [ ] Compilar servidor
  - [ ] Copiar modelo al contenedor
  
- [ ] **0.2.3** Probar infraestructura
  - [ ] `docker-compose up -d`
  - [ ] Verificar healthcheck pasa
  - [ ] Probar endpoint /health
  - [ ] `docker-compose down`

**Archivos:** `docker-compose.yml`, `Dockerfile` (opcional)  
**Dependencias:** 0.1  
**Tiempo estimado:** 2-3 horas

---

### Tarea 0.3: Estructura de Carpetas

**Objetivo:** Preparar layout del proyecto

- [ ] **0.3.1** Crear directorios
  ```bash
  mkdir -p src/ scripts/ migrations/
  mkdir -p inputs/{pending,processing,processed,big_size}
  mkdir -p transcriptions/cache
  ```
  
- [ ] **0.3.2** Crear archivos iniciales
  - [ ] `src/__init__.py`
  - [ ] `src/database.py` (vacío inicial)
  - [ ] `src/job_queue.py` (vacío inicial)
  - [ ] `scripts/worker.sh` (shebang + chmod +x)
  - [ ] `scripts/nightly.sh` (shebang + chmod +x)
  
- [ ] **0.3.3** Backup código existente
  - [ ] Mover `transcriptions/app.py` a `backup/app-v1.py`
  - [ ] Verificar que no se pierde nada

**Archivos:** Múltiples  
**Dependencias:** Ninguna  
**Tiempo estimado:** 30 minutos

---

### Tarea 0.4: Schema de Base de Datos

**Objetivo:** Definir estructura SQLite

- [ ] **0.4.1** Crear `migrations/001_init.sql`
  ```sql
  -- Tabla jobs
  CREATE TABLE jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      file_path TEXT NOT NULL,
      file_hash TEXT UNIQUE,
      file_size_mb REAL,
      status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
      queue TEXT CHECK(queue IN ('pending', 'big_files')),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      started_at TIMESTAMP,
      completed_at TIMESTAMP,
      error_message TEXT,
      retry_count INTEGER DEFAULT 0,
      user_id TEXT,
      platform TEXT CHECK(platform IN ('telegram', 'discord', 'cli')),
      progress INTEGER DEFAULT 0,
      chunks_total INTEGER DEFAULT 1,
      chunks_completed INTEGER DEFAULT 0
  );
  
  -- Tabla cache
  CREATE TABLE transcription_cache (
      file_hash TEXT PRIMARY KEY,
      transcription TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      access_count INTEGER DEFAULT 1,
      last_accessed TIMESTAMP
  );
  
  -- Tabla rate limits
  CREATE TABLE rate_limits (
      user_id TEXT,
      platform TEXT,
      file_count INTEGER DEFAULT 1,
      window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (user_id, platform, window_start)
  );
  
  -- Tabla métricas
  CREATE TABLE metrics (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      metric_name TEXT,
      metric_value REAL,
      recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  -- Índices
  CREATE INDEX idx_jobs_status ON jobs(status);
  CREATE INDEX idx_jobs_queue ON jobs(queue);
  CREATE INDEX idx_jobs_user ON jobs(user_id);
  CREATE INDEX idx_cache_hash ON transcription_cache(file_hash);
  ```
  
- [ ] **0.4.2** Probar migración
  - [ ] `sqlite3 whisper.db < migrations/001_init.sql`
  - [ ] Verificar tablas creadas
  - [ ] Borrar archivo de prueba

**Archivos:** `migrations/001_init.sql`  
**Dependencias:** 0.3  
**Tiempo estimado:** 1 hora

---

## Fase 1: Core Asíncrono

### Tarea 1.1: Módulo de Base de Datos

**Objetivo:** Wrapper SQLite robusto

- [ ] **1.1.1** Crear clase `Database`
  ```python
  class Database:
      def __init__(self, db_path: str = "whisper.db")
      def init_schema(self) -> bool
      def get_connection(self) -> sqlite3.Connection
      def close(self)
  ```
  
- [ ] **1.1.2** Implementar métodos para tabla `jobs`
  - [ ] `create_job(file_path, file_hash, file_size_mb, queue, user_id, platform) -> int`
  - [ ] `get_job(job_id: int) -> dict`
  - [ ] `update_job_status(job_id, status, error_message=None)`
  - [ ] `get_pending_jobs(queue: str = 'pending', limit: int = 10) -> list`
  - [ ] `get_processing_jobs() -> list`
  - [ ] `update_job_progress(job_id, progress, chunks_completed=None)`
  - [ ] `get_failed_jobs_for_retry(max_retries=3) -> list`
  
- [ ] **1.1.3** Implementar métodos para cache
  - [ ] `get_cached_transcription(file_hash: str) -> str | None`
  - [ ] `cache_transcription(file_hash: str, transcription: str) -> bool`
  - [ ] `clean_old_cache(days: int = 30) -> int` (retorna cantidad borrada)
  
- [ ] **1.1.4** Implementar rate limiting
  - [ ] `check_rate_limit(user_id: str, platform: str, max_per_hour: int = 5) -> bool`
  - [ ] `increment_rate_limit(user_id: str, platform: str)`
  - [ ] `reset_rate_limit(user_id: str, platform: str)`
  
- [ ] **1.1.5** Implementar métricas
  - [ ] `record_metric(metric_name: str, metric_value: float)`
  - [ ] `get_average_processing_time(hours: int = 24) -> float`
  - [ ] `get_success_rate(hours: int = 24) -> float`

**Archivos:** `src/database.py`  
**Dependencias:** 0.4  
**Tiempo estimado:** 4 horas

---

### Tarea 1.2: Sistema de Colas

**Objetivo:** Gestión de jobs con prioridad

- [ ] **1.2.1** Crear clase `JobQueue`
  ```python
  class JobQueue:
      def __init__(self, database: Database)
      def enqueue(self, file_path: str, user_id: str = None, 
                  platform: str = 'cli') -> int
      def dequeue(self, queue: str = 'pending') -> dict | None
      def complete_job(self, job_id: int, success: bool, 
                       error: str = None)
      def get_queue_status(self) -> dict
      def get_job_progress(self, job_id: int) -> dict
  ```
  
- [ ] **1.2.2** Implementar lógica de priorización
  - [ ] Prioridad: pending > big_files
  - [ ] Orden: created_at ASC (FIFO)
  - [ ] Si big_files tiene >5 archivos, procesar uno cada 3 de pending
  
- [ ] **1.2.3** Implementar reintentos
  - [ ] Si job falla, incrementar retry_count
  - [ ] Si retry_count < 3, volver a pending
  - [ ] Esperar 5 min * retry_count antes de reintentar
  - [ ] Si retry_count >= 3, marcar como failed permanentemente
  
- [ ] **1.2.4** Implementar callbacks de progreso
  - [ ] `register_progress_callback(job_id, callback)`
  - [ ] `notify_progress(job_id, progress)`

**Archivos:** `src/job_queue.py`  
**Dependencias:** 1.1  
**Tiempo estimado:** 3 horas

---

### Tarea 1.3: Gestión de Archivos

**Objetivo:** Mover archivos y manejo de locks

- [ ] **1.3.1** Crear clase `FileManager`
  ```python
  class FileManager:
      def __init__(self, base_path: str = 'inputs')
      def calculate_hash(self, file_path: str) -> str
      def move_to_pending(self, source: str) -> str
      def move_to_processing(self, file_path: str) -> str
      def move_to_processed(self, file_path: str) -> str
      def move_to_big_size(self, file_path: str) -> str
      def get_pending_files(self) -> list
      def cleanup_processing(self, max_age_hours: int = 24)
  ```
  
- [ ] **1.3.2** Implementar sistema de lock
  - [ ] Crear `acquire_lock(timeout_minutes: int = 30) -> bool`
  - [ ] Crear `release_lock() -> bool`
  - [ ] Crear `is_locked() -> bool`
  - [ ] Crear `get_lock_info() -> dict | None`
  - [ ] Implementar timeout automático (borrar lock si >timeout)
  - [ ] Usar PID para identificar proceso dueño
  
- [ ] **1.3.3** Implementar hash SHA256
  - [ ] Calcular hash en chunks de 1MB (para archivos grandes)
  - [ ] Cache de hashes recientes (últimas 100)
  
- [ ] **1.3.4** Implementar cleanup
  - [ ] Archivos en processing por >24h vuelven a pending
  - [ ] Logs antiguos comprimir y archivar
  - [ ] Archivos en big_size procesados mover a processed

**Archivos:** `src/file_manager.py`  
**Dependencias:** Ninguna  
**Tiempo estimado:** 3 horas

---

### Tarea 1.4: Procesamiento de Audio

**Objetivo:** FFmpeg + chunking para archivos grandes

- [ ] **1.4.1** Crear clase `AudioProcessor`
  ```python
  class AudioProcessor:
      def __init__(self, ffmpeg_path: str = 'ffmpeg')
      def validate_audio(self, file_path: str) -> tuple[bool, str]
      def get_duration(self, file_path: str) -> float
      def get_file_size_mb(self, file_path: str) -> float
      def convert_to_wav(self, input_path: str, 
                        output_path: str = None) -> str
      def needs_chunking(self, file_path: str, 
                        max_size_mb: int = 40) -> bool
      def create_chunks(self, file_path: str, 
                       chunk_duration: int = 600) -> list[str]
      def merge_transcriptions(self, transcriptions: list[str],
                              overlaps: list[str]) -> str
  ```
  
- [ ] **1.4.2** Implementar validación
  - [ ] Verificar formato soportado (mp3, wav, ogg, m4a, flac)
  - [ ] Verificar archivo no corrupto (ffprobe)
  - [ ] Verificar duración > 1 segundo
  
- [ ] **1.4.3** Implementar conversión
  - [ ] Comando: `ffmpeg -i input -ar 16000 -ac 1 -c:a pcm_s16le output.wav`
  - [ ] Timeout de 5 minutos
  - [ ] Manejo de errores de FFmpeg
  
- [ ] **1.4.4** Implementar chunking
  - [ ] Calcular número de chunks: ceil(duration / 600)
  - [ ] Crear chunks con overlap de 2 segundos
  - [ ] Comando: `ffmpeg -i input -ss START -t DURATION -c copy chunk.wav`
  - [ ] Overlap: últimos 2 segundos se repiten en siguiente chunk
  - [ ] Guardar chunks en carpeta temporal
  
- [ ] **1.4.5** Implementar merge de transcripciones
  - [ ] Concatenar transcripciones
  - [ ] Eliminar duplicados del overlap (últimos 30 caracteres vs primeros 30)
  - [ ] Preservar timestamps relativos

**Archivos:** `src/audio_processor.py`  
**Dependencias:** Ninguna  
**Tiempo estimado:** 4 horas

---

## Fase 2: Worker y Cliente Whisper

### Tarea 2.1: Cliente Whisper

**Objetivo:** Comunicación HTTP con servidor

- [ ] **2.1.1** Crear clase `WhisperClient`
  ```python
  class WhisperClient:
      def __init__(self, host: str, port: int, 
                   timeout: int = 300)
      def is_server_ready(self, retries: int = 5) -> bool
      def transcribe(self, audio_path: str,
                    language: str = 'es') -> str
      def health_check(self) -> bool
  ```
  
- [ ] **2.1.2** Implementar health check
  - [ ] Endpoint: `GET http://host:port/health`
  - [ ] Retry con backoff: 1s, 2s, 4s, 8s, 16s
  - [ ] Timeout por intento: 5 segundos
  
- [ ] **2.1.3** Implementar transcripción
  - [ ] Endpoint: `POST http://host:port/inference`
  - [ ] Headers: `Content-Type: multipart/form-data`
  - [ ] Body: archivo + parámetros (language, task)
  - [ ] Parsear respuesta JSON
  - [ ] Extraer campo `text`
  - [ ] Manejar errores HTTP (4xx, 5xx)
  
- [ ] **2.1.4** Implementar manejo de errores
  - [ ] WhisperError: servidor no disponible
  - [ ] TimeoutError: transcripción tomó >5 min
  - [ ] ParseError: respuesta inválida

**Archivos:** `src/whisper_client.py`  
**Dependencias:** Ninguna  
**Tiempo estimado:** 2 horas

---

### Tarea 2.2: Worker

**Objetivo:** Procesador asíncrono de jobs

- [ ] **2.2.1** Crear clase `Worker`
  ```python
  class Worker:
      def __init__(self, database: Database, 
                   job_queue: JobQueue,
                   file_manager: FileManager,
                   audio_processor: AudioProcessor,
                   whisper_client: WhisperClient)
      def start(self)
      def stop(self)
      def process_single_job(self, job: dict) -> bool
      def run(self)  # Loop principal
  ```
  
- [ ] **2.2.2** Implementar loop principal
  - [ ] While not self._stop_requested:
    - [ ] Verificar lock
    - [ ] Adquirir lock
    - [ ] Obtener job de cola
    - [ ] Si hay job: procesar
    - [ ] Si no hay job: dormir 5 segundos
    - [ ] Liberar lock si no hay más jobs
  - [ ] Graceful shutdown con cleanup
  
- [ ] **2.2.3** Implementar procesamiento de job
  - [ ] Mover archivo a processing/
  - [ ] Calcular hash y verificar cache
  - [ ] Si está en cache: usar transcripción cacheada
  - [ ] Si no: proceder con whisper
  - [ ] Validar audio
  - [ ] Si necesita chunking:
    - [ ] Crear chunks
    - [ ] Actualizar job.chunks_total
    - [ ] Por cada chunk:
      - [ ] Convertir a WAV
      - [ ] Enviar a whisper
      - [ ] Actualizar progreso
    - [ ] Merge transcripciones
  - [ ] Si no necesita chunking:
    - [ ] Convertir a WAV
    - [ ] Enviar a whisper
  - [ ] Guardar transcripción en JSON
  - [ ] Mover archivo a processed/
  - [ ] Marcar job como completed
  - [ ] Guardar en cache
  
- [ ] **2.2.4** Implementar manejo de errores
  - [ ] Try/except en process_single_job
  - [ ] Si falla: marcar job como failed
  - [ ] Guardar error_message
  - [ ] Si retry_count < 3: reencolar
  - [ ] Notificar error a usuario (via callback)

**Archivos:** `src/worker.py`  
**Dependencias:** 1.1, 1.2, 1.3, 1.4, 2.1  
**Tiempo estimado:** 4 horas

---

### Tarea 2.3: Scripts de Ejecución

**Objetivo:** Scripts shell para cron y manual

- [ ] **2.3.1** Crear `scripts/worker.sh`
  ```bash
  #!/bin/bash
  # Inicia worker en background
  set -e
  
  VENV_PATH="/ruta/a/venv"
  PROJECT_PATH="/ruta/a/proyecto"
  LOG_FILE="$PROJECT_PATH/inputs/worker.log"
  
  source "$VENV_PATH/bin/activate"
  cd "$PROJECT_PATH"
  
  nohup python -m src.worker >> "$LOG_FILE" 2>&1 &
  echo $! > worker.pid
  echo "Worker iniciado con PID $(cat worker.pid)"
  ```
  
- [ ] **2.3.2** Crear `scripts/nightly.sh`
  ```bash
  #!/bin/bash
  # Encola archivos pendientes (no procesa)
  set -e
  
  # Similar setup que worker.sh
  # Pero ejecuta: python -m src.cli process --enqueue-only
  ```
  
- [ ] **2.3.3** Crear `scripts/stop-worker.sh`
  ```bash
  #!/bin/bash
  # Detiene worker gracefully
  if [ -f worker.pid ]; then
      kill -TERM $(cat worker.pid)
      rm worker.pid
  fi
  ```
  
- [ ] **2.3.4** Configurar cron
  - [ ] `crontab -e`
  - [ ] Añadir: `0 2 * * * /ruta/scripts/nightly.sh`
  - [ ] Probar: Ejecutar manualmente

**Archivos:** `scripts/worker.sh`, `scripts/nightly.sh`, `scripts/stop-worker.sh`  
**Dependencias:** 2.2  
**Tiempo estimado:** 1 hora

---

## Fase 3: Bots con Progreso

### Tarea 3.1: Bot Telegram

**Objetivo:** Bot asíncrono con notificaciones

- [ ] **3.1.1** Configurar dependencias
  - [ ] Añadir `python-telegram-bot>=20.0` a requirements.txt
  - [ ] Instalar: `pip install python-telegram-bot`
  
- [ ] **3.1.2** Crear clase `TelegramBot`
  ```python
  class TelegramBot:
      def __init__(self, token: str, job_queue: JobQueue,
                   database: Database)
      async def start(self)
      async def stop(self)
      async def handle_voice(self, update: Update, 
                            context: ContextTypes.DEFAULT_TYPE)
      async def handle_status(self, update: Update,
                             context: ContextTypes.DEFAULT_TYPE)
      async def handle_transcribe(self, update: Update,
                                 context: ContextTypes.DEFAULT_TYPE)
      async def send_progress(self, chat_id: int, job_id: int,
                             progress: int)
  ```
  
- [ ] **3.1.3** Implementar comandos
  - [ ] `/start`: Mensaje de bienvenida + instrucciones
  - [ ] `/status`: Muestra colas y jobs del usuario
  - [ ] `/transcribe`: Fuerza procesamiento inmediato
  
- [ ] **3.1.4** Implementar manejo de notas de voz
  - [ ] Descargar archivo con `update.message.voice.get_file()`
  - [ ] Guardar en `inputs/pending/`
  - [ ] Verificar rate limit
  - [ ] Crear job en cola
  - [ ] Responder: "Archivo recibido. Posición en cola: X"
  
- [ ] **3.1.5** Implementar notificaciones de progreso
  - [ ] Registrar callback en JobQueue
  - [ ] Cuando progreso cambia:
    - [ ] Si 0%: "Procesando..."
    - [ ] Si cada 10%: Editar mensaje con "Progreso: X%"
    - [ ] Si 100%: "Completado!" + enviar transcripción
  - [ ] Manejar mensajes largos (>4096 caracteres)
    - [ ] Dividir en múltiples mensajes
    - [ ] O enviar como archivo
  
- [ ] **3.1.6** Implementar rate limiting
  - [ ] Antes de crear job: verificar rate limit
  - [ ] Si excedido: "Límite de 5 archivos/hora alcanzado"
  - [ ] Reset automático cada hora

**Archivos:** `src/telegram_bot.py`  
**Dependencias:** 1.2  
**Tiempo estimado:** 4 horas

---

### Tarea 3.2: Bot Discord

**Objetivo:** Bot asíncrono con embeds

- [ ] **3.2.1** Configurar dependencias
  - [ ] Añadir `discord.py>=2.0` a requirements.txt
  - [ ] Instalar: `pip install discord.py`
  
- [ ] **3.2.2** Crear clase `DiscordBot`
  ```python
  class DiscordBot(discord.Client):
      def __init__(self, token: str, job_queue: JobQueue,
                   database: Database)
      async def on_ready(self)
      async def on_message(self, message: discord.Message)
      async def handle_attachment(self, message: discord.Message)
      async def handle_voice(self, message: discord.Message)
      async def slash_status(self, interaction: discord.Interaction)
      async def slash_transcribe(self, interaction: discord.Interaction)
      async def send_progress_embed(self, channel_id: int,
                                   job_id: int, progress: int)
  ```
  
- [ ] **3.2.3** Implementar listeners
  - [ ] `on_ready()`: Loguear conexión exitosa
  - [ ] `on_message()`:
    - [ ] Ignorar mensajes de bots
    - [ ] Si tiene attachments: procesar
    - [ ] Si es mensaje de voz: procesar
    
- [ ] **3.2.4** Implementar comandos slash
  - [ ] `/status`: Embed con estado de colas
  - [ ] `/transcribe`: Embed para forzar procesamiento
  - [ ] Registrar comandos en `setup_hook()`
  
- [ ] **3.2.5** Implementar manejo de archivos
  - [ ] Descargar attachment con `attachment.save()`
  - [ ] Validar formato de audio
  - [ ] Guardar en pending/
  - [ ] Crear job
  
- [ ] **3.2.6** Implementar notificaciones
  - [ ] Crear embed con barra de progreso
  - [ ] Editar embed cada 10%
  - [ ] Color del embed: azul (procesando), verde (completado), rojo (error)
  - [ ] Enviar transcripción como mensaje separado o archivo
  
- [ ] **3.2.7** Implementar rate limiting global
  - [ ] Semáforo: máximo 10 jobs simultáneos
  - [ ] Cola de espera si se excede

**Archivos:** `src/discord_bot.py`  
**Dependencias:** 1.2  
**Tiempo estimado:** 4 horas

---

### Tarea 3.3: Integración de Progreso

**Objetivo:** Sistema unificado de notificaciones

- [ ] **3.3.1** Crear `ProgressNotifier`
  ```python
  class ProgressNotifier:
      def __init__(self, database: Database)
      def register_job(self, job_id: int, platform: str,
                      user_id: str, message_id: str = None)
      def update_progress(self, job_id: int, progress: int)
      def notify_completion(self, job_id: int, 
                           transcription: str)
      def notify_error(self, job_id: int, error: str)
  ```
  
- [ ] **3.3.2** Integrar con JobQueue
  - [ ] Cuando job cambia a processing: notificar inicio
  - [ ] Cuando progreso se actualiza: notificar
  - [ ] Cuando job completa: notificar resultado
  
- [ ] **3.3.3** Manejo de mensajes largos
  - [ ] Telegram: dividir en chunks de 4096 caracteres
  - [ ] Discord: dividir en chunks de 2000 caracteres
  - [ ] Opción: enviar como archivo .txt si >10 chunks

**Archivos:** `src/progress_notifier.py`  
**Dependencias:** 3.1, 3.2  
**Tiempo estimado:** 2 horas

---

## Fase 4: CLI y Tooling

### Tarea 4.1: CLI

**Objetivo:** Interfaz de línea de comandos

- [ ] **4.1.1** Configurar dependencias
  - [ ] Añadir `click` o `typer` a requirements.txt
  - [ ] Instalar dependencia elegida
  
- [ ] **4.1.2** Crear `cli.py`
  ```python
  import click
  
  @click.group()
  def cli():
      pass
  
  @cli.command()
  @click.option('--enqueue-only', is_flag=True)
  @click.argument('files', nargs=-1)
  def process(files, enqueue_only):
      pass
  
  @cli.command()
  def status():
      pass
  
  @cli.command()
  def config():
      pass
  
  @cli.command()
  @click.option('--start/--stop', default=True)
  def worker(start):
      pass
  
  if __name__ == '__main__':
      cli()
  ```
  
- [ ] **4.1.3** Implementar `process`
  - [ ] Sin argumentos: procesar pending/
  - [ ] Con archivos: encolar archivos específicos
  - [ ] `--enqueue-only`: solo encolar, no procesar
  
- [ ] **4.1.4** Implementar `status`
  - [ ] Mostrar tabla: Queue | Pending | Processing | Completed
  - [ ] Mostrar últimos 10 jobs
  - [ ] Mostrar métricas del día
  
- [ ] **4.1.5** Implementar `config`
  - [ ] `config init`: Crear .env desde .env.example
  - [ ] `config show`: Mostrar configuración actual (sin tokens)
  - [ ] `config validate`: Verificar que todo esté configurado
  
- [ ] **4.1.6** Implementar `worker`
  - [ ] `worker --start`: Ejecutar `scripts/worker.sh`
  - [ ] `worker --stop`: Ejecutar `scripts/stop-worker.sh`
  - [ ] `worker --status`: Verificar si está corriendo

**Archivos:** `src/cli.py`  
**Dependencias:** Todas las anteriores  
**Tiempo estimado:** 3 horas

---

### Tarea 4.2: Logging y Métricas

**Objetivo:** Observabilidad del sistema

- [ ] **4.2.1** Configurar logging
  - [ ] Crear `logger.py` con configuración JSON
  - [ ] Logs estructurados: timestamp, level, component, message
  - [ ] Rotación de logs: 10MB por archivo, máximo 5 archivos
  - [ ] Niveles: DEBUG (dev), INFO (prod), ERROR (siempre)
  
- [ ] **4.2.2** Añadir métricas
  - [ ] Tiempo promedio de procesamiento
  - [ ] Tasa de éxito/fallo
  - [ ] Archivos procesados por día
  - [ ] Uso de cache (hits/misses)
  
- [ ] **4.2.3** Exportar métricas
  - [ ] Comando: `whisper-local metrics --days 7 --format csv`
  - [ ] Formato: CSV o JSON
  - [ ] Incluir: fecha, métrica, valor

**Archivos:** `src/logger.py`, modificar `src/database.py`  
**Dependencias:** 1.1  
**Tiempo estimado:** 2 horas

---

### Tarea 4.3: Utilidades de Mantenimiento

**Objetivo:** Herramientas de administración

- [ ] **4.3.1** Comando `cleanup`
  - [ ] `cleanup cache --days 30`: Borrar cache antiguo
  - [ ] `cleanup logs --days 7`: Archivar logs antiguos
  - [ ] `cleanup processing`: Resetear archivos stuck
  
- [ ] **4.3.2** Comando `retry`
  - [ ] `retry --failed`: Reencolar todos los failed
  - [ ] `retry --job-id ID`: Reencolar job específico
  
- [ ] **4.3.3** Comando `stats`
  - [ ] `stats --today`: Resumen del día
  - [ ] `stats --week`: Resumen de la semana
  - [ ] Mostrar: procesados, fallidos, tiempo promedio, usuarios activos

**Archivos:** `src/cli.py`  
**Dependencias:** 4.1  
**Tiempo estimado:** 2 horas

---

## Fase 5: Testing y Optimización

### Tarea 5.1: Tests Unitarios

**Objetivo:** Cobertura de código core

- [ ] **5.1.1** Configurar pytest
  - [ ] Añadir `pytest`, `pytest-asyncio`, `pytest-cov` a requirements.txt
  - [ ] Crear `pytest.ini`
  - [ ] Crear `tests/` directory
  
- [ ] **5.1.2** Tests para `database.py`
  - [ ] Setup/teardown de DB en memoria
  - [ ] Test CRUD de jobs
  - [ ] Test cache
  - [ ] Test rate limiting
  
- [ ] **5.1.3** Tests para `job_queue.py`
  - [ ] Test enqueue/dequeue
  - [ ] Test priorización
  - [ ] Test reintentos
  
- [ ] **5.1.4** Tests para `file_manager.py`
  - [ ] Test locks
  - [ ] Test hash
  - [ ] Test cleanup
  
- [ ] **5.1.5** Tests para `audio_processor.py`
  - [ ] Mock ffmpeg
  - [ ] Test validación
  - [ ] Test chunking
  
- [ ] **5.1.6** Ejecutar tests
  - [ ] `pytest tests/ -v --cov=src`
  - [ ] Meta: >80% cobertura

**Archivos:** `tests/test_*.py`, `pytest.ini`  
**Dependencias:** Fases 1-2  
**Tiempo estimado:** 4 horas

---

### Tarea 5.2: Tests de Integración

**Objetivo:** Flujo end-to-end

- [ ] **5.2.1** Tests para worker
  - [ ] Crear archivo de audio de prueba
  - [ ] Encolar
  - [ ] Ejecutar worker
  - [ ] Verificar resultado
  
- [ ] **5.2.2** Mock de servidor whisper
  - [ ] Crear servidor HTTP mock
  - [ ] Responder con transcripción fija
  - [ ] Test worker completo con mock
  
- [ ] **5.2.3** Tests e2e para bots (opcional)
  - [ ] Mock de APIs de Telegram/Discord
  - [ ] Enviar mensaje de prueba
  - [ ] Verificar que job se crea

**Archivos:** `tests/integration/`, `tests/mocks/`  
**Dependencias:** 5.1  
**Tiempo estimado:** 3 horas

---

### Tarea 5.3: Optimizaciones

**Objetivo:** Mejoras de performance

- [ ] **5.3.1** Cache de transcripciones
  - [ ] Implementar tabla `transcription_cache`
  - [ ] Calcular SHA256 de archivo antes de procesar
  - [ ] Si hash existe: retornar transcripción cacheada
  - [ ] Actualizar access_count y last_accessed
  
- [ ] **5.3.2** Batch processing
  - [ ] Si hay múltiples archivos pequeños (<5MB):
  - [ ] Procesar en paralelo (hasta 3 simultáneos)
  - [ ] Cuidado con rate limits de whisper
  
- [ ] **5.3.3** Compresión de audio
  - [ ] Antes de enviar a whisper, comprimir si >20MB
  - [ ] Usar opus o mp3 con bitrate reducido
  - [ ] Verificar que calidad sigue siendo aceptable
  
- [ ] **5.3.4** Graceful shutdown
  - [ ] Capturar SIGTERM y SIGINT
  - [ ] Terminar job actual
  - [ ] Guardar estado de jobs incompletos
  - [ ] Liberar lock
  - [ ] Cerrar conexiones

**Archivos:** Modificar `src/worker.py`, `src/database.py`  
**Dependencias:** Fases 1-3  
**Tiempo estimado:** 3 horas

---

### Tarea 5.4: Documentación

**Objetivo:** Guías completas

- [ ] **5.4.1** Actualizar `README.md`
  - [ ] Instalación paso a paso
  - [ ] Configuración de .env
  - [ ] Uso básico (CLI)
  - [ ] Configuración de bots
  - [ ] Troubleshooting común
  
- [ ] **5.4.2** Crear `docs/INSTALL.md`
  - [ ] Requisitos del sistema
  - [ ] Instalación de Docker
  - [ ] Instalación de Python y dependencias
  - [ ] Configuración de cron
  
- [ ] **5.4.3** Crear `docs/API.md`
  - [ ] Documentar clases principales
  - [ ] Ejemplos de uso
  - [ ] Diagrama de arquitectura
  
- [ ] **5.4.4** Actualizar `AGENTS.md`
  - [ ] Nueva estructura de carpetas
  - [ ] Comandos actualizados
  - [ ] Convenciones de código
  
- [ ] **5.4.5** Crear `docs/TROUBLESHOOTING.md`
  - [ ] Servidor whisper no responde
  - [ ] Archivos stuck en processing
  - [ ] Rate limiting excedido
  - [ ] Docker issues
  - [ ] Cómo leer logs

**Archivos:** `README.md`, `docs/*.md`  
**Dependencias:** Todas las anteriores  
**Tiempo estimado:** 3 horas

---

## Resumen de Tiempo Estimado

| Fase | Tareas | Tiempo Estimado | Dependencias |
|------|--------|-----------------|--------------|
| Fase 0 | 4 tareas | 4-6 horas | - |
| Fase 1 | 4 tareas | 14 horas | Fase 0 |
| Fase 2 | 3 tareas | 7 horas | Fase 1 |
| Fase 3 | 3 tareas | 10 horas | Fase 2 |
| Fase 4 | 3 tareas | 7 horas | Fase 3 |
| Fase 5 | 4 tareas | 13 horas | Fases 1-4 |
| **Total** | **21 tareas** | **~55 horas** | - |

**Nota:** Los tiempos son estimaciones. Puede variar según:
- Experiencia previa con las librerías
- Complejidad inesperada
- Tiempo de debugging
- Revisión y refactorización

---

## Definición de "Hecho" (Definition of Done)

Para cada tarea, debe cumplirse:

1. ✅ Código escrito y funcional
2. ✅ Tests unitarios (si aplica)
3. ✅ Documentación de funciones (docstrings)
4. ✅ Probado manualmente
5. ✅ Sin errores de linting (`flake8`, `black`)
6. ✅ Commit con mensaje descriptivo
7. ✅ Actualizado `docs/tasks.md` (marcar como completado)

---

## Notas de Implementación

### Orden de Prioridad
Si el tiempo es limitado, priorizar en este orden:

1. **Must Have (MVP):**
   - Fase 0: Seguridad (.env)
   - Fase 1: Database, Queue, FileManager básico
   - Fase 2: Worker básico sin chunking
   - Fase 3: Telegram bot básico
   - Fase 4: CLI básico (process, status)

2. **Should Have:**
   - Fase 1: Chunking, AudioProcessor completo
   - Fase 2: Scripts, Docker
   - Fase 3: Discord bot
   - Fase 4: Métricas, utilidades

3. **Nice to Have:**
   - Fase 3: Notificaciones de progreso detalladas
   - Fase 4: Config management
   - Fase 5: Tests completos, optimizaciones avanzadas

### Dependencias Externas
- Docker y Docker Compose
- FFmpeg instalado en sistema
- Python 3.9+
- Cuenta de Telegram Bot
- Cuenta de Discord Bot
- Modelo whisper descargado

### Convenciones
- **Nombres:** snake_case para variables/funciones, PascalCase para clases
- **Imports:** Ordenar alfabéticamente, agrupar por stdlib, third-party, local
- **Tipado:** Usar type hints en todas las funciones públicas
- **Async:** Todas las operaciones de red deben ser async
- **Errores:** Usar excepciones personalizadas, no retornar None para errores

---

**Última actualización:** 2026-03-13  
**Responsable:** @usuario  
**Estado:** En planificación
