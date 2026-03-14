#!/usr/bin/env python3
"""
Script de auditoría en frío — Fase 1
Generado por: @phase1-auditor
Basado en: docs/tasks/phase-1-core.md
Propósito: Verificar implementación contra spec SIN haber consultado el código.

Uso:
    cd /path/to/whisper-local
    python tests/audit/cold_test_phase1.py

Exit codes:
    0 → todos los tests pasan
    1 → hay fallos
"""

import sys
import os
import tempfile
import shutil
import hashlib
import time

# Añadir src/ al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# ─────────────────────────────────────────────
# Utilidades de reporte
# ─────────────────────────────────────────────
RESULTS: list[dict] = []

def check(modulo: str, nombre: str, condicion: bool, detalle: str = "") -> None:
    """Registra un resultado de test PASS/FAIL."""
    estado = "PASS" if condicion else "FAIL"
    simbolo = "✅" if condicion else "❌"
    linea = f"  {simbolo} [{modulo}] {nombre}"
    if not condicion and detalle:
        linea += f"\n      → {detalle}"
    print(linea)
    RESULTS.append({"modulo": modulo, "nombre": nombre, "ok": condicion, "detalle": detalle})

def section(titulo: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {titulo}")
    print(f"{'─' * 50}")

def resumen() -> int:
    """Imprime resumen y retorna exit code."""
    totales: dict[str, dict] = {}
    for r in RESULTS:
        m = r["modulo"]
        if m not in totales:
            totales[m] = {"pass": 0, "fail": 0}
        if r["ok"]:
            totales[m]["pass"] += 1
        else:
            totales[m]["fail"] += 1

    print(f"\n{'═' * 50}")
    print("  INFORME DE AUDITORÍA — FASE 1")
    print(f"{'═' * 50}")

    total_pass = sum(v["pass"] for v in totales.values())
    total_fail = sum(v["fail"] for v in totales.values())

    for modulo, counts in totales.items():
        icono = "✅" if counts["fail"] == 0 else "❌"
        total = counts["pass"] + counts["fail"]
        print(f"  {icono}  {modulo:<25} {counts['pass']}/{total} tests pasaron")

    print(f"\n  TOTAL: {total_pass} PASS / {total_fail} FAIL")

    if total_fail == 0:
        print("  VEREDICTO: APROBADO ✅")
        print("  → Invocar @git-manager para commit semántico")
    else:
        print("  VEREDICTO: REQUIERE CORRECCIONES ❌")
        print("  → Devolver a @python-coder con la lista de fallos")
        print("\n  DESVIACIONES DE SPEC:")
        for r in RESULTS:
            if not r["ok"]:
                print(f"    - [{r['modulo']}] {r['nombre']}")
                if r["detalle"]:
                    print(f"      {r['detalle']}")

    return 0 if total_fail == 0 else 1


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────
TMP_DIR = tempfile.mkdtemp(prefix="audit_phase1_")
DB_PATH = os.path.join(TMP_DIR, "test_whisper.db")

# Crear un archivo de audio WAV mínimo para tests (44 bytes — cabecera válida)
DUMMY_WAV = os.path.join(TMP_DIR, "test_audio.wav")
with open(DUMMY_WAV, "wb") as f:
    # Cabecera WAV mínima: RIFF + tamaño + WAVE + fmt  + data
    f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
            b"\x01\x00\x01\x00\x80\x3e\x00\x00\x00\x7d\x00\x00"
            b"\x02\x00\x10\x00data\x00\x00\x00\x00")

DUMMY_MP3 = os.path.join(TMP_DIR, "test_audio.mp3")
shutil.copy(DUMMY_WAV, DUMMY_MP3)

DUMMY_INVALID = os.path.join(TMP_DIR, "test_doc.pdf")
with open(DUMMY_INVALID, "wb") as f:
    f.write(b"%PDF-1.4 fake content")

