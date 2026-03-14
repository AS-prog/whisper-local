# Agente: @phase1-auditor

**Tipo:** Subagente
**Modelo:** kimi-k2.5 (thinking habilitado)
**Ruta de configuración:** `~/.config/opencode/agents/phase1-auditor.md`
**Creado:** 2026-03-14

---

## Propósito

`@phase1-auditor` verifica que la implementación de los 4 módulos de Fase 1 cumpla la especificación técnica definida en `docs/tasks/phase-1-core.md`.

Su principio central es la **prueba en frío** (_cold testing_): el agente genera sus escenarios de verificación leyendo **únicamente la spec**, sin haber consultado el código del implementador. Esto garantiza que la auditoría sea verdaderamente independiente y no esté sesgada por las decisiones de implementación.

---

## Módulos Auditados

| Módulo | Tarea Spec | Aspectos Clave |
|--------|-----------|----------------|
| `src/database.py` | §1.1 | CRUD jobs, cache hit/miss, rate limiting, métricas |
| `src/job_queue.py` | §1.2 | Orden FIFO, prioridad pending>big_files, reintentos×3 |
| `src/file_manager.py` | §1.3 | Estados pending→processing→processed, locks por PID, SHA256 |
| `src/audio_processor.py` | §1.4 | Validación de formatos, umbral 40MB, overlap 2s en chunks |

---

## Protocolo de Auditoría (4 Fases)

### FASE A — Lectura de Especificación

- Lee exclusivamente `docs/tasks/phase-1-core.md`
- Para cada módulo documenta internamente:
  - Clases y firmas de métodos requeridas
  - Tipos de retorno esperados
  - Errores que deben lanzarse
  - Casos borde identificados en la spec

> **Restricción estricta:** En esta fase está **prohibido leer cualquier archivo de `src/`**.

### FASE B — Diseño de Escenarios en Frío

- Sin haber leído `src/`, escribe el script de verificación en `/tmp/audit_phase1_<TIMESTAMP>.py`
- Los escenarios se derivan exclusivamente de la spec
- Escenarios obligatorios mínimos por módulo:

#### database.py (8 escenarios)
1. `init_schema()` → retorna `bool`
2. `get_connection()` → retorna `sqlite3.Connection`
3. `create_job(...)` → retorna `int` (job_id)
4. `get_job(job_id)` → retorna `dict` con campos `id` y `status`
5. `update_job_status(job_id, status)` → sin excepción
6. `get_cached_transcription(hash_inexistente)` → retorna `None`
7. `cache_transcription(hash, texto)` → retorna `True`; posterior `get_cached_transcription` retorna el texto
8. `check_rate_limit(user_id, platform)` → retorna `bool`

#### job_queue.py (5 escenarios)
1. `enqueue(file_path)` × 2 en queue pending → retornan `int`
2. `dequeue('pending')` → respeta orden FIFO (created_at ASC)
3. 3 fallos consecutivos → `status = 'failed'` permanente (retry_count ≥ 3)
4. `get_queue_status()` → retorna `dict` con conteos
5. `register_progress_callback` + `notify_progress` → callback se invoca con `(job_id, progress)`

#### file_manager.py (6 escenarios)
1. `calculate_hash(archivo)` → string de 64 caracteres hexadecimales (SHA256)
2. Dos llamadas con el mismo archivo → mismo hash (idempotente)
3. `move_to_processing(ruta_en_pending)` → retorna nueva ruta; archivo existe allí; ruta contiene "processing"
4. `move_to_processed(ruta_en_processing)` → retorna nueva ruta; archivo existe allí
5. `acquire_lock()` primera vez → `True`; segunda vez inmediata → `False`
6. `release_lock()` + `acquire_lock()` → `True` de nuevo

