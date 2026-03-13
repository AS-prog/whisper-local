#!/usr/bin/env python3
import os
import json
import time
import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WHISPER_URL = "http://localhost:8080/inference"
INPUT_DIR = Path.home() / "projects" / "whisper-local" / "inputs"
OUTPUT_DIR = Path.home() / "projects" / "whisper-local" / "transcriptions"
PROCESSED_DIR = INPUT_DIR / "processed"

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(INPUT_DIR / "whisper_processor.log")
    ]
)
logger = logging.getLogger(__name__)


def convert_to_wav(file_path: Path) -> Path | None:
    """Convierte archivo de audio a WAV usando ffmpeg."""
    wav_path = file_path.with_suffix(".wav")
    
    try:
        cmd = [
            "ffmpeg", "-i", str(file_path),
            "-ar", "16000", "-ac", "1",
            "-loglevel", "error",
            str(wav_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Convertido {file_path.name} a WAV")
        return wav_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al convertir {file_path.name}: {e.stderr.decode() if e.stderr else e}")
        return None
    except FileNotFoundError:
        logger.error("ffmpeg no encontrado. Instálalo con: brew install ffmpeg")
        return None


def transcribe_audio(file_path: Path) -> dict | None:
    """Envía archivo al servidor whisper y retorna la transcripción."""
    original_path = file_path
    needs_conversion = file_path.suffix.lower() in {".m4a", ".mp3", ".ogg", ".flac"}
    
    if needs_conversion:
        wav_path = convert_to_wav(file_path)
        if not wav_path:
            return None
        file_path = wav_path
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f)}
            data = {
                "response_format": "json",
                "language": "es"
            }
            
            logger.info(f"Enviando {file_path.name} al servidor whisper...")
            response = requests.post(WHISPER_URL, files=files, data=data, timeout=300)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Transcripción exitosa para {original_path.name}")
                
                if needs_conversion and file_path.exists():
                    file_path.unlink()
                
                return result
            else:
                logger.error(f"Error del servidor: {response.status_code} - {response.text}")
                return None
                
    except requests.exceptions.ConnectionError:
        logger.error("No se pudo conectar al servidor whisper. ¿Está ejecutándose en localhost:8080?")
        return None
    except Exception as e:
        logger.error(f"Error al transcribir {original_path.name}: {e}")
        return None


def save_transcription(filename: str, result: dict) -> Path:
    """Guarda la transcripción en un archivo JSON."""
    base_name = Path(filename).stem
    output_path = OUTPUT_DIR / f"{base_name}.json"
    
    transcription_data = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "text": result.get("text", ""),
        "language": "es"
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(transcription_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Transcripción guardada en {output_path}")
    return output_path


def move_to_processed(file_path: Path) -> None:
    """Mueve el archivo original a la carpeta processed."""
    PROCESSED_DIR.mkdir(exist_ok=True)
    destination = PROCESSED_DIR / file_path.name
    
    counter = 1
    while destination.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        destination = PROCESSED_DIR / f"{stem}_{counter}{suffix}"
        counter += 1
    
    file_path.rename(destination)
    logger.info(f"Archivo movido a {destination}")


class AudioFileHandler(FileSystemEventHandler):
    """Manejador que detecta nuevos archivos de audio."""
    
    def __init__(self):
        self.processing = set()
    
    def is_audio_file(self, path: str) -> bool:
        return Path(path).suffix.lower() in ALLOWED_EXTENSIONS
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        if not self.is_audio_file(file_path.name):
            return
        
        if file_path.name in self.processing:
            return
        
        self.processing.add(file_path.name)
        
        logger.info(f"Nuevo archivo detectado: {file_path.name}")
        
        time.sleep(1)
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                if file_path.exists() and file_path.stat().st_size > 0:
                    break
            except Exception:
                pass
            time.sleep(1)
        
        result = transcribe_audio(file_path)
        
        if result:
            save_transcription(file_path.name, result)
            move_to_processed(file_path)
        else:
            logger.warning(f"No se pudo transcribir {file_path.name}. Manteniendo en inputs/")
        
        self.processing.discard(file_path.name)


def process_existing_files():
    """Procesa archivos existentes en la carpeta inputs al iniciar."""
    logger.info("Buscando archivos existentes en inputs/...")
    
    for file_path in INPUT_DIR.iterdir():
        if file_path.is_file() and file_path.name != "whisper_processor.log" and AudioFileHandler().is_audio_file(file_path.name):
            logger.info(f"Procesando archivo existente: {file_path.name}")
            result = transcribe_audio(file_path)
            
            if result:
                save_transcription(file_path.name, result)
                move_to_processed(file_path)


def main():
    """Inicia el watcher de archivos."""
    logger.info("=" * 50)
    logger.info("Whisper Processor iniciado")
    logger.info(f"Input directory: {INPUT_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Whisper server: {WHISPER_URL}")
    logger.info("=" * 50)
    
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    PROCESSED_DIR.mkdir(exist_ok=True)
    
    process_existing_files()
    
    event_handler = AudioFileHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INPUT_DIR), recursive=False)
    observer.start()
    
    logger.info(f"Observando {INPUT_DIR}... Presiona Ctrl+C para salir")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo watcher...")
        observer.stop()
    
    observer.join()
    logger.info("Whisper Processor detenido")


if __name__ == "__main__":
    main()
