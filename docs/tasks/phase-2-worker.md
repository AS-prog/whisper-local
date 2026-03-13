# Fase 2: Worker y Cliente Whisper

**Objetivo:** Implementar el procesamiento asíncrono y comunicación con whisper

**Tiempo Estimado:** 7 horas
**Dependencias:** Fase 1 completada

---

## Tarea 2.1: Cliente Whisper

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
**Agente Asignado:** @python-coder

---

## Tarea 2.2: Worker

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
**Agentes Asignados:** @python-coder + @data-engineer

---

## Tarea 2.3: Scripts de Ejecución

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
**Agente Asignado:** Manual

---

## Agentes Asignados

| Tarea | Agente | Justificación |
|-------|--------|---------------|
| 2.1 Cliente Whisper | **@python-coder** | HTTP client, manejo de errores, retry logic |
| 2.2 Worker | **@python-coder** + **@data-engineer** | Orquestación compleja de jobs |
| 2.3 Scripts Shell | Manual | Bash scripting básico |

---

[Volver al índice](../tasks.md)
