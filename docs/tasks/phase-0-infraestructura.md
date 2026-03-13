# Fase 0: Infraestructura Segura

**Objetivo:** Establecer la base técnica y de seguridad del proyecto

**Tiempo Estimado:** 4-6 horas
**Dependencias:** Ninguna

---

## Tarea 0.1: Configuración de Seguridad

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
**Tiempo estimado:** 30 minutos

---

## Tarea 0.2: Docker Compose

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

## Tarea 0.3: Estructura de Carpetas

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
**Tiempo estimado:** 30 minutos

---

## Tarea 0.4: Schema de Base de Datos

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
**Agente Asignado:** @sql-specialist

---

## Agente Asignado

| Tarea | Agente | Justificación |
|-------|--------|---------------|
| 0.1 Configuración de Seguridad | Manual | Tareas de configuración de archivos |
| 0.2 Docker Compose | Manual / DevOps | Infraestructura de contenedores |
| 0.3 Estructura de Carpetas | Manual / Shell | Tareas de sistema de archivos |
| 0.4 Schema de Base de Datos | **@sql-specialist** | Diseño SQL, índices, constraints, optimización |

---

[Volver al índice](../tasks.md)
