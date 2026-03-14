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
| **phase1-auditor** | kimi-k2.5 | Tester que lee las notas de la tarea, ejecuta el script de prueba existente y reporta resultados al orquestador | `~/.config/opencode/agents/phase1-auditor.md` | Verificación post-implementación de los 4 módulos de Fase 1 |

### Flujo de Uso de Agentes por Fase

**Fase 0 (Infraestructura):**
- `data-engineer` → Análisis y coordinación
- `sql-specialist` → Diseño del schema SQLite (Tarea 0.4)
- `git-manager` → Commits iniciales

**Fase 1 (Core Asíncrono):**
- `data-engineer` → Orquestación
- `tdd-architect` → Diseño de tests (Tarea 5.1)
- `python-coder` → Implementación de database.py, job_queue.py, file_manager.py, audio_processor.py
- `phase1-auditor` → Auditoría en frío post-implementación (lee spec → diseña escenarios → lee código → ejecuta → informa)
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

### Agente Tester: @phase1-auditor

Tester post-implementación para Fase 1. Lee las notas de la tarea, ejecuta el script de prueba ya existente y reporta los resultados al orquestador. No escribe pruebas nuevas.

**Ruta:** `~/.config/opencode/agents/phase1-auditor.md`
**Modelo:** kimi-k2.5
**Permisos:** Solo lectura + bash

**Flujo:**
```
Lee docs/tasks/phase-1-core.md → Lee src/*.py → Ejecuta tests/audit/cold_test_phase1.py → Reporta
```

**Invocación:**
```
@phase1-auditor Verifica la implementación de Fase 1.
Notas: docs/tasks/phase-1-core.md
Script: tests/audit/cold_test_phase1.py
```

**Documentación extendida:** [`docs/agents/phase1-auditor.md`](docs/agents/phase1-auditor.md)

---

### Convenciones de Uso de Agentes

1. **Invocación**: Usar `@nombre-agente` para invocar un agente específico
2. **Contexto**: Proporcionar el contexto completo del proyecto y la tarea actual
3. **Secuencia**: Seguir el orden TDD → Implementación → Auditoría → Revisión
4. **Commits**: Usar `git-manager` para todos los commits con mensajes semánticos
5. **Documentación**: Todos los agentes generan salida en español

---

## Protocolo de Inicio de Sesión

Cada vez que se inicie una nueva sesión de trabajo, los agentes deben seguir este protocolo para establecer el contexto actual del proyecto:

### Paso 1: Escaneo de Ramas Git

El agente `@git-manager` (o el agente principal) debe:

```bash
# Ver estado actual del repositorio
git status

# Listar todas las ramas
git branch -a

# Ver el último commit en la rama actual
git log -1 --oneline --format="%h %s (%cr) by %an"

# Ver historial reciente (últimos 5 commits)
git log -5 --oneline
```

**Checkpoint**: El hash del último commit (`99d1e74`) establece el punto de partida de la sesión.

### Paso 2: Revisión de Documentación de Sesiones

Después de obtener el checkpoint de Git, el agente debe:

1. **Listar sesiones anteriores**:
   ```bash
   ls -la docs/*.md | grep -E '[0-9]{8}\.md'
   ```

2. **Identificar la sesión más reciente**:
   - Buscar el archivo con fecha más reciente (formato: `YYYYMMDD.md`)
   - Ejemplo: `docs/20260313.md`

3. **Leer la sesión más reciente** para entender:
   - Qué se hizo en la sesión anterior
   - Qué fase del proyecto está activa
   - Qué tareas están pendientes
   - Qué decisiones se tomaron
   - Próximos pasos recomendados

### Paso 3: Determinar Estado del Proyecto

Con la información de Git y la sesión anterior, el agente debe poder responder:

**"¿En qué estado está el proyecto?"**

Template de respuesta:

```
📊 ESTADO DEL PROYECTO - whisper-local v2.1
═══════════════════════════════════════════════

🔄 Checkpoint Git: 99d1e74
📅 Última sesión: docs/20260313.md (2026-03-13)
🌿 Rama actual: main

📋 FASES COMPLETADAS:
   ⏳ Fase 0: Infraestructura (0/4 tareas)
   ⏳ Fase 1: Core Asíncrono (0/4 tareas)
   ⏳ Fase 2: Worker y Cliente (0/3 tareas)
   ⏳ Fase 3: Bots (0/3 tareas)
   ⏳ Fase 4: CLI (0/3 tareas)
   ⏳ Fase 5: Testing (0/4 tareas)

🎯 FASE ACTIVA: Ninguna (en planificación)
📝 TAREAS PENDIENTES: 21 totales
⏱️  TIEMPO ESTIMADO RESTANTE: ~55 horas

📁 ESTRUCTURA:
   ✅ Documentación de tareas separada por fases
   ✅ Asignación de agentes completada
   ⏳ Implementación de código: pendiente

💡 PRÓXIMO PASO RECOMENDADO:
   Iniciar Fase 0 con @sql-specialist → Tarea 0.4 (Schema DB)
```

### Paso 4: Sincronización de Contexto

Antes de comenzar cualquier tarea:

1. **Confirmar** con el usuario el estado detectado
2. **Preguntar** si hay cambios no commiteados que deban incluirse
3. **Verificar** si se debe continuar desde el último punto o cambiar de rama
4. **Actualizar** el archivo de sesiones si se detectan discrepancias

### Ejemplo de Inicio de Sesión

```
Agente: Voy a escanear el estado actual del proyecto...

[Ejecutando git status...]
[Ejecutando git log...]
[Leyendo docs/20260313.md...]

✅ Checkpoint establecido: 99d1e74
✅ Sesión anterior: 2026-03-13 (Restructuración de documentación)

📊 Estado detectado:
   - Rama: main
   - 21 tareas documentadas en 6 fases
   - Ninguna tarea iniciada
   - Documentación completa y estructurada

¿En qué estado está el proyecto?
→ En fase de planificación, listo para iniciar desarrollo.

¿Desea comenzar con la Fase 0 (Infraestructura)?
```

### Convención de Nomenclatura

- **Checkpoint**: Hash corto del último commit (ej: `99d1e74`)
- **Sesión**: Archivo `docs/YYYYMMDD.md`
- **Estado**: Una de [Planificación | En desarrollo | En testing | Completado]
- **Fase activa**: La fase con tareas en progreso

---

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