# Carpeta base para FileManager
FM_BASE = os.path.join(TMP_DIR, "inputs")
os.makedirs(os.path.join(FM_BASE, "pending"), exist_ok=True)
os.makedirs(os.path.join(FM_BASE, "processing"), exist_ok=True)
os.makedirs(os.path.join(FM_BASE, "processed"), exist_ok=True)
os.makedirs(os.path.join(FM_BASE, "big_size"), exist_ok=True)

# Archivo de audio en pending para FileManager
FM_AUDIO = os.path.join(FM_BASE, "pending", "fm_audio.wav")
shutil.copy(DUMMY_WAV, FM_AUDIO)


# ─────────────────────────────────────────────
# MÓDULO: database.py
# Spec: docs/tasks/phase-1-core.md § Tarea 1.1
# ─────────────────────────────────────────────
section("database.py")

try:
    from database import Database
    _db_import_ok = True
except ImportError as e:
    _db_import_ok = False
    check("database.py", "importar módulo Database", False, str(e))

if _db_import_ok:
    try:
        db = Database(db_path=DB_PATH)
        check("database.py", "instanciar Database(db_path)", True)
    except Exception as e:
        db = None
        check("database.py", "instanciar Database(db_path)", False, str(e))

    if db is not None:
        # 1.1 init_schema
        try:
            result = db.init_schema()
            check("database.py", "init_schema() retorna bool", isinstance(result, bool),
                  f"retornó {type(result).__name__}: {result}")
        except Exception as e:
            check("database.py", "init_schema() sin excepción", False, str(e))

        # 1.1 get_connection
        try:
            import sqlite3
            conn = db.get_connection()
            check("database.py", "get_connection() retorna sqlite3.Connection",
                  isinstance(conn, sqlite3.Connection))
        except Exception as e:
            check("database.py", "get_connection() sin excepción", False, str(e))

        # 1.1.2 create_job
        job_id = None
        try:
            job_id = db.create_job(
                file_path="/tmp/audio.wav",
                file_hash="abc123",
                file_size_mb=5.0,
                queue="pending",
                user_id="user_001",
                platform="cli"
            )
            check("database.py", "create_job() retorna int",
                  isinstance(job_id, int), f"retornó {type(job_id).__name__}: {job_id}")
        except Exception as e:
            check("database.py", "create_job() sin excepción", False, str(e))

        # 1.1.2 get_job
        if job_id is not None:
            try:
                job = db.get_job(job_id)
                check("database.py", "get_job() retorna dict",
                      isinstance(job, dict), f"retornó {type(job).__name__}")
                if isinstance(job, dict):
                    check("database.py", "get_job() contiene 'id' y 'status'",
                          "id" in job and "status" in job,
                          f"keys disponibles: {list(job.keys())}")
            except Exception as e:
                check("database.py", "get_job() sin excepción", False, str(e))

        # 1.1.2 update_job_status
        if job_id is not None:
            try:
                db.update_job_status(job_id, "processing")
                check("database.py", "update_job_status() sin excepción", True)
            except Exception as e:
                check("database.py", "update_job_status() sin excepción", False, str(e))

        # 1.1.2 get_pending_jobs
        try:
            pending = db.get_pending_jobs()
            check("database.py", "get_pending_jobs() retorna list",
                  isinstance(pending, list), f"retornó {type(pending).__name__}")
        except Exception as e:
            check("database.py", "get_pending_jobs() sin excepción", False, str(e))

        # 1.1.3 cache miss
        try:
            cached = db.get_cached_transcription("hash_que_no_existe_xyz")
            check("database.py", "get_cached_transcription() cache miss → None",
                  cached is None, f"retornó: {repr(cached)}")
        except Exception as e:
            check("database.py", "get_cached_transcription() cache miss sin excepción", False, str(e))

        # 1.1.3 cache hit
        try:
            TEXT = "Hola mundo, esta es la transcripción."
            HASH = "sha256_test_hash_001"
            ok = db.cache_transcription(HASH, TEXT)
            check("database.py", "cache_transcription() retorna bool",
                  isinstance(ok, bool), f"retornó {type(ok).__name__}: {ok}")
            cached = db.get_cached_transcription(HASH)
            check("database.py", "get_cached_transcription() cache hit → texto",
                  cached == TEXT, f"esperado: {repr(TEXT)}, obtenido: {repr(cached)}")
        except Exception as e:
            check("database.py", "cache_transcription() + get_cached_transcription() sin excepción",
                  False, str(e))

        # 1.1.4 rate limit
        try:
            result = db.check_rate_limit("user_001", "telegram")
            check("database.py", "check_rate_limit() retorna bool",
                  isinstance(result, bool), f"retornó {type(result).__name__}: {result}")
        except Exception as e:
            check("database.py", "check_rate_limit() sin excepción", False, str(e))

        try:
            db.increment_rate_limit("user_001", "telegram")
            check("database.py", "increment_rate_limit() sin excepción", True)
        except Exception as e:
            check("database.py", "increment_rate_limit() sin excepción", False, str(e))

        # 1.1.5 métricas
        try:
            db.record_metric("processing_time", 2.5)
            check("database.py", "record_metric() sin excepción", True)
        except Exception as e:
            check("database.py", "record_metric() sin excepción", False, str(e))

        try:
            avg = db.get_average_processing_time()
            check("database.py", "get_average_processing_time() retorna float",
                  isinstance(avg, (int, float)), f"retornó {type(avg).__name__}: {avg}")
        except Exception as e:
            check("database.py", "get_average_processing_time() sin excepción", False, str(e))