#### audio_processor.py (5 escenarios)
1. `validate_audio(mp3)` → retorna `tuple[bool, str]`
2. `validate_audio(extension_no_soportada)` → `(False, mensaje_no_vacío)`
3. `needs_chunking(archivo_pequeño, max_size_mb=40)` → `False`
4. `needs_chunking(archivo, max_size_mb=0)` → `True` (simula >40MB)
5. `merge_transcriptions([...], [...])` → retorna `str`

> **Restricción estricta:** En esta fase también está **prohibido leer `src/`**.

### FASE C — Ejecución de Pruebas en Frío

Solo en este momento el agente puede:
1. Leer `src/database.py`, `src/job_queue.py`, `src/file_manager.py`, `src/audio_processor.py`
2. Ajustar imports del script si los nombres de clase difieren de la spec
3. Ejecutar el script via bash: `python /tmp/audit_phase1_<TIMESTAMP>.py`
4. Capturar stdout/stderr completo

### FASE D — Informe de Auditoría

El agente emite el siguiente informe estructurado:

```
INFORME DE AUDITORÍA — FASE 1
══════════════════════════════
Auditor: @phase1-auditor | Fecha: <TIMESTAMP>
Commit auditado: <GIT_HASH>

RESULTADO POR MÓDULO:
  database.py        ✅/❌  X/Y tests pasaron
  job_queue.py       ✅/❌  X/Y tests pasaron
  file_manager.py    ✅/❌  X/Y tests pasaron
  audio_processor.py ✅/❌  X/Y tests pasaron

VEREDICTO GLOBAL: APROBADO / REQUIERE CORRECCIONES

DESVIACIONES DE SPEC:
  [Lista de métodos con comportamiento incorrecto]
  Formato: [módulo] método() — esperado: X, obtenido: Y

RECOMENDACIÓN:
  - Si APROBADO      → invocar @git-manager para commit semántico
  - Si FALLA         → devolver a @python-coder con lista de fallos
```

---

## Script de Referencia

El archivo `tests/audit/cold_test_phase1.py` es el script de prueba de referencia con 25+ assertions. Puede ejecutarse directamente:

```bash
cd /path/to/whisper-local
python3 tests/audit/cold_test_phase1.py
```

**Comportamiento esperado con módulos completos:** exit code `0`, todos los checks en `✅`
**Comportamiento con stubs (estado actual):** exit code `1`, todos los checks en `❌` por `ImportError`

---

## Permisos del Agente

| Herramienta | Permitido |
|-------------|-----------|
| `read` | ✅ |
| `bash` | ✅ |
| `glob` | ✅ |
| `grep` | ✅ |
| `write` | ❌ |
| `edit` | ❌ |

El agente nunca modifica archivos del proyecto — solo lee y ejecuta.

---

## Flujo de Integración en Fase 1

```
@python-coder  → Implementa src/{database,job_queue,file_manager,audio_processor}.py
      ↓
@phase1-auditor → FASE A: Lee spec
                → FASE B: Diseña escenarios en frío
                → FASE C: Lee código + ejecuta tests
                → FASE D: Emite informe
      ↓
  APROBADO?
  ├── SÍ → @git-manager → commit semántico
  └── NO → @python-coder recibe lista de fallos → corrige → vuelve a auditoría
```

---

## Invocación

```
@phase1-auditor Audita la implementación de Fase 1.
Spec: docs/tasks/phase-1-core.md
Código: src/database.py, src/job_queue.py, src/file_manager.py, src/audio_processor.py
Proyecto: /Users/andresrsotelo_mm/projects/whisper-local
```

---

## Referencias

- Spec auditada: [`docs/tasks/phase-1-core.md`](../tasks/phase-1-core.md)
- Script de prueba: [`tests/audit/cold_test_phase1.py`](../../tests/audit/cold_test_phase1.py)
- Configuración del agente: `~/.config/opencode/agents/phase1-auditor.md`
- Contexto del proyecto: [`AGENTS.md`](../../AGENTS.md)
