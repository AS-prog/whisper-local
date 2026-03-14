-- ============================================================================
-- MIGRACIÓN INICIAL - whisper-local v2.1
-- ============================================================================
-- Script de creación del schema inicial para la base de datos SQLite
-- Fecha: 2026-03-14
-- Descripción: Crea todas las tablas necesarias para el sistema de transcripción
-- ============================================================================

-- Activar llaves foráneas (SQLite las desactiva por defecto)
PRAGMA foreign_keys = ON;

-- ============================================================================
-- TABLA: jobs
-- Descripción: Almacena los trabajos de transcripción de audio
-- ============================================================================

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_hash TEXT UNIQUE,                          -- Para cache y evitar duplicados
    file_size_mb REAL,                              -- Tamaño del archivo en MB
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) NOT NULL DEFAULT 'pending',
    queue TEXT CHECK(queue IN ('pending', 'big_files')),  -- Para manejar archivos grandes por separado
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,                             -- Mensaje de error en caso de fallo
    retry_count INTEGER DEFAULT 0,                  -- Número de intentos en caso de fallo
    user_id TEXT,                                   -- Para rate limiting por usuario
    platform TEXT CHECK(platform IN ('telegram', 'discord', 'cli')),  -- Plataforma de origen
    progress INTEGER DEFAULT 0,                     -- Progreso de transcripción (0-100)
    chunks_total INTEGER DEFAULT 1,                 -- Número total de segmentos si se divide el archivo
    chunks_completed INTEGER DEFAULT 0              -- Número de segmentos completados
);

-- ============================================================================
-- TABLA: transcription_cache
-- Descripción: Cache de transcripciones para mejorar performance
-- ============================================================================

CREATE TABLE transcription_cache (
    file_hash TEXT PRIMARY KEY,                     -- Hash único del archivo
    transcription TEXT NOT NULL,                    -- La transcripción en sí
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Fecha de creación de la transcripción
    access_count INTEGER DEFAULT 1,                 -- Número de veces que se ha accedido
    last_accessed TIMESTAMP                         -- Última vez que se accedió a este registro
);

-- ============================================================================
-- TABLA: rate_limits
-- Descripción: Control de límites de uso por usuario
-- ============================================================================

CREATE TABLE rate_limits (
    user_id TEXT NOT NULL,                          -- ID del usuario
    platform TEXT NOT NULL,                         -- Plataforma de usuario ('telegram', 'discord', 'cli')
    file_count INTEGER DEFAULT 1,                   -- Número de archivos procesados
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Inicio de la ventana de tiempo
    PRIMARY KEY (user_id, platform, window_start)   -- Clave primaria compuesta
);

-- ============================================================================
-- TABLA: metrics
-- Descripción: Métricas del sistema para monitoreo
-- ============================================================================

CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,                      -- Nombre de la métrica
    metric_value REAL NOT NULL,                     -- Valor numérico de la métrica
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Fecha de registro de la métrica
);

-- ============================================================================
-- ÍNDICES: Para optimizar las consultas más comunes
-- ============================================================================

-- Índice para búsqueda rápida por estado de job
CREATE INDEX idx_jobs_status ON jobs(status);

-- Índice para filtrar jobs por cola
CREATE INDEX idx_jobs_queue ON jobs(queue);

-- Índice para buscar jobs por usuario (importante para rate limiting)
CREATE INDEX idx_jobs_user ON jobs(user_id);

-- Índice para acceso rápido al cache por hash
CREATE INDEX idx_cache_hash ON transcription_cache(file_hash);

-- Índices adicionales que podrían ser útiles para consultas frecuentes
CREATE INDEX idx_jobs_platform ON jobs(platform);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_metrics_name ON metrics(metric_name);
CREATE INDEX idx_metrics_timestamp ON metrics(recorded_at);

-- ============================================================================
-- FIN DEL SCRIPT DE MIGRACIÓN
-- ============================================================================
