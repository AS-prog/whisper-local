#!/usr/bin/env python3
"""
Script de auditoría en frío — Fase 2
Generado por: @phase2-auditor (tdd-architect)
Basado en: docs/tasks/phase-2-worker.md
Propósito: Verificar implementación contra spec SIN haber consultado el código.

Uso:
    cd /path/to/whisper-local
    python tests/audit/cold_test_phase2.py

Exit codes:
    0 → todos los tests pasan
    1 → hay fallos
"""

import sys
import os
import tempfile
import shutil
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
    print("  INFORME DE AUDITORÍA — FASE 2")
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
TMP_DIR = tempfile.mkdtemp(prefix="audit_phase2_")

# Crear un archivo de audio WAV mínimo para tests (44 bytes — cabecera válida)
DUMMY_WAV = os.path.join(TMP_DIR, "test_audio.wav")
with open(DUMMY_WAV, "wb") as f:
    # Cabecera WAV mínima: RIFF + tamaño + WAVE + fmt  + data
    f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
            b"\x01\x00\x01\x00\x80\x3e\x00\x00\x00\x7d\x00\x00"
            b"\x02\x00\x10\x00data\x00\x00\x00\x00")


# ─────────────────────────────────────────────
# MÓDULO: whisper_client.py
# Spec: docs/tasks/phase-2-worker.md § Tarea 2.1
# ─────────────────────────────────────────────
section("whisper_client.py")

try:
    from whisper_client import WhisperClient, WhisperError, TimeoutError, ParseError
    _wc_import_ok = True
except ImportError as e:
    _wc_import_ok = False
    check("whisper_client.py", "importar módulos", False, str(e))

if _wc_import_ok:
    # 2.1.1 Crear clase WhisperClient
    try:
        client = WhisperClient(host="localhost", port=8080)
        check("whisper_client.py", "instanciar WhisperClient(host, port)", True)
    except Exception as e:
        client = None
        check("whisper_client.py", "instanciar WhisperClient(host, port)", False, str(e))

    if client is not None:
        # 2.1.1 __init__ almacena host y port
        try:
            check("whisper_client.py", "__init__ almacena host",
                  hasattr(client, 'host') and client.host == "localhost")
            check("whisper_client.py", "__init__ almacena port",
                  hasattr(client, 'port') and client.port == 8080)
        except Exception as e:
            check("whisper_client.py", "__init__ almacena atributos", False, str(e))

        # 2.1.1 __init__ con timeout por defecto
        try:
            client_default = WhisperClient(host="localhost", port=8080)
            check("whisper_client.py", "__init__ timeout por defecto = 300",
                  hasattr(client_default, 'timeout') and client_default.timeout == 300)
        except Exception as e:
            check("whisper_client.py", "__init__ timeout por defecto", False, str(e))

        # 2.1.1 __init__ con timeout personalizado
        try:
            client_custom = WhisperClient(host="localhost", port=8080, timeout=600)
            check("whisper_client.py", "__init__ timeout personalizado",
                  client_custom.timeout == 600)
        except Exception as e:
            check("whisper_client.py", "__init__ timeout personalizado", False, str(e))

        # 2.1.2 health_check existe
        try:
            check("whisper_client.py", "método health_check() existe",
                  hasattr(client, 'health_check') and callable(getattr(client, 'health_check')))
        except Exception as e:
            check("whisper_client.py", "health_check() existe", False, str(e))

        # 2.1.2 is_server_ready existe
        try:
            check("whisper_client.py", "método is_server_ready() existe",
                  hasattr(client, 'is_server_ready') and callable(getattr(client, 'is_server_ready')))
        except Exception as e:
            check("whisper_client.py", "is_server_ready() existe", False, str(e))

        # 2.1.3 transcribe existe
        try:
            check("whisper_client.py", "método transcribe() existe",
                  hasattr(client, 'transcribe') and callable(getattr(client, 'transcribe')))
        except Exception as e:
            check("whisper_client.py", "transcribe() existe", False, str(e))

    # 2.1.4 Excepciones personalizadas
    try:
        check("whisper_client.py", "WhisperError hereda de Exception",
              issubclass(WhisperError, Exception))
    except Exception as e:
        check("whisper_client.py", "WhisperError definida", False, str(e))

    try:
        check("whisper_client.py", "TimeoutError hereda de WhisperError",
              issubclass(TimeoutError, WhisperError))
    except Exception as e:
        check("whisper_client.py", "TimeoutError definida", False, str(e))

    try:
        check("whisper_client.py", "ParseError hereda de WhisperError",
              issubclass(ParseError, WhisperError))
    except Exception as e:
        check("whisper_client.py", "ParseError definida", False, str(e))


# ─────────────────────────────────────────────
# MÓDULO: worker.py
# Spec: docs/tasks/phase-2-worker.md § Tarea 2.2
# ─────────────────────────────────────────────
section("worker.py")

try:
    from worker import Worker
    _worker_import_ok = True
except ImportError as e:
    _worker_import_ok = False
    check("worker.py", "importar módulo Worker", False, str(e))