# ─────────────────────────────────────────────
# MÓDULO: job_queue.py
# Spec: docs/tasks/phase-1-core.md § Tarea 1.2
# ─────────────────────────────────────────────
section("job_queue.py")

try:
    from job_queue import JobQueue
    _jq_import_ok = True
except ImportError as e:
    _jq_import_ok = False
    check("job_queue.py", "importar módulo JobQueue", False, str(e))

if _jq_import_ok and _db_import_ok:
    try:
        jq_db = Database(db_path=os.path.join(TMP_DIR, "jq_test.db"))
        jq_db.init_schema()
        jq = JobQueue(database=jq_db)
        check("job_queue.py", "instanciar JobQueue(database)", True)
    except Exception as e:
        jq = None
        check("job_queue.py", "instanciar JobQueue(database)", False, str(e))

    if jq is not None:
        # 1.2.1 enqueue
        jid1 = jid2 = jid3 = None
        try:
            jid1 = jq.enqueue("/tmp/audio1.wav", user_id="u1", platform="cli")
            check("job_queue.py", "enqueue() job1 retorna int",
                  isinstance(jid1, int), f"retornó {type(jid1).__name__}: {jid1}")
        except Exception as e:
            check("job_queue.py", "enqueue() job1 sin excepción", False, str(e))

        try:
            time.sleep(0.01)  # Garantizar orden FIFO por created_at
            jid2 = jq.enqueue("/tmp/audio2.wav", user_id="u2", platform="telegram")
            check("job_queue.py", "enqueue() job2 retorna int",
                  isinstance(jid2, int), f"retornó {type(jid2).__name__}: {jid2}")
        except Exception as e:
            check("job_queue.py", "enqueue() job2 sin excepción", False, str(e))

        # 1.2.2 dequeue orden FIFO
        if jid1 is not None and jid2 is not None:
            try:
                dequeued = jq.dequeue("pending")
                check("job_queue.py", "dequeue() retorna dict o None",
                      dequeued is None or isinstance(dequeued, dict),
                      f"retornó {type(dequeued).__name__}")
                if isinstance(dequeued, dict):
                    check("job_queue.py", "dequeue() orden FIFO — primer job es jid1",
                          dequeued.get("id") == jid1,
                          f"esperado id={jid1}, obtenido id={dequeued.get('id')}")
            except Exception as e:
                check("job_queue.py", "dequeue() sin excepción", False, str(e))

        # 1.2.3 reintentos — retry_count >= 3 → failed permanente
        try:
            jid_retry = jq.enqueue("/tmp/retry_audio.wav", user_id="u3", platform="cli")
            # Simular que ya tiene retry_count = 2 (próximo fallo → >= 3 → failed)
            # La spec dice: si retry_count < 3, volver a pending; si >= 3, failed permanente
            # Fallamos 3 veces consecutivas para llegar a failed
            for _ in range(3):
                deq = jq.dequeue("pending")
                if deq and deq.get("id") == jid_retry:
                    jq.complete_job(jid_retry, success=False, error="error de prueba")
            job_final = jq_db.get_job(jid_retry)
            if job_final:
                check("job_queue.py", "retry_count>=3 → status 'failed' permanente",
                      job_final.get("status") == "failed",
                      f"status actual: {job_final.get('status')}, retry_count: {job_final.get('retry_count')}")
            else:
                check("job_queue.py", "retry_count>=3 → job sigue existiendo en DB", False,
                      "get_job() retornó None")
        except Exception as e:
            check("job_queue.py", "lógica de reintentos sin excepción", False, str(e))

        # 1.2.1 get_queue_status
        try:
            status = jq.get_queue_status()
            check("job_queue.py", "get_queue_status() retorna dict",
                  isinstance(status, dict), f"retornó {type(status).__name__}")
        except Exception as e:
            check("job_queue.py", "get_queue_status() sin excepción", False, str(e))

        # 1.2.4 callbacks de progreso
        try:
            callback_llamado = []
            def mi_callback(job_id, progress):
                callback_llamado.append((job_id, progress))

            jq.register_progress_callback(jid2, mi_callback)
            jq.notify_progress(jid2, 50)
            check("job_queue.py", "register_progress_callback + notify_progress funcionan",
                  len(callback_llamado) == 1 and callback_llamado[0][1] == 50,
                  f"llamadas recibidas: {callback_llamado}")
        except Exception as e:
            check("job_queue.py", "callbacks de progreso sin excepción", False, str(e))


