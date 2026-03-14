#!/usr/bin/env python3
"""
Gestión de Archivos
Manejo de locks, hashing SHA256 y operaciones de archivo.
"""

import hashlib
import json
import logging
import os
import shutil
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from typing import Union

# Configuración del logger
logger = logging.getLogger(__name__)


class FileManager:
    """
    Gestor de archivos para el procesador de transcripciones.
    
    Proporciona funcionalidad para:
    - Manejo de locks con timeout y PID de proceso dueño
    - Cálculo de hashes SHA256 con caching
    - Movimiento de archivos entre estados (pending, processing, processed, big_size)
    - Limpieza de archivos stale
    
    Attributes:
        base_path (Path): Ruta base del directorio de entrada
        lock_file (Path): Ruta al archivo de lock
        hash_cache (OrderedDict): Cache de hashes recientes (últimos 100)
    """
    
    _MAX_CACHE_SIZE = 100
    _HASH_CHUNK_SIZE = 1024 * 1024  # 1MB
    
    def __init__(self, base_path: str = 'inputs') -> None:
        """
        Inicializa el gestor de archivos.
        
        Args:
            base_path: Ruta base del directorio de entrada (por defecto 'inputs')
        """
        self.base_path = Path(base_path).resolve()
        self.lock_file = self.base_path / '.lock'
        self.hash_cache: OrderedDict[str, str] = OrderedDict()
        
        # Crear estructura de directorios si no existe
        self._ensure_directories()
        
        logger.info(f"FileManager inicializado con base_path={self.base_path}")
    
    def _ensure_directories(self) -> None:
        """Crea la estructura de directorios si no existe."""
        directories = [
            self.base_path,
            self.base_path / 'processed',
            self.base_path / 'pending',
            self.base_path / 'processing',
            self.base_path / 'big_size'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directorio asegurado: {directory}")
    
    def calculate_hash(self, file_path: str) -> str:
        """
        Calcula el hash SHA256 de un archivo.
        
        Lee el archivo en chunks de 1MB para manejar archivos grandes eficientemente.
        Usa un cache de las últimas 100 operaciones para evitar cálculos redundantes.
        
        Args:
            file_path: Ruta al archivo a Hashear
            
        Returns:
            Hash SHA256 del archivo en formato hexadecimal
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            PermissionError: Si no hay permisos para leer el archivo
            IOError: Si ocurre un error durante la lectura del archivo
        """
        file_path_obj = Path(file_path).resolve()
        
        # Verificar si el archivo existe
        if not file_path_obj.exists():
            raise FileNotFoundError(f"El archivo no existe: {file_path}")
        
        # Verificar si el archivo es un archivo regular
        if not file_path_obj.is_file():
            raise ValueError(f"La ruta no es un archivo: {file_path}")
        
        # Verificar si está en cache (usando ruta resuelta como key)
        cache_key = str(file_path_obj)
        
        if cache_key in self.hash_cache:
            logger.debug(f"Cache hit para hash: {file_path}")
            return self.hash_cache[cache_key]
        
        # Calcular hash en chunks de 1MB
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path_obj, 'rb') as f:
                while True:
                    chunk = f.read(self._HASH_CHUNK_SIZE)
                    if not chunk:
                        break
                    sha256_hash.update(chunk)
            
            hash_result = sha256_hash.hexdigest()
            
            # Actualizar cache (mantener solo los últimos 100)
            if cache_key in self.hash_cache:
                self.hash_cache.move_to_end(cache_key)
            else:
                self.hash_cache[cache_key] = hash_result
                if len(self.hash_cache) > self._MAX_CACHE_SIZE:
                    # Eliminar el más antiguo
                    self.hash_cache.popitem(last=False)
            
            logger.debug(f"Hash calculado para {file_path}: {hash_result[:16]}...")
            
            return hash_result
            
        except PermissionError as e:
            logger.error(f"Permiso denegado al leer {file_path}: {e}")
            raise
        except IOError as e:
            logger.error(f"Error de I/O al leer {file_path}: {e}")
            raise
    
    def acquire_lock(self, timeout_minutes: int = 30) -> bool:
        """
        Adquiere un lock sobre el directorio de entrada.
        
        Args:
            timeout_minutes: Tiempo de expiración automática en minutos (por defecto 30)
            
        Returns:
            True si el lock se adquirió exitosamente, False si ya está ocupado
        """
        try:
            # Verificar si ya hay un lock
            if self.is_locked():
                lock_info = self.get_lock_info()
                if lock_info is not None:
                    # Verificar si el lock ha expirado
                    lock_time = datetime.fromtimestamp(lock_info['timestamp'])
                    expires_at = lock_time + timedelta(minutes=timeout_minutes)
                    
                    if datetime.now() > expires_at:
                        # El lock ha expirado, intentar tomárselo al proceso anterior
                        logger.warning(f"Lock expirado encontrado, tomándolo: PID {lock_info['pid']}")
                        self.release_lock()
                    else:
                        # El lock aún es válido
                        logger.warning(f"El sistema ya está en proceso (PID {lock_info['pid']})")
                        return False
            
            # Crear archivo de lock conPID y timestamp
            pid = os.getpid()
            timestamp = time.time()
            
            lock_data = {
                'pid': pid,
                'timestamp': timestamp,
                'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown'
            }
            
            # Escribir datos de lock con formato JSON simple
            import json
            with open(self.lock_file, 'w') as f:
                json.dump(lock_data, f, indent=2)
            
            logger.info(f"Lock adquirido por PID {pid}")
            return True
            
        except Exception as e:
            logger.error(f"Error al adquirir lock: {e}")
            return False
    
    def release_lock(self) -> bool:
        """
        Libera el lock sobre el directorio de entrada.
        
        Returns:
            True si el lock se liberó exitosamente, False si no había lock
        """
        try:
            if not self.lock_file.exists():
                logger.warning("No hay lock para liberar")
                return False
            
            # Verificar que este proceso es el dueño (o forzar)
            lock_info = self.get_lock_info()
            current_pid = os.getpid()
            
            if lock_info is not None and lock_info['pid'] != current_pid:
                logger.warning(f"Intento de liberar lock de otro proceso (PID {lock_info['pid']})")
                return False
            
            self.lock_file.unlink()
            logger.info(f"Lock liberado por PID {current_pid}")
            return True
            
        except Exception as e:
            logger.error(f"Error al liberar lock: {e}")
            return False
    
    def is_locked(self) -> bool:
        """
        Verifica si el directorio está en uso (con lock activo).
        
        Returns:
            True si hay un lock activo, False en caso contrario
        """
        if not self.lock_file.exists():
            return False
        
        # Verificar si el lock ha expirado
        lock_info = self.get_lock_info()
        return lock_info is not None
    
    def get_lock_info(self) -> Optional[dict]:
        """
        Obtiene información sobre el lock actual.
        
        Returns:
            Dict con información del lock (pid, timestamp, hostname) o None si no hay lock
        """
        try:
            if not self.lock_file.exists():
                return None
            
            with open(self.lock_file, 'r') as f:
                return json.load(f)
                
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error al leer información del lock: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al leer lock: {e}")
            return None
    
    def move_to_pending(self, source: str) -> str:
        """
        Mueve un archivo del sistema de entrada al estado pending.
        
        Args:
            source: Ruta del archivo a mover
            
        Returns:
            Ruta completa al archivo en estado pending
            
        Raises:
            FileNotFoundError: Si el archivo source no existe
            PermissionError: Si no hay permisos para mover el archivo
        """
        source_path = Path(source).resolve()
        
        if not source_path.exists():
            raise FileNotFoundError(f"El archivo source no existe: {source}")
        
        # Si ya está en pending, devolver la ruta actual
        if source_path.parent.name == 'pending':
            return str(source_path)
        
        pending_path = self.base_path / 'pending' / source_path.name
        
        # Evitar sobrescritura
        if pending_path.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pending_path = self.base_path / 'pending' / f"{source_path.stem}_{timestamp}{source_path.suffix}"
        
        try:
            shutil.move(str(source_path), str(pending_path))
            logger.info(f"Archivo movido a pending: {source_path} -> {pending_path}")
            return str(pending_path)
            
        except PermissionError as e:
            logger.error(f"Permiso denegado al mover {source_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al mover archivo a pending: {e}")
            raise
    
    def move_to_processing(self, file_path: str) -> str:
        """
        Mueve un archivo del estado pending a processing.
        
        Args:
            file_path: Ruta del archivo a mover
            
        Returns:
            Ruta completa al archivo en estado processing
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            PermissionError: Si no hay permisos para mover el archivo
        """
        source_path = Path(file_path).resolve()
        
        if not source_path.exists():
            raise FileNotFoundError(f"El archivo no existe: {file_path}")
        
        # Si ya está en processing, devolver la ruta actual
        if source_path.parent.name == 'processing':
            return str(source_path)
        
        # Verificar que está en pending
        if source_path.parent.name != 'pending':
            raise ValueError(f"El archivo no está en estado pending: {file_path}")
        
        processing_path = self.base_path / 'processing' / source_path.name
        
        # Evitar sobrescritura
        if processing_path.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            processing_path = self.base_path / 'processing' / f"{source_path.stem}_{timestamp}{source_path.suffix}"
        
        try:
            shutil.move(str(source_path), str(processing_path))
            logger.info(f"Archivo movido a processing: {source_path} -> {processing_path}")
            return str(processing_path)
            
        except PermissionError as e:
            logger.error(f"Permiso denegado al mover {source_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al mover archivo a processing: {e}")
            raise
    
    def move_to_processed(self, file_path: str) -> str:
        """
        Mueve un archivo del estado processing a processed.
        
        Args:
            file_path: Ruta del archivo a mover
            
        Returns:
            Ruta completa al archivo en estado processed
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            PermissionError: Si no hay permisos para mover el archivo
        """
        source_path = Path(file_path).resolve()
        
        if not source_path.exists():
            raise FileNotFoundError(f"El archivo no existe: {file_path}")
        
        # Si ya está en processed, devolver la ruta actual
        if source_path.parent.name == 'processed':
            return str(source_path)
        
        # Verificar que está en processing
        if source_path.parent.name != 'processing':
            raise ValueError(f"El archivo no está en estado processing: {file_path}")
        
        processed_path = self.base_path / 'processed' / source_path.name
        
        # Evitar sobrescritura
        if processed_path.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            processed_path = self.base_path / 'processed' / f"{source_path.stem}_{timestamp}{source_path.suffix}"
        
        try:
            shutil.move(str(source_path), str(processed_path))
            logger.info(f"Archivo movido a processed: {source_path} -> {processed_path}")
            return str(processed_path)
            
        except PermissionError as e:
            logger.error(f"Permiso denegado al mover {source_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al mover archivo a processed: {e}")
            raise
    
    def move_to_big_size(self, file_path: str) -> str:
        """
        Mueve un archivo al estado big_size (archivos grandes pendientes).
        
        Args:
            file_path: Ruta del archivo a mover
            
        Returns:
            Ruta completa al archivo en estado big_size
            
        Raises:
            FileNotFoundError: Si el archivo no existe
            PermissionError: Si no hay permisos para mover el archivo
        """
        source_path = Path(file_path).resolve()
        
        if not source_path.exists():
            raise FileNotFoundError(f"El archivo no existe: {file_path}")
        
        # Si ya está en big_size, devolver la ruta actual
        if source_path.parent.name == 'big_size':
            return str(source_path)
        
        big_size_path = self.base_path / 'big_size' / source_path.name
        
        # Evitar sobrescritura
        if big_size_path.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            big_size_path = self.base_path / 'big_size' / f"{source_path.stem}_{timestamp}{source_path.suffix}"
        
        try:
            shutil.move(str(source_path), str(big_size_path))
            logger.info(f"Archivo movido a big_size: {source_path} -> {big_size_path}")
            return str(big_size_path)
            
        except PermissionError as e:
            logger.error(f"Permiso denegado al mover {source_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al mover archivo a big_size: {e}")
            raise
    
    def get_pending_files(self) -> list:
        """
        Obtiene la lista de archivos en estado pending.
        
        Returns:
            Lista de rutas absolutas a los archivos en estado pending
        """
        pending_dir = self.base_path / 'pending'
        
        if not pending_dir.exists():
            return []
        
        try:
            files = [
                str(f.resolve())
                for f in pending_dir.iterdir()
                if f.is_file()
            ]
            logger.debug(f"Archivos en estado pending: {len(files)}")
            return files
            
        except PermissionError as e:
            logger.error(f"Permiso denegado al acceder a {pending_dir}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error al obtener archivos pending: {e}")
            return []
    
    def cleanup_processing(self, max_age_hours: int = 24) -> list:
        """
        Limpia archivos en estado processing que exceden el tiempo máximo.
        
        Archivos que llevan más de max_age_hours en processing se mueven de vuelta a pending.
        También archiva logs antiguos y procesa archivos en big_size que ya están procesados.
        
        Args:
            max_age_hours: Edad máxima en horas para archivos en processing (por defecto 24)
            
        Returns:
            Lista de archivos movidos (ya sea a pending o a other destinations)
        """
        moved_files = []
        
        processing_dir = self.base_path / 'processing'
        
        if not processing_dir.exists():
            logger.info("Directorio processing no existe")
            return moved_files
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        try:
            for file_path in processing_dir.iterdir():
                if not file_path.is_file():
                    continue
                
                # Obtener tiempo de modificación
                stat = file_path.stat()
                file_age = current_time - stat.st_mtime
                
                if file_age > max_age_seconds:
                    # Archivo stale, mover a pending
                    pending_path = self.base_path / 'pending' / file_path.name
                    
                    # Evitar sobrescritura
                    if pending_path.exists():
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        pending_path = self.base_path / 'pending' / f"{file_path.stem}_{timestamp}{file_path.suffix}"
                    
                    shutil.move(str(file_path), str(pending_path))
                    moved_files.append(str(pending_path))
                    logger.info(f"Archivo stale movido a pending: {file_path} -> {pending_path}")
            
            # Archivar logs antiguos
            self._archive_old_logs()
            
            # Procesar archivos en big_size que ya fueron procesados
            self._process_big_size_files()
            
            logger.info(f"Cleanup completado: {len(moved_files)} archivos movidos")
            return moved_files
            
        except PermissionError as e:
            logger.error(f"Permiso denegado durante cleanup: {e}")
            return moved_files
        except Exception as e:
            logger.error(f"Error durante cleanup: {e}")
            return moved_files
    
    def _archive_old_logs(self, max_age_days: int = 30) -> None:
        """
        Archiva logs antiguos comprimiéndolos y moviéndolos a una carpeta archive.
        
        Args:
            max_age_days: Edad máxima en días para mantener logs sin comprimir
        """
        logs_archive = self.base_path / 'archive'
        
        try:
            logs_archive.mkdir(exist_ok=True)
            
            # Buscar logs antiguos
            import gzip
            import shutil as shutil_module
            
            current_time = datetime.now()
            
            for log_file in self.base_path.glob('*.log'):
                stat = log_file.stat()
                file_age_days = (current_time - datetime.fromtimestamp(stat.st_mtime)).days
                
                if file_age_days > max_age_days:
                    # Archivar log
                    archive_date = current_time.strftime('%Y%m%d')
                    archive_name = f"{log_file.stem}_{archive_date}.log.gz"
                    archive_path = logs_archive / archive_name
                    
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(archive_path, 'wb') as f_out:
                            shutil_module.copyfileobj(f_in, f_out)
                    
                    log_file.unlink()
                    logger.info(f"Log archivado: {log_file} -> {archive_path}")
            
        except Exception as e:
            logger.error(f"Error al archivar logs: {e}")
    
    def _process_big_size_files(self) -> None:
        """
        Procesa archivos en big_size que ya fueron procesados previamente.
        
        Mueve archivos arbitrados que ya fueron procesados a processed.
        """
        big_size_dir = self.base_path / 'big_size'
        processed_dir = self.base_path / 'processed'
        
        if not big_size_dir.exists():
            return
        
        try:
            for file_path in big_size_dir.iterdir():
                if not file_path.is_file():
                    continue
                
                # Buscar transcripción asociada
                json_file = processed_dir / f"{file_path.stem}.json"
                
                if json_file.exists():
                    # Mover archivo de audio procesado a processed
                    processed_path = processed_dir / file_path.name
                    shutil.move(str(file_path), str(processed_path))
                    logger.info(f"Archivo big_size procesado movido a processed: {file_path} -> {processed_path}")
            
        except Exception as e:
            logger.error(f"Error al procesar archivos big_size: {e}")
    
    def get_statistics(self) -> dict:
        """
        Obtiene estadísticas del estado actual del gestor de archivos.
        
        Returns:
            Dict con conteo de archivos por estado y tamaño total
        """
        stats = {
            'total_pending': 0,
            'total_processing': 0,
            'total_processed': 0,
            'total_big_size': 0,
            'total_size_bytes': 0,
            'cache_size': len(self.hash_cache)
        }
        
        directories = [
            ('pending', 'total_pending'),
            ('processing', 'total_processing'),
            ('processed', 'total_processed'),
            ('big_size', 'total_big_size')
        ]
        
        for dir_name, stats_key in directories:
            dir_path = self.base_path / dir_name
            
            if dir_path.exists():
                try:
                    files = list(dir_path.iterdir())
                    stats[stats_key] = len(files)
                    stats['total_size_bytes'] += sum(
                        f.stat().st_size for f in files if f.is_file()
                    )
                except Exception as e:
                    logger.error(f"Error al leer directorio {dir_name}: {e}")
        
        return stats


# Funciones de utilidad
def get_file_size(file_path: str) -> int:
    """
    Obtiene el tamaño de un archivo en bytes.
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        Tamaño del archivo en bytes
        
    Raises:
        FileNotFoundError: Si el archivo no existe
    """
    return Path(file_path).stat().st_size


def format_file_size(size_bytes: Union[int, float]) -> str:
    """
    Formatea un tamaño de archivo en una representación legible.
    
    Args:
        size_bytes: Tamaño en bytes
        
    Returns:
        Cadena formateada (ej: '1.5 MB')
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def is_audio_file(file_path: str) -> bool:
    """
    Verifica si un archivo es un archivo de audio soportado.
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        True si es un archivo de audio soportado
    """
    audio_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.flac'}
    return Path(file_path).suffix.lower() in audio_extensions
