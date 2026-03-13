# Fase 1: Core Asíncrono

**Objetivo:** Implementar los módulos fundamentales del sistema

**Tiempo Estimado:** 14 horas
**Dependencias:** Fase 0 completada

---

## Tarea 1.1: Módulo de Base de Datos

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
**Agentes Asignados:** @sql-specialist + @python-coder

---

## Tarea 1.2: Sistema de Colas

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
**Agente Asignado:** @python-coder

---

## Tarea 1.3: Gestión de Archivos

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
**Agente Asignado:** @python-coder

---

## Tarea 1.4: Procesamiento de Audio

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
**Agente Asignado:** @python-coder

---

## Agentes Asignados

| Tarea | Agente | Justificación |
|-------|--------|---------------|
| 1.1 Módulo Database | **@sql-specialist** + **@python-coder** | SQL wrapper con type hints |
| 1.2 Sistema de Colas | **@python-coder** | Async, callbacks, priorización |
| 1.3 Gestión de Archivos | **@python-coder** | Locks, hashing SHA256, cleanup |
| 1.4 Procesamiento Audio | **@python-coder** | FFmpeg integration, chunking |

---

[Volver al índice](../tasks.md)