if _worker_import_ok:
    # 2.2.1 Crear clase Worker con dependencias
    try:
        from database import Database
        from job_queue import JobQueue
        from file_manager import FileManager
        from audio_processor import AudioProcessor
        from whisper_client import WhisperClient
        
        # Crear dependencias mockeadas
        mock_db = MagicMock() if 'MagicMock' in globals() else object()
        mock_jq = MagicMock() if 'MagicMock' in globals() else object()
        mock_fm = MagicMock() if 'MagicMock' in globals() else object()
        mock_ap = MagicMock() if 'MagicMock' in globals() else object()
        mock_wc = MagicMock() if 'MagicMock' in globals() else object()
        
        # Si no hay MagicMock, crear mocks simples
        if not hasattr(mock_db, 'return_value'):
            class SimpleMock:
                pass
            mock_db = SimpleMock()
            mock_jq = SimpleMock()
            mock_fm = SimpleMock()
            mock_ap = SimpleMock()
            mock_wc = SimpleMock()
        
        worker = Worker(
            database=mock_db,
            job_queue=mock_jq,
            file_manager=mock_fm,
            audio_processor=mock_ap,
            whisper_client=mock_wc
        )
        check("worker.py", "instanciar Worker(dependencies)", True)
    except Exception as e:
        worker = None
        check("worker.py", "instanciar Worker(dependencies)", False, str(e))

    if worker is not None:
        # 2.2.1 Almacena dependencias
        try:
            check("worker.py", "__init__ almacena database",
                  hasattr(worker, 'database') and worker.database is mock_db)
            check("worker.py", "__init__ almacena job_queue",
                  hasattr(worker, 'job_queue') and worker.job_queue is mock_jq)
            check("worker.py", "__init__ almacena file_manager",
                  hasattr(worker, 'file_manager') and worker.file_manager is mock_fm)
            check("worker.py", "__init__ almacena audio_processor",
                  hasattr(worker, 'audio_processor') and worker.audio_processor is mock_ap)
            check("worker.py", "__init__ almacena whisper_client",
                  hasattr(worker, 'whisper_client') and worker.whisper_client is mock_wc)
        except Exception as e:
            check("worker.py", "__init__ almacena dependencias", False, str(e))

        # 2.2.2 start() existe
        try:
            check("worker.py", "método start() existe",
                  hasattr(worker, 'start') and callable(getattr(worker, 'start')))
        except Exception as e:
            check("worker.py", "start() existe", False, str(e))

        # 2.2.2 stop() existe
        try:
            check("worker.py", "método stop() existe",
                  hasattr(worker, 'stop') and callable(getattr(worker, 'stop')))
        except Exception as e:
            check("worker.py", "stop() existe", False, str(e))

        # 2.2.3 process_single_job() existe
        try:
            check("worker.py", "método process_single_job() existe",
                  hasattr(worker, 'process_single_job') and callable(getattr(worker, 'process_single_job')))
        except Exception as e:
            check("worker.py", "process_single_job() existe", False, str(e))

        # 2.2.2 run() existe
        try:
            check("worker.py", "método run() existe",
                  hasattr(worker, 'run') and callable(getattr(worker, 'run')))
        except Exception as e:
            check("worker.py", "run() existe", False, str(e))

        # 2.2.2 stop_requested inicialmente False
        try:
            check("worker.py", "_stop_requested inicialmente False",
                  hasattr(worker, '_stop_requested') and worker._stop_requested is False)
        except Exception as e:
            check("worker.py", "_stop_requested inicializado", False, str(e))

    # 2.2.2 start/stop ciclo de vida
    if worker is not None:
        try:
            # Detener si está corriendo
            if hasattr(worker, 'stop'):
                worker.stop()
            check("worker.py", "stop() ejecuta sin error", True)
        except Exception as e:
            check("worker.py", "stop() sin excepción", False, str(e))

    # 2.2.3 process_single_job retorna bool
    if worker is not None:
        try:
            from unittest.mock import MagicMock, patch
            
            # Crear mocks con comportamiento específico
            mock_fm = MagicMock()
            mock_fm.move_to_processing.return_value = "/processing/test.wav"
            mock_fm.calculate_hash.return_value = "abc123"
            
            mock_db = MagicMock()
            mock_db.get_cached_transcription.return_value = None
            
            mock_ap = MagicMock()
            mock_ap.validate_audio.return_value = (True, "")
            mock_ap.needs_chunking.return_value = False
            mock_ap.convert_to_wav.return_value = "/processing/test.wav"
            
            mock_wc = MagicMock()
            mock_wc.transcribe.return_value = "Texto"
            
            mock_jq = MagicMock()
            
            worker_test = Worker(
                database=mock_db,
                job_queue=mock_jq,
                file_manager=mock_fm,
                audio_processor=mock_ap,
                whisper_client=mock_wc
            )
            
            job = {"id": 1, "file_path": "/pending/test.wav", "user_id": "u1"}
            result = worker_test.process_single_job(job)
            
            check("worker.py", "process_single_job() retorna bool",
                  isinstance(result, bool), f"retornó {type(result).__name__}: {result}")
        except Exception as e:
            check("worker.py", "process_single_job() retorna bool", False, str(e))


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
