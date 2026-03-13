# Whisper Local - AGENTS.md

Este documento proporciona contexto para agentes IA sobre la estructura y propósito del proyecto.

## Propósito del Proyecto

Procesador de transcripciones de audio usando whisper.cpp con servidor REST local. Convierte archivos de audio a texto en español utilizando el modelo `ggml-large-v3-turbo`.

## Estructura de Directorios

```
whisper-local/
├── .git/                    # Repositorio Git
├── .gitignore               # Archivos ignorados por Git
├── README.md                # Documentación del proyecto
├── venv/                    # Entorno virtual Python
├── inputs/                  # Archivos de audio de entrada
│   ├── processed/           # Audios ya transcritos
│   └── whisper_processor.log # Log del procesador
├── transcriptions/          # Código y transcripciones
│   ├── app.py              # Procesador principal
│   ├── requirements.txt    # Dependencias Python
│   └── *.json              # Archivos de transcripción
└── whisper.cpp/            # Repositorio de whisper.cpp
    └── models/             # Modelos Whisper GGML
        └── ggml-large-v3-turbo.bin  # Modelo activo (1.5GB)
```

## Descripción de Cada Carpeta

### `venv/`

Entorno virtual Python que contiene las dependencias instaladas del proyecto. Se usa para ejecutar el procesador de transcripciones.

### `inputs/`

Directorio de entrada para archivos de audio. Aquí se copian los archivos de audio a transcribir.

- **Formatos soportados:** `.mp3`, `.wav`, `.ogg`, `.m4a`, `.flac`
- **Límite recomendado:** < 50MB (~30-40 min audio)

### `inputs/processed/`

Contiene los archivos de audio que ya han sido transcritos. El procesador mueve automáticamente los archivos procesados a esta carpeta.

### `inputs/whisper_processor.log`

Log de ejecución del procesador. Útil para debugging y seguimiento de transcripciones.

### `transcriptions/`

Contiene el código fuente del procesador y los archivos de transcripción generados.

- `app.py`: Procesador principal que detecta archivos, convierte a WAV, envía al servidor y guarda transcripciones
- `requirements.txt`: Dependencias Python del proyecto
- `*.json`: Archivos de transcripción generados (formato: `{filename}.json`)

### `whisper.cpp/`