# ─────────────────────────────────────────────
# MÓDULO: file_manager.py
# Spec: docs/tasks/phase-1-core.md § Tarea 1.3
# ─────────────────────────────────────────────
section("file_manager.py")

try:
    from file_manager import FileManager
    _fm_import_ok = True
except ImportError as e:
    _fm_import_ok = False
    check("file_manager.py", "importar módulo FileManager", False, str(e))

if _fm_import_ok:
    try:
        fm = FileManager(base_path=FM_BASE)
        check("file_manager.py", "instanciar FileManager(base_path)", True)
    except Exception as e:
        fm = None
        check("file_manager.py", "instanciar FileManager(base_path)", False, str(e))

    if fm is not None:
        # 1.3.3 hash SHA256
        try:
            h1 = fm.calculate_hash(DUMMY_WAV)
            check("file_manager.py", "calculate_hash() retorna string",
                  isinstance(h1, str), f"retornó {type(h1).__name__}: {h1!r}")
            check("file_manager.py", "calculate_hash() — 64 caracteres hex (SHA256)",
                  len(h1) == 64 and all(c in "0123456789abcdef" for c in h1.lower()),
                  f"longitud={len(h1)}, valor={h1!r}")
        except Exception as e:
            check("file_manager.py", "calculate_hash() sin excepción", False, str(e))
            h1 = None

        # Idempotencia del hash
        if h1 is not None:
            try:
                h2 = fm.calculate_hash(DUMMY_WAV)
                check("file_manager.py", "calculate_hash() idempotente (mismo resultado)",
                      h1 == h2, f"primera={h1!r}, segunda={h2!r}")
            except Exception as e:
                check("file_manager.py", "calculate_hash() idempotente sin excepción", False, str(e))

        # 1.3.1 move_to_processing
        try:
            new_path = fm.move_to_processing(FM_AUDIO)
            check("file_manager.py", "move_to_processing() retorna str",
                  isinstance(new_path, str), f"retornó {type(new_path).__name__}")
            check("file_manager.py", "move_to_processing() — archivo existe en nueva ruta",
                  os.path.exists(new_path), f"ruta retornada: {new_path}")
            check("file_manager.py", "move_to_processing() — ruta contiene 'processing'",
                  "processing" in new_path, f"ruta: {new_path}")
        except Exception as e:
            new_path = None
            check("file_manager.py", "move_to_processing() sin excepción", False, str(e))

        # 1.3.1 move_to_processed
        if new_path and os.path.exists(new_path):
            try:
                proc_path = fm.move_to_processed(new_path)
                check("file_manager.py", "move_to_processed() retorna str",
                      isinstance(proc_path, str), f"retornó {type(proc_path).__name__}")
                check("file_manager.py", "move_to_processed() — archivo existe en nueva ruta",
                      os.path.exists(proc_path), f"ruta: {proc_path}")
            except Exception as e:
                check("file_manager.py", "move_to_processed() sin excepción", False, str(e))

        # 1.3.2 locks
        try:
            r1 = fm.acquire_lock(timeout_minutes=1)
            check("file_manager.py", "acquire_lock() primera vez → True",
                  r1 is True, f"retornó {r1!r}")
        except Exception as e:
            r1 = None
            check("file_manager.py", "acquire_lock() sin excepción", False, str(e))

        if r1:
            try:
                r2 = fm.acquire_lock(timeout_minutes=1)
                check("file_manager.py", "acquire_lock() segunda vez inmediata → False",
                      r2 is False, f"retornó {r2!r} (esperado False — lock ya tomado)")
            except Exception as e:
                check("file_manager.py", "segundo acquire_lock() sin excepción", False, str(e))

            try:
                released = fm.release_lock()
                check("file_manager.py", "release_lock() retorna bool",
                      isinstance(released, bool))
                r3 = fm.acquire_lock(timeout_minutes=1)
                check("file_manager.py", "acquire_lock() tras release → True",
                      r3 is True, f"retornó {r3!r}")
                fm.release_lock()  # Limpieza
            except Exception as e:
                check("file_manager.py", "release_lock() + re-acquire sin excepción", False, str(e))

        # 1.3.1 get_pending_files
        try:
            # Crear un archivo nuevo en pending para la búsqueda
            nuevo_pending = os.path.join(FM_BASE, "pending", "nuevo_audio.wav")
            shutil.copy(DUMMY_WAV, nuevo_pending)
            pending_files = fm.get_pending_files()
            check("file_manager.py", "get_pending_files() retorna list",
                  isinstance(pending_files, list), f"retornó {type(pending_files).__name__}")
        except Exception as e:
            check("file_manager.py", "get_pending_files() sin excepción", False, str(e))


