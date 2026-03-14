#!/usr/bin/env python3
"""
Procesamiento de Audio
Conversión FFmpeg, validación y chunking.
"""

import os
import subprocess
import tempfile
import math
import logging
from pathlib import Path
from typing import Optional
from shutil import rmtree

# Configuración del logger
logger = logging.getLogger(__name__)

# Extensiones de audio soportadas
SUPPORTED_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac'}


class AudioProcessor:
    """
    Clase para procesar archivos de audio usando FFmpeg.
    
    Proporciona métodos para validar, convertir, particionar (chunking)
    y fusionar transcripciones de archivos de audio.
    """
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg'):
        """
        Inicializa el procesador de audio con la ruta a FFmpeg.
        
        Args:
            ffmpeg_path: Ruta al binario de FFmpeg. Por defecto 'ffmpeg'.
        """
        self.ffmpeg_path = ffmpeg_path
        self._verify_ffmpeg()
    
    def _verify_ffmpeg(self) -> None:
        """
        Verifica que FFmpeg esté instalado y доступен.
        
        Raises:
            FileNotFoundError: Si FFmpeg no se encuentra en el sistema.
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                timeout=5,
                check=True
            )
            logger.info("FFmpeg verificado correctamente")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"FFmpeg no encontrado en '{self.ffmpeg_path}'. "
                "Asegúrese de que FFmpeg esté instalado y en el PATH del sistema."
            )
        except subprocess.TimeoutExpired:
            raise FileNotFoundError(
                f"Timeout al verificar FFmpeg en '{self.ffmpeg_path}'"
            )
        except subprocess.CalledProcessError as e:
            raise FileNotFoundError(
                f"Error al ejecutar FFmpeg: {e.stderr.decode('utf-8') if e.stderr else str(e)}"
            )
    
    def validate_audio(self, file_path: str) -> tuple[bool, str]:
        """
        Valida que el archivo de audio sea compatible y no esté corrupto.
        
        Args:
            file_path: Ruta al archivo de audio a validar.
        
        Returns:
            Tuple (is_valid, error_message):
            - (True, "") si el archivo es válido
            - (False, "error_msg") si hay un error de validación
        """
        path = Path(file_path)
        
        # Verificar que el archivo existe
        if not path.exists():
            return False, f"El archivo no existe: {file_path}"
        
        # Verificar que es un archivo (no directorio)
        if not path.is_file():
            return False, f"La ruta no es un archivo: {file_path}"
        
        # Verificar extensión soportada
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return False, (
                f"Formato no soportado: {ext}. "
                f"Formatos soportados: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        
        # Verificar que el archivo no está vacío
        size = path.stat().st_size
        if size == 0:
            return False, "El archivo está vacío"
        
        # Usar ffprobe para verificar que no esté corrupto
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    str(path)
                ],
                capture_output=True,
                timeout=30,
                check=True
            )
            
            # Verificar duración > 1 segundo
            duration_str = result.stdout.decode('utf-8').strip()
            try:
                duration = float(duration_str)
                if duration <= 1.0:
                    return False, f"La duración del audio es demasiado corta: {duration:.2f}s (mínimo 1s)"
            except ValueError:
                return False, f"No se pudo determinar la duración del audio: {duration_str}"
            
            logger.info(f"Audio validado: {file_path} ({duration:.2f}s)")
            
        except subprocess.TimeoutExpired:
            return False, "Timeout al validator el archivo con ffprobe"
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
            return False, f"Error al validator el audio (probablemente corrupto): {error_msg}"
        
        return True, ""
    
    def get_duration(self, file_path: str) -> float:
        """
        Obtiene la duración del archivo de audio en segundos.
        
        Args:
            file_path: Ruta al archivo de audio.
        
        Returns:
            Duración del audio en segundos.
        
        Raises:
            FileNotFoundError: Si el archivo no existe.
            RuntimeError: Si no se puede determinar la duración.
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"El archivo no existe: {file_path}")
        
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    str(path)
                ],
                capture_output=True,
                timeout=30,
                check=True
            )
            
            duration_str = result.stdout.decode('utf-8').strip()
            duration = float(duration_str)
            
            if duration <= 0:
                raise RuntimeError(f"Duración inválida: {duration}")
            
            return duration
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
            raise RuntimeError(f"No se pudo obtener la duración del audio: {error_msg}")
        except ValueError as e:
            raise RuntimeError(f"Duración inválida del audio: {e}")
    
    def get_file_size_mb(self, file_path: str) -> float:
        """
        Obtiene el tamaño del archivo en megabytes.
        
        Args:
            file_path: Ruta al archivo de audio.
        
        Returns:
            Tamaño del archivo en MB (con 2 decimales).
        
        Raises:
            FileNotFoundError: Si el archivo no existe.
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"El archivo no existe: {file_path}")
        
        size_bytes = path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        return size_mb
    
    def convert_to_wav(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Convierte un archivo de audio a WAV (16kHz, mono, PCM 16-bit).
        
        Args:
            input_path: Ruta al archivo de entrada.
            output_path: Ruta de salida. Si None, usa input_path + '.wav'.
        
        Returns:
            Ruta al archivo WAV generado.
        
        Raises:
            FileNotFoundError: Si el archivo de entrada no existe.
            RuntimeError: Si la conversión falla.
            subprocess.TimeoutExpired: Si supera el timeout de 5 minutos.
        """
        path = Path(input_path)
        
        if not path.exists():
            raise FileNotFoundError(f"El archivo de origen no existe: {input_path}")
        
        # Definir ruta de salida si no se especifica
        if output_path is None:
            output_path = str(path.with_suffix('.wav'))
        
        logger.info(f"Convirtiendo {input_path} a WAV: {output_path}")
        
        try:
            # Comando FFmpeg para convertir a WAV 16kHz mono
            result = subprocess.run(
                [
                    self.ffmpeg_path,
                    '-i', str(path),
                    '-ar', '16000',
                    '-ac', '1',
                    '-c:a', 'pcm_s16le',
                    '-y',
                    output_path
                ],
                capture_output=True,
                timeout=300,  # 5 minutos
                check=True
            )
            
            # Verificar que el archivo de salida fue creado
            if not Path(output_path).exists():
                raise RuntimeError(
                    "FFmpeg terminó exitosamente pero no se creó el archivo de salida"
                )
            
            logger.info(f"Conversión exitosa: {output_path}")
            return output_path
            
        except subprocess.TimeoutExpired as e:
            error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
            timeout_error = subprocess.TimeoutExpired(
                f"Timeout al convertir audio: {error_msg}",
                timeout=e.timeout
            )
            raise timeout_error
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
            raise RuntimeError(f"Error al convertir.audio: {error_msg}")
    
    def needs_chunking(self, file_path: str, max_size_mb: int = 40) -> bool:
        """
        Determina si el archivo necesita ser particionado (chunking).
        
        Criteria de chunking:
        - Tamaño del archivo > max_size_mb
        - Duración > chunk_duration (default 600s = 10 min)
        
        Args:
            file_path: Ruta al archivo de audio.
            max_size_mb: Tamaño máximo en MB antes de requerir chunking.
        
        Returns:
            True si el archivo necesita chunking, False en caso contrario.
        
        Note:
            Si no se puede determinar el tamaño o duración del archivo
            (ej. archivo inválido), retornará False安静o requerir chunking.
        """
        # Verificar tamaño
        try:
            size_mb = self.get_file_size_mb(file_path)
            # Obtener tamaño en bytes para comparación más precisa
            path = Path(file_path)
            size_bytes = path.stat().st_size
            size_mb_exact = size_bytes / (1024 * 1024)  # Sin truncar
            
            if size_mb_exact > max_size_mb:
                logger.info(f"Archivo需要 chunking por tamaño: {size_mb:.2f}MB > {max_size_mb}MB")
                return True
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.warning(f"No se pudo verificar tamaño del archivo: {e}")
            # No lanzar excepción, solo no chunk por tamaño
        
        # Verificar duración (WAV 16kHz mono ~500KB/s, entonces 40MB ~80min)
        # Consideramos chunking si la duración supera 10 minutos
        try:
            duration = self.get_duration(file_path)
            if duration > 600:  # 10 minutos
                logger.info(f"Archivo需要 chunking por duración: {duration:.2f}s > 600s")
                return True
        except FileNotFoundError:
            raise
        except (subprocess.TimeoutExpired, RuntimeError, ValueError) as e:
            # Capturar errores de procesamiento de audio y no lanzar excepción
            logger.warning(f"No se pudo verificar duración del archivo (posiblemente inválido): {e}")
            # No chunk por duración si no se puede determinar
        except Exception as e:
            logger.warning(f"Error inesperado al verificar duración del archivo: {e}")
            # No chunk por duración en caso de error inesperado
        
        return False
    
    def create_chunks(
        self,
        file_path: str,
        chunk_duration: int = 600
    ) -> list[str]:
        """
        Particiona un archivo de audio en chunks con overlap de 2 segundos.
        
        Args:
            file_path: Ruta al archivo de audio.
            chunk_duration: Duración de cada chunk en segundos (default 600 = 10 min).
        
        Returns:
            Lista de rutas a los archivos de chunk generados.
        
        Raises:
            FileNotFoundError: Si el archivo de entrada no existe.
            RuntimeError: Si falla la creación de chunks.
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"El archivo no existe: {file_path}")
        
        # Obtener duración total
        total_duration = self.get_duration(str(path))
        logger.info(f"Creando chunks de {chunk_duration}s para audio de {total_duration:.2f}s")
        
        # Crear carpeta temporal para los chunks
        temp_dir = tempfile.mkdtemp(prefix='whisper_chunk_')
        logger.debug(f"Carpeta temporal creada: {temp_dir}")
        
        try:
            # Calcular número de chunks
            num_chunks = math.ceil(total_duration / chunk_duration)
            
            chunks = []
            
            for i in range(num_chunks):
                # Calcular tiempo de inicio (con overlap de 2s para chunks después del primero)
                start_time = max(0, i * chunk_duration - (2 if i > 0 else 0))
                
                # Calcular duración (puede ser menor para el último chunk)
                remaining = total_duration - start_time
                duration = min(chunk_duration + 2, remaining)
                
                # Definir nombre del chunk
                chunk_name = f"{path.stem}_chunk_{i:03d}{path.suffix}"
                chunk_path = Path(temp_dir) / chunk_name
                
                logger.debug(
                    f"Chunk {i}: start={start_time:.2f}s, duration={duration:.2f}s, "
                    f"output={chunk_name}"
                )
                
                # Ejecutar FFmpeg para crear el chunk
                try:
                    result = subprocess.run(
                        [
                            self.ffmpeg_path,
                            '-i', str(path),
                            '-ss', f'{start_time:.2f}',
                            '-t', f'{duration:.2f}',
                            '-c', 'copy',
                            '-y',
                            str(chunk_path)
                        ],
                        capture_output=True,
                        timeout=120,  # 2 minutos por chunk
                        check=True
                    )
                    
                    # Verificar que el chunk se creó
                    if chunk_path.exists():
                        chunks.append(str(chunk_path))
                        logger.debug(f"Chunk creado: {chunk_path}")
                    else:
                        raise RuntimeError(f"No se pudo crear el chunk: {chunk_path}")
                        
                except subprocess.CalledProcessError as e:
                    error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
                    raise RuntimeError(f"Error al crear chunk {i}: {error_msg}")
                except subprocess.TimeoutExpired as e:
                    raise RuntimeError(
                        f"Timeout al crear chunk {i}. "
                        f"Considere reducir chunk_duration."
                    )
            
            logger.info(f"Se crearon {len(chunks)} chunks en {temp_dir}")
            return chunks
            
        except Exception:
            # Limpiar archivos temporales en caso de error
            logger.error(f"Error al crear chunks, limpiando {temp_dir}")
            rmtree(temp_dir, ignore_errors=True)
            raise
    
    def merge_transcriptions(
        self,
        transcriptions: list[str],
        overlaps: Optional[list[str]] = None
    ) -> str:
        """
        Fusiona transcripciones de chunks eliminando el contenido duplicado del overlap.
        
        Args:
            transcriptions: Lista de textos de transcripción de cada chunk.
            overlaps: Lista de textos de overlap para eliminar (opcional).
        
        Returns:
            Texto fusionado sin duplicados de overlap.
        
        Note:
            Si overlaps no se proporciona, elimina duplicados basados en
            comparación de última parte del chunk con primera parte del siguiente.
        """
        if not transcriptions:
            return ""
        
        if len(transcriptions) == 1:
            return transcriptions[0]
        
        merged = transcriptions[0]
        
        for i in range(1, len(transcriptions)):
            current = transcriptions[i]
            
            # Determinar qué texto usar para detectar overlap
            if overlaps and i - 1 < len(overlaps):
                overlap_text = overlaps[i - 1]
            else:
                overlap_text = None
            
            # Eliminar duplicados de overlap
            if overlap_text:
                # Si se proporciona texto de overlap, eliminarlo del inicio del siguiente chunk
                current = current.lstrip()
                if current.startswith(overlap_text):
                    current = current[len(overlap_text):].lstrip()
            else:
                # Comparar últimos 30 caracteres con primeros 30 del siguiente chunk
                last_chars = merged[-30:].lower().strip()
                first_chars = current[:30].lower().strip()
                
                if last_chars == first_chars:
                    # Encontrar el punto de superposición exacto
                    overlap_len = len(last_chars)
                    current = current[overlap_len:].lstrip()
            
            # Concatenar con un espacio
            if not merged.endswith(' '):
                merged += ' '
            merged += current
        
        logger.info(
            f"Fusionadas {len(transcriptions)} transcripciones. "
            f"Total caracteres: {len(merged)}"
        )
        
        return merged
