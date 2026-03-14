#!/usr/bin/env python3
"""
Módulo de Base de Datos
Wrapper SQLite para gestión de jobs, cache y métricas.
"""
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

# Constantes
DEFAULT_DB_PATH = "whisper.db"
MAX_RETRIES_DEFAULT = 3


class Database:
    """
    Clase para gestionar la base de datos SQLite de whisper-local.

    Proporciona métodos para operaciones CRUD en las tablas:
    - jobs: Gestión de trabajos de transcripción
    - transcription_cache: Cache de transcripciones
    - rate_limits: Control de límites por usuario
    - metrics: registro de métricas del sistema

    Attributes:
        db_path: Ruta al archivo de base de datos SQLite
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        """
        Inicializa la conexión con la base de datos.

        Args:
            db_path: Ruta al archivo de base de datos. Por defecto 'whisper.db'
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._logger = logging.getLogger(__name__)
        self.init_schema()

    def init_schema(self) -> bool:
        """
        Inicializa el esquema de la base de datos si no existe.

        Ejecuta el script de migración para crear todas las tablas necesarias.

        Returns:
            bool: True si la inicialización fue exitosa o ya existe el schema,
                 False si hubo un error
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Verificar si las tablas ya existen
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
            )
            if cursor.fetchone():
                self._logger.info("Schema ya existe en la base de datos")
                conn.close()
                return True

            # Cargar y ejecutar el script de migración
            migration_path = "migrations/001_init.sql"
            try:
                with open(migration_path, "r") as f:
                    sql_script = f.read()
                cursor.executescript(sql_script)
                conn.commit()
                self._logger.info("Schema inicializado correctamente")
            except FileNotFoundError:
                self._logger.error(f"Script de migración no encontrado: {migration_path}")
                conn.close()
                return False

            conn.close()
            return True

        except sqlite3.Error as e:
            self._logger.error(f"Error al inicializar el schema: {e}")
            return False

    def get_connection(self) -> sqlite3.Connection:
        """
        Obtiene una conexión a la base de datos con row_factory configurada.

        Returns:
            sqlite3.Connection: Connection object con row_factory configurada
                            para retornar filas como diccionarios
        """
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def close(self) -> None:
        """Cierra la conexión con la base de datos."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    # ==================== MÉTODOS PARA TABLA jobs ====================

    def create_job(
        self,
        file_path: str,
        file_hash: str,
        file_size_mb: float,
        queue: str,
        user_id: Optional[str],
        platform: str,
    ) -> Optional[int]:
        """
        Crea un nuevo job de transcripción.

        Args:
            file_path: Ruta al archivo de audio
            file_hash: Hash único del archivo paracache
            file_size_mb: Tamaño del archivo en megabytes
            queue: Cola de procesamiento ('pending' o 'big_files')
            user_id: ID del usuario que solicitó la transcripción
            platform: Plataforma de origen ('telegram', 'discord', 'cli')

        Returns:
            int: ID del job creado, o -1 si hubo error
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO jobs (file_path, file_hash, file_size_mb, status, queue,
                                user_id, platform, created_at)
                VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (
                    file_path,
                    file_hash,
                    file_size_mb,
                    queue,
                    user_id or '',
                    platform,
                    datetime.now(),
                ),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            self._logger.error(f"Error al crear job: {e}")
            return -1

    def get_job(self, job_id: int) -> Optional[dict]:
        """
        Obtiene un job por su ID.

        Args:
            job_id: ID del job a recuperar

        Returns:
            dict con todos los campos del job, o None si no existe
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            self._logger.error(f"Error al obtener job {job_id}: {e}")
            return None

    def update_job_status(
        self, job_id: int, status: str, error_message: Optional[str] = None
    ) -> bool:
        """
        Actualiza el estado de un job.

        Args:
            job_id: ID del job a actualizar
            status: Nuevo estado ('pending', 'processing', 'completed', 'failed')
            error_message: Mensaje de error si el status es 'failed'

        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?
                %s
                WHERE id = ?
                """
                % (", error_message = ?" if error_message else ""),
                (
                    *(status, datetime.now())
                    + ((error_message, job_id,) if error_message else (job_id,)),
                ),
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self._logger.error(f"Error al actualizar job {job_id}: {e}")
            return False

    def get_pending_jobs(self, queue: str = "pending", limit: int = 10) -> list:
        """
        Obtiene los jobs pendientes para un cola específica.

        Args:
            queue: Nombre de la cola a procesar ('pending' o 'big_files')
            limit: Número máximo de jobs a recuperar

        Returns:
            list: Lista de diccionarios con los jobs pendientes
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'pending' AND queue = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (queue, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            self._logger.error(f"Error al obtener jobs pendientes: {e}")
            return []

    def get_processing_jobs(self) -> list:
        """
        Obtiene todos los jobs que están actualmente en procesamiento.

        Returns:
            list: Lista de diccionarios con los jobs en processing
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM jobs WHERE status = 'processing' ORDER BY updated_at ASC"
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            self._logger.error(f"Error al obtener jobs en processing: {e}")
            return []

    def update_job_progress(
        self, job_id: int, progress: int, chunks_completed: Optional[int] = None
    ) -> bool:
        """
        Actualiza el progreso de un job.

        Args:
            job_id: ID del job a actualizar
            progress: Progreso actual (0-100)
            chunks_completed: Número de segmentos completados (opcional)

        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if chunks_completed is not None:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET progress = ?, chunks_completed = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (progress, chunks_completed, datetime.now(), job_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET progress = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (progress, datetime.now(), job_id),
                )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self._logger.error(f"Error al actualizar progreso del job {job_id}: {e}")
            return False

    def get_failed_jobs_for_retry(self, max_retries: int = MAX_RETRIES_DEFAULT) -> list:
        """
        Obtiene jobs fallidos que están listos para reintento.

        Args:
            max_retries: Número máximo de reintentos permitidos

        Returns:
            list: Lista de diccionarios con jobs que pueden reintentar
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'failed' AND retry_count < ?
                ORDER BY retry_count ASC, created_at ASC
                """,
                (max_retries,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            self._logger.error(f"Error al obtener jobs para reintentar: {e}")
            return []

    # ==================== MÉTODOS PARA TABLA transcription_cache ====================

    def get_cached_transcription(self, file_hash: str) -> Optional[str]:
        """
        Obtiene una transcripción del cache por hash de archivo.

        Args:
            file_hash: Hash único del archivo

        Returns:
            str con la transcripción, o None si no existe en cache
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT transcription, access_count FROM transcription_cache
                WHERE file_hash = ?
                """,
                (file_hash,),
            )
            row = cursor.fetchone()
            if row:
                # Incrementar contador de acceso
                cursor.execute(
                    """
                    UPDATE transcription_cache
                    SET access_count = access_count + 1,
                        last_accessed = ?
                    WHERE file_hash = ?
                    """,
                    (datetime.now(), file_hash),
                )
                conn.commit()
                return row["transcription"]
            return None
        except sqlite3.Error as e:
            self._logger.error(f"Error al obtener cache para hash {file_hash}: {e}")
            return None

    def cache_transcription(self, file_hash: str, transcription: str) -> bool:
        """
        Guarda una transcripción en el cache.

        Args:
            file_hash: Hash único del archivo
            transcription: Texto de la transcripción

        Returns:
            bool: True si el cacheo fue exitoso
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO transcription_cache
                (file_hash, transcription, created_at, access_count, last_accessed)
                VALUES (?, ?, ?, 1, ?)
                """,
                (file_hash, transcription, datetime.now(), datetime.now()),
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            self._logger.error(f"Error al guardar en cache: {e}")
            return False

    def clean_old_cache(self, days: int = 30) -> int:
        """
        Elimina transcripciones del cache más antiguas que el período especificado.

        Args:
            days: Número de días para retener en cache

        Returns:
            int: Número de registros eliminados
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor.execute(
                """
                DELETE FROM transcription_cache
                WHERE last_accessed < ?
                """,
                (cutoff_date.isoformat(),),
            )
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            self._logger.error(f"Error al limpiar cache antiguo: {e}")
            return 0

    # ==================== MÉTODOS PARA TABLA rate_limits ====================

    def check_rate_limit(
        self, user_id: str, platform: str, max_per_hour: int = 5
    ) -> bool:
        """
        Verifica si un usuario puede procesar más archivos en la ventana actual.

        Args:
            user_id: ID del usuario
            platform: Plataforma de usuario ('telegram', 'discord', 'cli')
            max_per_hour: Número máximo permitido de archivos por hora

        Returns:
            bool: True si el usuario puede procesar más, False si está limitado
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            current_time = datetime.now()
            window_start = current_time - timedelta(hours=1)

            cursor.execute(
                """
                SELECT COALESCE(SUM(file_count), 0) as total
                FROM rate_limits
                WHERE user_id = ? AND platform = ? AND window_start >= ?
                """,
                (user_id, platform, window_start.isoformat()),
            )
            row = cursor.fetchone()
            total = row["total"] if row else 0
            return total < max_per_hour
        except sqlite3.Error as e:
            self._logger.error(f"Error al verificar límite de rate: {e}")
            return True  # Permitir si hay error

    def increment_rate_limit(self, user_id: str, platform: str) -> bool:
        """
        Incrementa el contador de archivos procesados por un usuario.

        Args:
            user_id: ID del usuario
            platform: Plataforma de usuario

        Returns:
            bool: True si la operación fue exitosa
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            current_time = datetime.now()

            # Intentar actualizar si ya existe un registro para esta ventana
            cursor.execute(
                """
                UPDATE rate_limits
                SET file_count = file_count + 1
                WHERE user_id = ? AND platform = ? AND window_start >= ?
                """,
                (user_id, platform, (current_time - timedelta(hours=1)).isoformat()),
            )

            if cursor.rowcount == 0:
                # Si no existe, crear un nuevo registro
                cursor.execute(
                    """
                    INSERT INTO rate_limits
                    (user_id, platform, file_count, window_start)
                    VALUES (?, ?, 1, ?)
                    """,
                    (user_id, platform, current_time.isoformat()),
                )

            conn.commit()
            return True
        except sqlite3.Error as e:
            self._logger.error(f"Error al incrementar rate limit: {e}")
            return False

    def reset_rate_limit(self, user_id: str, platform: str) -> bool:
        """
        Resetea el contador de rate limit para un usuario y plataforma.

        Args:
            user_id: ID del usuario
            platform: Plataforma de usuario

        Returns:
            bool: True si la operación fue exitosa
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM rate_limits
                WHERE user_id = ? AND platform = ?
                """,
                (user_id, platform),
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            self._logger.error(f"Error al resetear rate limit: {e}")
            return False

    # ==================== MÉTODOS PARA TABLA metrics ====================

    def record_metric(self, metric_name: str, metric_value: float) -> bool:
        """
        Registra una métrica en la base de datos.

        Args:
            metric_name: Nombre de la métrica
            metric_value: Valor numérico de la métrica

        Returns:
            bool: True si el registro fue exitoso
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO metrics (metric_name, metric_value, recorded_at)
                VALUES (?, ?, ?)
                """,
                (metric_name, metric_value, datetime.now()),
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            self._logger.error(f"Error al registrar métrica: {e}")
            return False

    def get_average_processing_time(self, hours: int = 24) -> float:
        """
        Calcula el tiempo promedio de procesamiento de jobs completados.

        Args:
            hours: Ventana de tiempo en horas para considerar

        Returns:
            float: Tiempo promedio en segundos, o 0.0 si no hay datos
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(hours=hours)

            cursor.execute(
                """
                SELECT AVG(
                    (julianday(completed_at) - julianday(started_at)) * 86400
                ) as avg_seconds
                FROM jobs
                WHERE status = 'completed'
                    AND started_at IS NOT NULL
                    AND completed_at IS NOT NULL
                    AND completed_at >= ?
                """,
                (cutoff_date.isoformat(),),
            )
            row = cursor.fetchone()
            avg_seconds = row["avg_seconds"] if row else 0.0
            return float(avg_seconds) if avg_seconds else 0.0
        except sqlite3.Error as e:
            self._logger.error(f"Error al calcular tiempo promedio: {e}")
            return 0.0

    def get_success_rate(self, hours: int = 24) -> float:
        """
        Calcula la tasa de éxito de procesamiento en la ventana temporal.

        Args:
            hours: Ventana de tiempo en horas para considerar

        Returns:
            float: Tasa de éxito (0.0 - 1.0), o 0.0 si no hay datos
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(hours=hours)

            cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM jobs
                WHERE created_at >= ?
                """,
                (cutoff_date.isoformat(),),
            )
            row = cursor.fetchone()
            if row and row["total"] > 0:
                return row["completed"] / row["total"]
            return 0.0
        except sqlite3.Error as e:
            self._logger.error(f"Error al calcular tasa de éxito: {e}")
            return 0.0

    def __enter__(self) -> "Database":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cierra la conexión."""
        self.close()