# ─────────────────────────────────────────────
# MÓDULO: audio_processor.py
# Spec: docs/tasks/phase-1-core.md § Tarea 1.4
# ─────────────────────────────────────────────
section("audio_processor.py")

try:
    from audio_processor import AudioProcessor
    _ap_import_ok = True
except ImportError as e:
    _ap_import_ok = False
    check("audio_processor.py", "importar módulo AudioProcessor", False, str(e))

if _ap_import_ok:
    try:
        ap = AudioProcessor()
        check("audio_processor.py", "instanciar AudioProcessor()", True)
    except Exception as e:
        ap = None
        check("audio_processor.py", "instanciar AudioProcessor()", False, str(e))

    if ap is not None:
        # 1.4.1 get_file_size_mb
        try:
            size = ap.get_file_size_mb(DUMMY_WAV)
            check("audio_processor.py", "get_file_size_mb() retorna float",
                  isinstance(size, (int, float)), f"retornó {type(size).__name__}: {size}")
        except Exception as e:
            check("audio_processor.py", "get_file_size_mb() sin excepción", False, str(e))

        # 1.4.2 validar formato válido (mp3)
        try:
            valid, msg = ap.validate_audio(DUMMY_MP3)
            check("audio_processor.py", "validate_audio(mp3) retorna tuple (bool, str)",
                  isinstance(valid, bool) and isinstance(msg, str),
                  f"retornó ({type(valid).__name__}, {type(msg).__name__})")
            # Nota: puede retornar False por contenido inválido pero no por extensión
            # Lo importante es que no lance excepción y retorne (bool, str)
        except Exception as e:
            check("audio_processor.py", "validate_audio(mp3) sin excepción", False, str(e))

        # 1.4.2 validar formato inválido (pdf)
        try:
            valid_pdf, msg_pdf = ap.validate_audio(DUMMY_INVALID)
            check("audio_processor.py", "validate_audio(pdf) → (False, mensaje)",
                  valid_pdf is False and isinstance(msg_pdf, str) and len(msg_pdf) > 0,
                  f"retornó ({valid_pdf!r}, {msg_pdf!r})")
        except Exception as e:
            check("audio_processor.py", "validate_audio(pdf) sin excepción", False, str(e))

        # 1.4.4 needs_chunking — archivo pequeño → False
        try:
            needs = ap.needs_chunking(DUMMY_WAV, max_size_mb=40)
            check("audio_processor.py", "needs_chunking(archivo_pequeño) → False",
                  needs is False, f"retornó {needs!r}")
        except Exception as e:
            check("audio_processor.py", "needs_chunking(pequeño) sin excepción", False, str(e))

        # 1.4.4 needs_chunking — simular archivo grande (max_size_mb=0 → siempre True)
        try:
            needs_big = ap.needs_chunking(DUMMY_WAV, max_size_mb=0)
            check("audio_processor.py", "needs_chunking(max_size_mb=0) → True (simula >40MB)",
                  needs_big is True, f"retornó {needs_big!r}")
        except Exception as e:
            check("audio_processor.py", "needs_chunking(max_size_mb=0) sin excepción", False, str(e))

        # 1.4.3 convert_to_wav — solo verificar que el método existe y acepta los parámetros
        try:
            import inspect
            sig = inspect.signature(ap.convert_to_wav)
            params = list(sig.parameters.keys())
            check("audio_processor.py", "convert_to_wav() acepta (input_path, output_path=None)",
                  "input_path" in params,
                  f"parámetros encontrados: {params}")
        except Exception as e:
            check("audio_processor.py", "convert_to_wav() firma correcta", False, str(e))

        # 1.4.4 create_chunks — verificar firma
        try:
            sig = inspect.signature(ap.create_chunks)
            params = list(sig.parameters.keys())
            check("audio_processor.py", "create_chunks() acepta (file_path, chunk_duration=600)",
                  "file_path" in params and "chunk_duration" in params,
                  f"parámetros encontrados: {params}")
        except Exception as e:
            check("audio_processor.py", "create_chunks() firma correcta", False, str(e))

        # 1.4.5 merge_transcriptions — verificar firma
        try:
            sig = inspect.signature(ap.merge_transcriptions)
            params = list(sig.parameters.keys())
            check("audio_processor.py", "merge_transcriptions() acepta (transcriptions, overlaps)",
                  "transcriptions" in params and "overlaps" in params,
                  f"parámetros encontrados: {params}")
        except Exception as e:
            check("audio_processor.py", "merge_transcriptions() firma correcta", False, str(e))

        # 1.4.5 merge_transcriptions — lógica básica
        try:
            result = ap.merge_transcriptions(
                transcriptions=["Hola mundo.", "mundo. Cómo estás."],
                overlaps=["mundo."]
            )
            check("audio_processor.py", "merge_transcriptions() retorna str",
                  isinstance(result, str), f"retornó {type(result).__name__}: {result!r}")
        except Exception as e:
            check("audio_processor.py", "merge_transcriptions() sin excepción", False, str(e))


# ─────────────────────────────────────────────
# Limpieza
# ─────────────────────────────────────────────
try:
    shutil.rmtree(TMP_DIR, ignore_errors=True)
except Exception:
    pass

# ─────────────────────────────────────────────
# Resumen final
# ─────────────────────────────────────────────
exit_code = resumen()
sys.exit(exit_code)
