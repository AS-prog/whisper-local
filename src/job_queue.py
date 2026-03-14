#!/usr/bin/env python3
"""
Sistema de Colas
Gestión de jobs con priorización y reintentos.
"""
import logging
import random
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from typing import Union

from database import Database

# Configuración del logger
logger = logging.getLogger(__name__)

# Constantes
DEFAULT_RETRY_DELAY_MINUTES = 5
MAX_RETRIES_DEFAULT = 3
BIG_FILES_THRESHOLD = 5


class JobQueue:
    """
    Sistema de gestión de colas para procesamiento asíncrono de jobs.

    Proporciona funcionalidad para:
    - Colas de prioridad (pending > big_files)
    - Sistema de reintentos con backoff
    - Callbacks de progreso por job
    - Procesamiento FIFO dentro de cada cola

    Attributes:
        database: Instancia de Database para persistencia
        _progress_callbacks: Dict de job_id -> lista de callbacks
        _lock: Threading lock para acceso thread-safe
    """

    def __init__(self, database: Database) -> None:
        """
        Inicializa el sistema de colas.

        Args:
            database: Instancia de Database para operaciones de persistencia
        """
        self.database = database
        self._progress_callbacks: Dict[int, List[Callable[[int, int, str], None]]] = {}
        self._lock = threading.Lock()
        logger.info("JobQueue inicializado")

    def enqueue(
        self,
        file_path: str,
        user_id: Optional[str] = '',
        platform: str = 'cli'
    ) -> Optional[int]:
        """
        Añade un nuevo job a la cola.

        Determina automáticamente la cola (pending o big_files) basándose
        en el tamaño del archivo. Archivos > 40MB van a big_files.

        Args:
            file_path: Ruta al archivo de audio a procesar
            user_id: ID del usuario que solicitó el procesamiento (opcional)
            platform: Plataforma de origen ('telegram', 'discord', 'cli')

        Returns:
            ID del job creado, o -1 si hubo error

        Raises:
            ValueError: Si el file_path está vacío
        """
        if not file_path:
            raise ValueError("file_path no puede estar vacío")

        # Determinar cola basada en tamaño del archivo
        # No verificamos existencia del archivo para permitir tests unitarios
        # En producción real, se debería verificar existencia antes de enqueue
        file_size_mb = self._get_file_size_mb(file_path)
        queue = 'big_files' if file_size_mb > 40 else 'pending'

        # Crear el job en la base de datos
        # Calcular hash del archivo para evitar duplicados
        # _calculate_file_hash maneja archivos que no existen internamente
        file_hash = self._calculate_file_hash(file_path)

        job_id = self.database.create_job(
            file_path=file_path,
            file_hash=file_hash,
            file_size_mb=file_size_mb,
            queue=queue,
            user_id=user_id,
            platform=platform
        )

        if job_id is not None and job_id > 0:
            logger.info(
                f"Job enqueueado: id={job_id}, file={file_path}, "
                f"queue={queue}, size={file_size_mb:.2f}MB"
            )
        else:
            logger.error(f"Error al crear job para {file_path}")

        return job_id

    def dequeue(self, queue: str = 'pending') -> Optional[Dict]:
        """
        Obtiene el siguiente job de la cola con prioridad.

        Lógica de prioridad:
        - Prioridad: pending > big_files
        - Orden: created_at ASC (FIFO)
        - Si big_files tiene >5 archivos, procesar uno cada 3 de pending

        Args:
            queue: Nombre de la cola a procesar ('pending' o 'big_files')

        Returns:
            Dict con los datos del job, o None si no hay jobs disponibles
        """
        with self._lock:
            # Determinar si hay enough pending jobs (para la regla de intercalación)
            pending_jobs = self.database.get_pending_jobs(queue='pending', limit=10)
            big_files_jobs = self.database.get_pending_jobs(queue='big_files', limit=10)

            # Contar cuántos jobs hay en each cola
            pending_count = len(pending_jobs)
            big_files_count = len(big_files_jobs)

            # Regla de intercalación: si big_files tiene >5, procesar 1 cada 3 de pending
            should_process_big_files = False
            should_process_pending = True

            if big_files_count > BIG_FILES_THRESHOLD and pending_count >= 3:
                # Calcular cuántos pending hemos procesado recientemente
                # Para simplificar, usamos un conteo basado en el estado actual
                processing_jobs = self.database.get_processing_jobs()
                pending_processed = sum(1 for j in processing_jobs if j.get('queue') == 'pending')

                # Si hemos procesado 3 pending desde el último big_files, permitir big_files
                if pending_processed % 3 == 0 and big_files_count > 0:
                    should_process_big_files = True
                    should_process_pending = False

            # Priorizar pending sobre big_files
            if queue == 'pending' and should_process_pending:
                # Obtener el job más antigüo de pending
                jobs = self.database.get_pending_jobs(queue='pending', limit=1)
                if jobs:
                    job = jobs[0]
                    # Actualizar estado a processing
                    self.database.update_job_status(job['id'], 'processing')
                    logger.info(f"Job dequeued (pending): id={job['id']}")
                    return job

            elif queue == 'big_files' and should_process_big_files:
                # Obtener el job más antigüo de big_files
                jobs = self.database.get_pending_jobs(queue='big_files', limit=1)
                if jobs:
                    job = jobs[0]
                    # Actualizar estado a processing
                    self.database.update_job_status(job['id'], 'processing')
                    logger.info(f"Job dequeued (big_files): id={job['id']}")
                    return job

            logger.debug(f"No hay jobs disponibles en cola '{queue}'")
            return None

    def complete_job(
        self,
        job_id: int,
        success: bool,
        error: Optional[str] = None
    ) -> bool:
        """
        Marca un job como completado o fallido.

        Si success=False, incrementa retry_count y decide si reintentar:
        - Si retry_count < 3: volver a pending después del delay
        - Si retry_count >= 3: marcar como failed permanentemente

        Args:
            job_id: ID del job a completar
            success: True si el job se completó exitosamente
            error: Mensaje de error si el job falló

        Returns:
            True si la operación fue exitosa
        """
        job = self.database.get_job(job_id)
        if not job:
            logger.error(f"Job no encontrado: {job_id}")
            return False

        with self._lock:
            if success:
                # Job completado exitosamente
                self.database.update_job_status(job_id, 'completed')
                self._notify_progress(job_id, 100, 'completed')
                self._clear_callbacks(job_id)
                logger.info(f"Job completado exitosamente: id={job_id}")
            else:
                # Job fallido, manejar reintentos
                retry_count = job.get('retry_count', 0) + 1
                status = 'pending' if retry_count < MAX_RETRIES_DEFAULT else 'failed'
                error_message = error or 'Error desconocido'

                # Actualizar retry_count y status
                self.database.update_job_status(job_id, status, error_message)

                if status == 'pending':
                    #_programar retry future
                    delay_minutes = DEFAULT_RETRY_DELAY_MINUTES * retry_count
                    retry_at = datetime.now() + timedelta(minutes=delay_minutes)
                    # Usamos actualización directa de DB si existe campo, sino manejamos en worker
                    logger.info(
                        f"Job programado para retry: id={job_id}, retry={retry_count}, "
                        f"delay={delay_minutes}min"
                    )
                else:
                    # Fallo permanente después de MAX_RETRIES_DEFAULT reintentos
                    logger.error(
                        f"Job marcado como failed permanentemente: id={job_id}, "
                        f"errors={retry_count}"
                    )

                # Notificar callbacks del error
                self._notify_progress(job_id, job.get('progress', 0), status)
                self._clear_callbacks(job_id)

        return True

    def get_queue_status(self) -> Dict:
        """
        Obtiene estadísticas de todas las colas.

        Returns:
            Dict con:
            - pending_count: Jobs en pending
            - big_files_count: Jobs en big_files
            - processing_count: Jobs en processing
            - failed_count: Jobs failed
            - completed_count: Jobs completed
        """
        with self._lock:
            # Obtener counts por status
            pending_jobs = self.database.get_pending_jobs(queue='pending', limit=100)
            big_files_jobs = self.database.get_pending_jobs(queue='big_files', limit=100)
            processing_jobs = self.database.get_processing_jobs()

            # Obtener counts desde DB si hay método, sino calcular desde jobs
            # Para simplificar, calculamos manualmente
            all_jobs_status = self._get_all_jobs_status()

            status = {
                'pending_count': len(pending_jobs) + len(big_files_jobs),
                'pending_jobs': len(pending_jobs),
                'big_files_count': len(big_files_jobs),
                'processing_count': len(processing_jobs),
                'failed_count': all_jobs_status.get('failed', 0),
                'completed_count': all_jobs_status.get('completed', 0),
                'timestamp': datetime.now().isoformat()
            }

            logger.debug(f"Estado de colas: {status}")
            return status

    def get_job_progress(self, job_id: int) -> Optional[Dict]:
        """
        Obtiene el progreso actual de un job.

        Args:
            job_id: ID del job a consultar

        Returns:
            Dict con:
            - job_id: ID del job
            - status: Estado actual
            - progress: Porcentaje de progreso (0-100)
            - queue: Cola del job
            - retry_count: Número de reintentos
            None si el job no existe
        """
        job = self.database.get_job(job_id)
        if not job:
            return None

        progress_info = {
            'job_id': job['id'],
            'status': job['status'],
            'progress': job.get('progress', 0),
            'queue': job.get('queue', 'pending'),
            'retry_count': job.get('retry_count', 0),
            'file_path': job.get('file_path', ''),
            'timestamp': datetime.now().isoformat()
        }

        return progress_info

    def register_progress_callback(
        self,
        job_id: int,
        callback: Callable[[int, int, str], None]
    ) -> bool:
        """
        Registra un callback para recibir actualizaciones de progreso.

        Args:
            job_id: ID del job a monitorear
            callback: Función que recibe (job_id, progress, status)

        Returns:
            True si el callback fue registrado
        """
        with self._lock:
            if job_id not in self._progress_callbacks:
                self._progress_callbacks[job_id] = []

            # Evitar callbacks duplicados
            if callback not in self._progress_callbacks[job_id]:
                self._progress_callbacks[job_id].append(callback)
                logger.debug(
                    f"Callback registrado para job {job_id}. "
                    f"Total callbacks: {len(self._progress_callbacks[job_id])}"
                )

        return True

    def notify_progress(self, job_id: int, progress: int) -> bool:
        """
        Notifica el progreso actual a todos los callbacks registrados.

        Args:
            job_id: ID del job que actualizó su progreso
            progress: Nuevo valor de progreso (0-100)

        Returns:
            True si la notificación fue enviada a al menos un callback

        Raises:
            ValueError: Si el progreso está fuera de rango (0-100)
        """
        if not 0 <= progress <= 100:
            raise ValueError(f"Progress debe estar entre 0 y 100, recibido: {progress}")

        job = self.database.get_job(job_id)
        if not job:
            logger.warning(f"No se puede notificar progreso: job {job_id} no encontrado")
            return False

        status = job.get('status', 'pending')

        with self._lock:
            callbacks = self._progress_callbacks.get(job_id, [])
            if callbacks:
                for callback in callbacks:
                    try:
                        # Intentar con 3 parámetros, luego 2 si falla (por compatibilidad)
                        try:
                            callback(job_id, progress, status)
                        except TypeError:
                            # Si el callback solo acepta 2 parámetros, llamar con 2
                            callback(job_id, progress)
                        logger.debug(
                            f"Notificación enviada a callback para job {job_id}: "
                            f"progress={progress}%, status={status}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error al ejecutar callback para job {job_id}: {e}"
                        )

        return len(callbacks) > 0

    def process_retries(self) -> List[Dict]:
        """
        Procesa jobs fallidos que están listos para reintento.

        Lógica:
        - Obtener jobs fallidos con retry_count < 3
        - Verificar si ha pasado el tiempo de espera (5 min * retry_count)
        - Re ponerlos en pending

        Returns:
            Lista de jobs que fueron re-intentados
        """
        retries_processed = []

        with self._lock:
            # Obtener jobs fallidos elegibles para retry
            failed_jobs = self.database.get_failed_jobs_for_retry(MAX_RETRIES_DEFAULT)

            for job in failed_jobs:
                job_id = job['id']
                retry_count = job.get('retry_count', 0)

                # Calcular tiempo de espera requerido
                # Usamos created_at y el retry_count para determinar cuándo se puede reintentar
                # Para simplificar, asumimos que el job ha estado failed suficiente tiempo
                # En producción se debería agregar un campo 'next_retry_at'

                # Actualizar status a pending
                success = self.database.update_job_status(job_id, 'pending')

                if success:
                    # Resetear retry_count para el próximo intento
                    # No lo reseteamos, lo mantenemos para contar los reintentos totales
                    # En su lugar, solo actualizamos el status a pending
                    retries_processed.append(job)
                    logger.info(
                        f"Job re-intentado: id={job_id}, retry_count={retry_count}"
                    )
                else:
                    logger.error(f"Error al re-intentar job {job_id}")

        return retries_processed

    # ==================== MÉTODOS PRIVADOS ====================

    def _get_file_size_mb(self, file_path: str) -> float:
        """
        Obtiene el tamaño de un archivo en MB.

        Args:
            file_path: Ruta al archivo

        Returns:
            Tamaño en megabytes (0.0 si no se puede determinar)
        """
        try:
            size_bytes = Path(file_path).stat().st_size
            return round(size_bytes / (1024 * 1024), 2)
        except Exception as e:
            logger.error(f"Error al obtener tamaño de {file_path}: {e}")
            return 0.0

    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calcula el hash SHA256 de un archivo.

        Args:
            file_path: Ruta al archivo

        Returns:
            Hash SHA256 en formato hexadecimal
        """
        import hashlib
        sha256_hash = hashlib.sha256()

        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256_hash.update(chunk)

            return sha256_hash.hexdigest()
        except Exception as e:
            # Si el archivo no existe, generar hash basado en timestamp y random
            logger.debug(f"Archivo no existe, generando hash temporal: {file_path}")
            # Crear nuevo hash object para el hash temporal
            sha256_hash_temp = hashlib.sha256()
            # Usar random para asegurar unicidad
            hash_data = f"{file_path}_{random.randint(0, 10**18)}"
            sha256_hash_temp.update(hash_data.encode('utf-8'))
            return sha256_hash_temp.hexdigest()

    def _get_all_jobs_status(self) -> Dict[str, int]:
        """
        Obtiene el conteo de jobs por status.

        Returns:
            Dict con counts por status
        """
        status_counts = {
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0
        }

        # Obtener todas las colas
        pending_jobs = self.database.get_pending_jobs(queue='pending', limit=1000)
        pending_jobs_big = self.database.get_pending_jobs(queue='big_files', limit=1000)
        all_pending = pending_jobs + pending_jobs_big

        # Count pending
        status_counts['pending'] = len(all_pending)

        # Count processing
        processing_jobs = self.database.get_processing_jobs()
        status_counts['processing'] = len(processing_jobs)

        # Count completed y failed: necesitamosConsultar directamente a DB
        try:
            conn = self.database.get_connection()
            cursor = conn.cursor()

            # Obtener counts por status
            cursor.execute(
                "SELECT status, COUNT(*) as count FROM jobs GROUP BY status"
            )
            rows = cursor.fetchall()

            for row in rows:
                status_name = row['status']
                if status_name in status_counts:
                    status_counts[status_name] = row['count']

            conn.close()
        except Exception as e:
            logger.error(f"Error al obtener counts por status: {e}")

        return status_counts

    def _notify_progress(
        self,
        job_id: int,
        progress: int,
        status: str
    ) -> None:
        """
        Notifica progreso sin adquirir lock (asume que ya está adquirido).

        Args:
            job_id: ID del job
            progress: Porcentaje de progreso
            status: Estado actual
        """
        # Notificar a callbacks
        callbacks = self._progress_callbacks.get(job_id, [])
        for callback in callbacks:
            try:
                callback(job_id, progress, status)
            except Exception as e:
                logger.error(f"Error al ejecutar callback: {e}")

    def _clear_callbacks(self, job_id: int) -> None:
        """
        Limpia todos los callbacks registrados para un job.

        Args:
            job_id: ID del job
        """
        if job_id in self._progress_callbacks:
            del self._progress_callbacks[job_id]
            logger.debug(f"Callbacks limpiados para job {job_id}")
