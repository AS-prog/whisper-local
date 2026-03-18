#!/usr/bin/env python3
"""
Tests unitarios para Worker — Fase 2
Generado por: @tdd-architect
Basado en: docs/tasks/phase-2-worker.md § Tarea 2.2

Uso:
    cd /path/to/whisper-local
    python -m pytest tests/test_worker.py -v
"""

import sys
import os
import tempfile
import time
import pytest
from unittest.mock import Mock, patch, MagicMock, call

# Añadir src/ al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestWorkerInit:
    """Tests para inicialización de Worker."""

    def test_init_requires_all_dependencies(self):
        """
        ESCENARIO: Crear Worker con todas las dependencias requeridas.
        COMPORTAMIENTO: Almacena referencias a todas las dependencias.
        PROPÓSITO: Inicializar worker con componentes necesarios.
        """
        from worker import Worker
        
        mock_db = MagicMock()
        mock_jq = MagicMock()
        mock_fm = MagicMock()
        mock_ap = MagicMock()
        mock_wc = MagicMock()
        
        worker = Worker(
            database=mock_db,
            job_queue=mock_jq,
            file_manager=mock_fm,
            audio_processor=mock_ap,
            whisper_client=mock_wc
        )
        
        assert worker.database is mock_db
        assert worker.job_queue is mock_jq
        assert worker.file_manager is mock_fm
        assert worker.audio_processor is mock_ap
        assert worker.whisper_client is mock_wc

    def test_init_sets_stop_requested_false(self):
        """
        ESCENARIO: Inicialización del worker.
        COMPORTAMIENTO: _stop_requested es False inicialmente.
        PROPÓSITO: Worker arranca en estado activo.
        """
        from worker import Worker
        
        worker = Worker(
            database=MagicMock(),
            job_queue=MagicMock(),
            file_manager=MagicMock(),
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        assert worker._stop_requested is False


class TestWorkerStart:
    """Tests para método start."""

    def test_start_creates_thread(self):
        """
        ESCENARIO: Llamar a start() en worker.
        COMPORTAMIENTO: Crea e inicia un thread que ejecuta run().
        PROPÓSITO: Iniciar procesamiento asíncrono.
        """
        from worker import Worker
        
        worker = Worker(
            database=MagicMock(),
            job_queue=MagicMock(),
            file_manager=MagicMock(),
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        with patch('threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            
            worker.start()
            
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()

    def test_start_stores_thread_reference(self):
        """
        ESCENARIO: Llamar a start() exitosamente.
        COMPORTAMIENTO: Guarda referencia al thread creado.
        PROPÓSITO: Permitir gestión del thread.
        """
        from worker import Worker
        
        worker = Worker(
            database=MagicMock(),
            job_queue=MagicMock(),
            file_manager=MagicMock(),
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        with patch('threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            
            worker.start()
            
            assert worker._thread is mock_thread_instance


class TestWorkerStop:
    """Tests para método stop."""

    def test_stop_sets_stop_requested_true(self):
        """
        ESCENARIO: Llamar a stop() en worker corriendo.
        COMPORTAMIENTO: Establece _stop_requested a True.
        PROPÓSITO: Señalizar graceful shutdown.
        """
        from worker import Worker
        
        worker = Worker(
            database=MagicMock(),
            job_queue=MagicMock(),
            file_manager=MagicMock(),
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        worker.stop()
        
        assert worker._stop_requested is True

    def test_stop_waits_for_thread(self):
        """
        ESCENARIO: Llamar a stop() con thread activo.
        COMPORTAMIENTO: Llama a join() en el thread.
        PROPÓSITO: Esperar que el worker termine limpiamente.
        """
        from worker import Worker
        
        worker = Worker(
            database=MagicMock(),
            job_queue=MagicMock(),
            file_manager=MagicMock(),
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        mock_thread = MagicMock()
        worker._thread = mock_thread
        
        worker.stop()
        
        mock_thread.join.assert_called_once()


class TestWorkerRun:
    """Tests para loop principal run()."""

    @patch('worker.time.sleep')
    def test_run_processes_jobs_until_stopped(self, mock_sleep):
        """
        ESCENARIO: Loop principal con jobs disponibles.
        COMPORTAMIENTO: Procesa jobs mientras no se solicite stop.
        PROPÓSITO: Procesamiento continuo de jobs.
        """
        from worker import Worker
        
        mock_jq = MagicMock()
        mock_jq.dequeue.return_value = {"id": 1, "file_path": "/test.wav"}
        
        worker = Worker(
            database=MagicMock(),
            job_queue=mock_jq,
            file_manager=MagicMock(),
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        # Simular que procesa 3 jobs y luego se detiene
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 3:
                worker._stop_requested = True
            return True
        
        with patch.object(worker, 'process_single_job', side_effect=side_effect):
            worker.run()
        
        assert call_count[0] == 3

    @patch('worker.time.sleep')
    def test_run_sleeps_when_no_jobs(self, mock_sleep):
        """
        ESCENARIO: No hay jobs en la cola.
        COMPORTAMIENTO: Duerme 5 segundos.
        PROPÓSITO: No consumir CPU cuando no hay trabajo.
        """
        from worker import Worker
        
        mock_jq = MagicMock()
        mock_jq.dequeue.return_value = None  # No hay jobs
        
        worker = Worker(
            database=MagicMock(),
            job_queue=mock_jq,
            file_manager=MagicMock(),
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        # Detener después de un ciclo
        def stop_after_one(*args):
            worker._stop_requested = True
        
        mock_sleep.side_effect = stop_after_one
        
        worker.run()
        
        mock_sleep.assert_called_with(5)

    def test_run_acquires_lock_before_processing(self):
        """
        ESCENARIO: Procesamiento de job.
        COMPORTAMIENTO: Adquiere lock antes de obtener job.
        PROPÓSITO: Evitar procesamiento concurrente.
        """
        from worker import Worker
        
        mock_fm = MagicMock()
        mock_fm.acquire_lock.return_value = True
        
        mock_jq = MagicMock()
        mock_jq.dequeue.return_value = {"id": 1, "file_path": "/test.wav"}
        
        worker = Worker(
            database=MagicMock(),
            job_queue=mock_jq,
            file_manager=mock_fm,
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        with patch.object(worker, 'process_single_job', return_value=True):
            with patch('worker.time.sleep'):
                worker._stop_requested = True
                worker.run()
        
        mock_fm.acquire_lock.assert_called_once()

    def test_run_releases_lock_after_processing(self):
        """
        ESCENARIO: Job procesado exitosamente.
        COMPORTAMIENTO: Libera lock después de procesar.
        PROPÓSITO: Permitir que otros procesos adquieran el lock.
        """
        from worker import Worker
        
        mock_fm = MagicMock()
        mock_fm.acquire_lock.return_value = True
        
        mock_jq = MagicMock()
        mock_jq.dequeue.return_value = {"id": 1, "file_path": "/test.wav"}
        
        worker = Worker(
            database=MagicMock(),
            job_queue=mock_jq,
            file_manager=mock_fm,
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        with patch.object(worker, 'process_single_job', return_value=True):
            with patch('worker.time.sleep'):
                worker._stop_requested = True
                worker.run()
        
        mock_fm.release_lock.assert_called_once()


class TestWorkerProcessSingleJob:
    """Tests para process_single_job."""

    def test_process_moves_to_processing(self):
        """
        ESCENARIO: Job recibido en estado pending.
        COMPORTAMIENTO: Mueve archivo a processing/.
        PROPÓSITO: Marcar archivo como en proceso.
        """
        from worker import Worker
        
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
        mock_wc.transcribe.return_value = "Hola mundo"
        
        worker = Worker(
            database=mock_db,
            job_queue=MagicMock(),
            file_manager=mock_fm,
            audio_processor=mock_ap,
            whisper_client=mock_wc
        )
        
        job = {"id": 1, "file_path": "/pending/test.wav", "user_id": "u1"}
        result = worker.process_single_job(job)
        
        mock_fm.move_to_processing.assert_called_once_with("/pending/test.wav")
        assert result is True

    def test_process_checks_cache_before_whisper(self):
        """
        ESCENARIO: Archivo con hash ya cacheado.
        COMPORTAMIENTO: Usa transcripción cacheada sin llamar a whisper.
        PROPÓSITO: Optimizar repeticiones del mismo audio.
        """
        from worker import Worker
        
        mock_db = MagicMock()
        mock_db.get_cached_transcription.return_value = "Transcripción cacheada"
        
        mock_fm = MagicMock()
        mock_fm.calculate_hash.return_value = "cached_hash"
        
        mock_wc = MagicMock()
        
        worker = Worker(
            database=mock_db,
            job_queue=MagicMock(),
            file_manager=mock_fm,
            audio_processor=MagicMock(),
            whisper_client=mock_wc
        )
        
        with tempfile.TemporaryDirectory() as tmp:
            job = {"id": 1, "file_path": os.path.join(tmp, "test.wav"), "user_id": "u1"}
            # Simular que el archivo existe
            with open(job["file_path"], "w") as f:
                f.write("dummy")
            result = worker.process_single_job(job)
        
        # No debe llamar a transcribe si está en cache
        mock_wc.transcribe.assert_not_called()
        assert result is True

    def test_process_validates_audio(self):
        """
        ESCENARIO: Archivo en processing.
        COMPORTAMIENTO: Valida que sea audio válido.
        PROPÓSITO: Rechazar archivos corruptos o inválidos.
        """
        from worker import Worker
        
        mock_ap = MagicMock()
        mock_ap.validate_audio.return_value = (False, "Formato inválido")
        
        mock_fm = MagicMock()
        mock_fm.calculate_hash.return_value = "hash123"
        
        mock_db = MagicMock()
        mock_db.get_cached_transcription.return_value = None
        
        mock_jq = MagicMock()
        
        worker = Worker(
            database=mock_db,
            job_queue=mock_jq,
            file_manager=mock_fm,
            audio_processor=mock_ap,
            whisper_client=MagicMock()
        )
        
        job = {"id": 1, "file_path": "/test.wav", "user_id": "u1"}
        result = worker.process_single_job(job)
        
        mock_ap.validate_audio.assert_called_once()
        # Debe marcar como failed
        mock_jq.complete_job.assert_called_once_with(1, success=False)

    def test_process_handles_chunking(self):
        """
        ESCENARIO: Audio que necesita chunking (>40MB).
        COMPORTAMIENTO: Crea chunks, procesa cada uno, hace merge.
        PROPÓSITO: Manejar archivos grandes.
        """
        from worker import Worker
        
        mock_ap = MagicMock()
        mock_ap.validate_audio.return_value = (True, "")
        mock_ap.needs_chunking.return_value = True
        mock_ap.create_chunks.return_value = ["/chunk1.wav", "/chunk2.wav"]
        mock_ap.merge_transcriptions.return_value = "Transcripción completa"
        
        mock_fm = MagicMock()
        mock_fm.calculate_hash.return_value = "hash123"
        
        mock_db = MagicMock()
        mock_db.get_cached_transcription.return_value = None
        
        mock_wc = MagicMock()
        mock_wc.transcribe.return_value = "Texto"
        
        worker = Worker(
            database=mock_db,
            job_queue=MagicMock(),
            file_manager=mock_fm,
            audio_processor=mock_ap,
            whisper_client=mock_wc
        )
        
        job = {"id": 1, "file_path": "/test.wav", "user_id": "u1"}
        result = worker.process_single_job(job)
        
        mock_ap.create_chunks.assert_called_once()
        # Debe llamar a transcribe para cada chunk
        assert mock_wc.transcribe.call_count == 2
        mock_ap.merge_transcriptions.assert_called_once()

    def test_process_saves_json_result(self):
        """
        ESCENARIO: Transcripción completada.
        COMPORTAMIENTO: Guarda resultado en archivo JSON.
        PROPÓSITO: Persistir transcripción.
        """
        from worker import Worker
        
        mock_fm = MagicMock()
        mock_fm.calculate_hash.return_value = "hash123"
        
        mock_ap = MagicMock()
        mock_ap.validate_audio.return_value = (True, "")
        mock_ap.needs_chunking.return_value = False
        mock_ap.convert_to_wav.return_value = "/test.wav"
        
        mock_wc = MagicMock()
        mock_wc.transcribe.return_value = "Texto transcrito"
        
        mock_db = MagicMock()
        mock_db.get_cached_transcription.return_value = None
        
        worker = Worker(
            database=mock_db,
            job_queue=MagicMock(),
            file_manager=mock_fm,
            audio_processor=mock_ap,
            whisper_client=mock_wc
        )
        
        job = {"id": 1, "file_path": "/test.wav", "user_id": "u1"}
        result = worker.process_single_job(job)
        
        mock_fm.save_transcription_json.assert_called_once()

    def test_process_moves_to_processed(self):
        """
        ESCENARIO: Transcripción guardada exitosamente.
        COMPORTAMIENTO: Mueve archivo a processed/.
        PROPÓSITO: Marcar archivo como completado.
        """
        from worker import Worker
        
        mock_fm = MagicMock()
        mock_fm.calculate_hash.return_value = "hash123"
        
        mock_ap = MagicMock()
        mock_ap.validate_audio.return_value = (True, "")
        mock_ap.needs_chunking.return_value = False
        mock_ap.convert_to_wav.return_value = "/processing/test.wav"
        
        mock_wc = MagicMock()
        mock_wc.transcribe.return_value = "Texto"
        
        mock_db = MagicMock()
        mock_db.get_cached_transcription.return_value = None
        
        worker = Worker(
            database=mock_db,
            job_queue=MagicMock(),
            file_manager=mock_fm,
            audio_processor=mock_ap,
            whisper_client=mock_wc
        )
        
        job = {"id": 1, "file_path": "/processing/test.wav", "user_id": "u1"}
        result = worker.process_single_job(job)
        
        mock_fm.move_to_processed.assert_called_once_with("/processing/test.wav")

    def test_process_marks_job_completed(self):
        """
        ESCENARIO: Procesamiento exitoso.
        COMPORTAMIENTO: Marca job como completed en database.
        PROPÓSITO: Actualizar estado del job.
        """
        from worker import Worker
        
        mock_jq = MagicMock()
        mock_fm = MagicMock()
        mock_fm.calculate_hash.return_value = "hash123"
        
        mock_ap = MagicMock()
        mock_ap.validate_audio.return_value = (True, "")
        mock_ap.needs_chunking.return_value = False
        mock_ap.convert_to_wav.return_value = "/test.wav"
        
        mock_wc = MagicMock()
        mock_wc.transcribe.return_value = "Texto"
        
        mock_db = MagicMock()
        mock_db.get_cached_transcription.return_value = None
        
        worker = Worker(
            database=mock_db,
            job_queue=mock_jq,
            file_manager=mock_fm,
            audio_processor=mock_ap,
            whisper_client=mock_wc
        )
        
        job = {"id": 1, "file_path": "/test.wav", "user_id": "u1"}
        result = worker.process_single_job(job)
        
        mock_jq.complete_job.assert_called_once_with(1, success=True)

    def test_process_caches_transcription(self):
        """
        ESCENARIO: Transcripción nueva completada.
        COMPORTAMIENTO: Guarda en cache el resultado.
        PROPÓSITO: Evitar reprocesamiento futuro.
        """
        from worker import Worker
        
        mock_fm = MagicMock()
        mock_fm.calculate_hash.return_value = "hash123"
        
        mock_ap = MagicMock()
        mock_ap.validate_audio.return_value = (True, "")
        mock_ap.needs_chunking.return_value = False
        mock_ap.convert_to_wav.return_value = "/test.wav"
        
        mock_wc = MagicMock()
        mock_wc.transcribe.return_value = "Texto transcrito"
        
        mock_db = MagicMock()
        mock_db.get_cached_transcription.return_value = None
        
        worker = Worker(
            database=mock_db,
            job_queue=MagicMock(),
            file_manager=mock_fm,
            audio_processor=mock_ap,
            whisper_client=mock_wc
        )
        
        job = {"id": 1, "file_path": "/test.wav", "user_id": "u1"}
        result = worker.process_single_job(job)
        
        mock_db.cache_transcription.assert_called_once_with("hash123", "Texto transcrito")

    def test_process_handles_exception(self):
        """
        ESCENARIO: Error durante procesamiento.
        COMPORTAMIENTO: Captura excepción, marca job como failed.
        PROPÓSITO: No dejar jobs en estado inconsistente.
        """
        from worker import Worker
        
        mock_fm = MagicMock()
        mock_fm.move_to_processing.side_effect = Exception("IO Error")
        
        mock_jq = MagicMock()
        
        worker = Worker(
            database=MagicMock(),
            job_queue=mock_jq,
            file_manager=mock_fm,
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        job = {"id": 1, "file_path": "/test.wav", "user_id": "u1"}
        result = worker.process_single_job(job)
        
        # Debe marcar como fallido
        mock_jq.complete_job.assert_called_once_with(1, success=False, error="IO Error")
        assert result is False

    def test_process_retries_when_failed(self):
        """
        ESCENARIO: Job falla con retry_count < 3.
        COMPORTAMIENTO: Reencola el job para reintento.
        PROPÓSITO: Permitir recuperación de errores temporales.
        """
        from worker import Worker
        
        mock_fm = MagicMock()
        mock_fm.move_to_processing.side_effect = Exception("Error temporal")
        
        mock_jq = MagicMock()
        
        mock_db = MagicMock()
        
        worker = Worker(
            database=mock_db,
            job_queue=mock_jq,
            file_manager=mock_fm,
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        job = {"id": 1, "file_path": "/test.wav", "user_id": "u1", "retry_count": 1}
        result = worker.process_single_job(job)
        
        # Debe actualizar estado a pending para reintento
        mock_jq.update_job_status.assert_called_with(1, "pending")

    def test_process_permanent_failure_after_3_retries(self):
        """
        ESCENARIO: Job falla con retry_count >= 3.
        COMPORTAMIENTO: Marca como failed permanente.
        PROPÓSITO: Evitar reintentos infinitos.
        """
        from worker import Worker
        
        mock_fm = MagicMock()
        mock_fm.move_to_processing.side_effect = Exception("Error persistente")
        
        mock_jq = MagicMock()
        
        worker = Worker(
            database=MagicMock(),
            job_queue=mock_jq,
            file_manager=mock_fm,
            audio_processor=MagicMock(),
            whisper_client=MagicMock()
        )
        
        job = {"id": 1, "file_path": "/test.wav", "user_id": "u1", "retry_count": 3}
        result = worker.process_single_job(job)
        
        # No debe reencolar, debe dejar como failed
        mock_jq.update_job_status.assert_not_called()
        mock_jq.complete_job.assert_called_once_with(1, success=False, error="Error persistente")

    def test_process_updates_progress(self):
        """
        ESCENARIO: Procesamiento de chunks.
        COMPORTAMIENTO: Notifica progreso por cada chunk.
        PROPÓSITO: Mantener informado al usuario.
        """
        from worker import Worker
        
        mock_ap = MagicMock()
        mock_ap.validate_audio.return_value = (True, "")
        mock_ap.needs_chunking.return_value = True
        mock_ap.create_chunks.return_value = ["/chunk1.wav", "/chunk2.wav", "/chunk3.wav"]
        mock_ap.merge_transcriptions.return_value = "Completo"
        
        mock_fm = MagicMock()
        mock_fm.calculate_hash.return_value = "hash123"
        
        mock_db = MagicMock()
        mock_db.get_cached_transcription.return_value = None
        
        mock_wc = MagicMock()
        mock_wc.transcribe.return_value = "Texto"
        
        mock_jq = MagicMock()
        
        worker = Worker(
            database=mock_db,
            job_queue=mock_jq,
            file_manager=mock_fm,
            audio_processor=mock_ap,
            whisper_client=mock_wc
        )
        
        job = {"id": 1, "file_path": "/test.wav", "user_id": "u1"}
        result = worker.process_single_job(job)
        
        # Debe llamar a notify_progress para cada chunk
        assert mock_jq.notify_progress.call_count == 3