Repositorio clonado de [whisper.cpp](https://github.com/ggerganov/whisper.cpp). Contiene el código fuente y binarios compilados.

### `whisper.cpp/models/`

Modelos Whisper en formato GGML. Contiene:

- `ggml-large-v3-turbo.bin`: Modelo activo (1.5GB) - mejor calidad
- Modelos de prueba para desarrollo

## Comandos Útiles

```bash
# Iniciar servidor whisper
cd whisper.cpp && ./build/bin/whisper-server -m models/ggml-large-v3-turbo.bin --port 8080 --host 0.0.0.0

# Ejecutar procesador
./venv/bin/python transcriptions/app.py

# Verificar estado del servidor
curl -s http://localhost:8080/health

# Ver logs del procesador
tail -f inputs/whisper_processor.log

# Apagar servidor
pkill -f "whisper-server"
```

## Notas Importantes

- La carpeta `inputs/` NO debe subirse a Git (contiene audios originales)
- Solo trackear: código fuente, configuraciones, modelos (si es necesario)
- El servidor whisper debe estar corriendo antes de ejecutar el procesador

## Convenciones de Código

- **Idioma del código**: Todo el código en inglés (nombres de variables, funciones, clases, etc.)
- **Nomenclatura**: kebab-case para nombres de archivos, snake_case para Python
- **Idioma de comentarios**: Español
- **Documentación**: Docstrings en español

---

## Agentes Disponibles

Este proyecto puede utilizar los siguientes agentes especializados ubicados en `~/.config/opencode/agentes/`:

### Agente Principal (Orquestador)

| Agente | Modelo | Descripción | Ruta |
|--------|--------|-------------|------|
| **data-engineer** | kimi-k2.5 | Ingeniero de Datos Senior que coordina workflows completos de desarrollo, orquestando subagentes según necesidad | `~/.config/opencode/agentes/data-engineer.md` |

### Subagentes Especializados

| Agente | Modelo | Descripción | Ruta | Uso Recomendado |
|--------|--------|-------------|------|-----------------|
| **tdd-architect** | kimi-k2.5 | Diseña suites de pruebas con TDD, asegurando documentación detallada en cada caso de prueba | `~/.config/opencode/agentes/tdd-architect.md` | Fase 5: Testing - Diseñar tests unitarios e integración |
| **python-coder** | qwen3-coder-next | Especialista en desarrollo Python que cumple estrictamente PEP 8 y estándares de tipado | `~/.config/opencode/agentes/python-coder.md` | Implementación de módulos src/*.py |
| **sql-specialist** | qwen3-coder-plus | Especialista en SQL que diseña, optimiza y ejecuta queries de alta performance | `~/.config/opencode/agentes/sql-specialist.md` | Fase 0.4: Schema de Base de Datos |
| **code-reviewer** | glm-5 | Revisa código Python buscando defectos, anti-patrones y oportunidades de mejora | `~/.config/opencode/agentes/code-reviewer.md` | Revisión final de cada módulo implementado |
| **git-manager** | MiniMax-M2.5 | Especialista en control de versiones, gestión de ramas y mensajes de commit semánticos | `~/.config/opencode/agentes/git-manager.md` | Gestión de commits y ramas durante el desarrollo |
| **config-guardian** | qwen3.5-plus | Agente especializado en automatización de PRs y monitoreo de repositorios | `~/.config/opencode/agentes/config-guardian.md` | Monitoreo de cambios en develop |

### Flujo de Uso de Agentes por Fase

**Fase 0 (Infraestructura):**
- `data-engineer` → Análisis y coordinación
- `sql-specialist` → Diseño del schema SQLite (Tarea 0.4)
- `git-manager` → Commits iniciales

**Fase 1 (Core Asíncrono):**
- `data-engineer` → Orquestación
- `tdd-architect` → Diseño de tests (Tarea 5.1)
- `python-coder` → Implementación de database.py, job_queue.py, file_manager.py, audio_processor.py
- `code-reviewer` → Revisión de cada módulo

**Fase 2 (Worker y Cliente):**
- `data-engineer` → Coordinación
- `python-coder` → Implementación de whisper_client.py, worker.py
- `code-reviewer` → Revisión

**Fase 3 (Bots):**
- `data-engineer` → Arquitectura de bots
- `python-coder` → Implementación de telegram_bot.py, discord_bot.py, progress_notifier.py
- `code-reviewer` → Revisión

**Fase 4 (CLI y Tooling):**
- `python-coder` → Implementación de cli.py, logger.py
- `code-reviewer` → Revisión

**Fase 5 (Testing y Optimización):**
- `tdd-architect` → Diseño completo de suite de tests
- `python-coder` → Implementación de tests/
- `code-reviewer` → Revisión final de cobertura

### Convenciones de Uso de Agentes

1. **Invocación**: Usar `@nombre-agente` para invocar un agente específico
2. **Contexto**: Proporcionar el contexto completo del proyecto y la tarea actual
3. **Secuencia**: Seguir el orden TDD → Implementación → Revisión
4. **Commits**: Usar `git-manager` para todos los commits con mensajes semánticos
5. **Documentación**: Todos los agentes generan salida en español

### Análisis para Asignación de Modelos

**Modelos Disponibles:**
- `qwen3.5-plus` - Thinking enabled (1024 tokens)
- `qwen3-max-2026-01-23` - Modelo general
- `qwen3-coder-next` - Especializado en código
- `qwen3-coder-plus` - Especializado en código (avanzado)
- `MiniMax-M2.5` - Thinking enabled (1024 tokens)
- `glm-5` - Thinking enabled (1024 tokens)
- `glm-4.7` - Thinking enabled (1024 tokens)
- `kimi-k2.5` - Multimodal (texto+imagen), Thinking enabled (1024 tokens)

**Criterios de Asignación:**
1. **Agentes de Razonamiento Profundo** (requieren thinking capability):
   - `tdd-architect` → Diseño de pruebas complejas, escenarios edge case
   - `data-engineer` → Orquestación multi-agente, decisiones arquitectónicas
   - `code-reviewer` → Análisis de seguridad, patrones y calidad

2. **Agentes Especializados en Código:**
   - `python-coder` → Implementación precisa de Python, PEP 8, type hints
   - `sql-specialist` → Optimización de queries, diseño de esquemas

3. **Agentes de Automatización:**
   - `config-guardian` → Monitoreo estructurado con validaciones
   - `git-manager` → Gestión de versiones, validaciones de seguridad
