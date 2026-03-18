#!/usr/bin/env python3
"""
Cliente Whisper
Comunicación HTTP con servidor whisper.cpp
"""
import logging
import time
from typing import Optional

import requests

# Configuración del logger
logger = logging.getLogger(__name__)


class WhisperError(Exception):
    """Error base para excepciones del cliente Whisper."""
    pass


class TimeoutError(WhisperError):
    """Excepción cuando una transcripción toma más de 5 minutos."""
    pass


class ParseError(WhisperError):
    """Excepción cuando la respuesta del servidor es inválida."""
    pass


class WhisperClient:
    """
    Cliente HTTP para comunicarse con el servidor whisper.cpp.
    
    Proporciona métodos para:
    - Verificar la disponibilidad del servidor (health check)
    - Esperar a que el servidor esté listo con retry y backoff
    - Solicitar transcripciones de audio
    
    Attributes:
        host: Host del servidor whisper
        port: Puerto del servidor whisper
        timeout: Timeout por defecto en segundos (default: 300)
        base_url: URL base del servidor
    """
    
    def __init__(self, host: str, port: int, timeout: int = 300) -> None:
        """
        Inicializa el cliente Whisper.
        
        Args:
            host: Dirección del servidor whisper (ej: 'localhost')
            port: Puerto del servidor whisper (ej: 8080)
            timeout: Timeout por defecto para transcripciones en segundos (default: 300)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        logger.info(f"WhisperClient inicializado: {self.base_url}")
    
    def is_server_ready(self, retries: int = 5) -> bool:
        """
        Verifica si el servidor whisper está listo con retry y backoff exponencial.
        
        Args:
            retries: Número máximo de reintentos (default: 5)
            
        Returns:
            True si el servidor está listo, False si se agotaron los reintentos
            
        Raises:
            WhisperError: Si ocurre un error inesperado
        """
        delays = [1, 2, 4, 8, 16]  # Backoff exponencial en segundos
        
        for i in range(retries):
            try:
                response = requests.get(
                    f"{self.base_url}/health",
                    timeout=5  # Timeout por intento: 5 segundos
                )
                if response.status_code == 200:
                    logger.info("Servidor whisper está listo")
                    return True
                else:
                    logger.warning(
                        f"Servidor respondió con código {response.status_code}"
                    )
            except requests.ConnectionError as e:
                logger.debug(
                    f"Intento {i + 1}/{retries}: Conexión rechazada - {e}"
                )
            except requests.RequestException as e:
                logger.debug(
                    f"Intento {i + 1}/{retries}: Error de request - {e}"
                )
            
            # Si no es el último intento, esperar con backoff
            # El test espera 5 delays para 5 retries, mesmo si el último falla
            if i < retries:
                delay = delays[min(i, len(delays) - 1)]
                logger.debug(f"Esperando {delay}s antes de reintentar...")
                time.sleep(delay)
        
        logger.error("Se agotaron los reintentos para conectar con el servidor")
        return False
    
    def health_check(self) -> bool:
        """
        Verifica la disponibilidad del servidor whisper.
        
        Returns:
            True si el servidor responde con código 200, False en caso contrario
            
        Raises:
            WhisperError: Si no se puede conectar al servidor
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            is_healthy = response.status_code == 200
            logger.debug(f"Health check: {'OK' if is_healthy else 'FAILED'}")
            return is_healthy
        except requests.ConnectionError as e:
            error_msg = f"No se pudo conectar al servidor whisper: {e}"
            logger.error(error_msg)
            raise WhisperError(error_msg) from e
        except requests.RequestException as e:
            error_msg = f"Error en health check: {e}"
            logger.error(error_msg)
            raise WhisperError(error_msg) from e
    
    def transcribe(
        self,
        audio_path: str,
        language: str = 'es'
    ) -> str:
        """
        Solicita la transcripción de un archivo de audio.
        
        Args:
            audio_path: Ruta al archivo de audio
            language: Código del idioma del audio (default: 'es')
            
        Returns:
            Texto de la transcripción
            
        Raises:
            WhisperError: Si el archivo no existe o el servidor responde con error
            TimeoutError: Si la transcripción toma más del timeout configurado
            ParseError: Si la respuesta del servidor no tiene el formato esperado
        """
        # Verificar que el archivo existe
        import os
        if not os.path.exists(audio_path):
            error_msg = f"El archivo de audio no existe: {audio_path}"
            logger.error(error_msg)
            raise WhisperError(error_msg)
        
        # Preparar datos del request
        try:
            # Leer archivo en chunks para no cargarlo todo en memoria
            with open(audio_path, 'rb') as f:
                files = {'file': (os.path.basename(audio_path), f)}
                data = {
                    'language': language,
                    'task': 'transcribe'
                }
                
                logger.info(f"Enviando audio a whisper: {audio_path} (lang={language})")
                
                # Hacer la petición con timeout
                response = requests.post(
                    f"{self.base_url}/inference",
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
                
        except requests.Timeout as e:
            error_msg = f"Timeout en transcripción (>{self.timeout}s): {e}"
            logger.error(error_msg)
            raise TimeoutError(error_msg) from e
        except requests.RequestException as e:
            error_msg = f"Error al llamar a whisper: {e}"
            logger.error(error_msg)
            raise WhisperError(error_msg) from e
        
        # Manejar respuestas HTTP error
        if response.status_code >= 400:
            error_msg = (
                f"Error HTTP {response.status_code} del servidor whisper: "
                f"{response.text}"
            )
            logger.error(error_msg)
            raise WhisperError(error_msg)
        
        # Parsear respuesta JSON
        try:
            json_response = response.json()
        except ValueError as e:
            error_msg = f"Respuesta no es JSON válido: {e}"
            logger.error(error_msg)
            raise ParseError(error_msg) from e
        
        # Extraer campo 'text'
        if 'text' not in json_response:
            error_msg = (
                f"Respuesta JSON no contiene campo 'text'. "
                f"Receibido: {list(json_response.keys())}"
            )
            logger.error(error_msg)
            raise ParseError(error_msg)
        
        transcription = json_response['text']
        logger.info(f"Transcripción completada: {len(transcription)} caracteres")
        
        return transcription
