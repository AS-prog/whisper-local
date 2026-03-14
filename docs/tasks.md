# Documento de Tareas - whisper-local v2.1

**Fecha de creación:** 2026-03-13  
**Versión:** 2.1  
**Estado:** Planificación

---

## Índice de Fases

| Fase | Descripción | Tareas | Tiempo | Estado |
|------|-------------|--------|--------|--------|
| **[Fase 0](tasks/phase-0-infraestructura.md)** | Infraestructura Segura | 4 | 4-6h | ⏳ |
| **[Fase 1](tasks/phase-1-core.md)** | Core Asíncrono | 4 | 14h | ⏳ |
| **[Fase 2](tasks/phase-2-worker.md)** | Worker y Cliente Whisper | 3 | 7h | ⏳ |
| **[Fase 3](tasks/phase-3-bots.md)** | Bots con Progreso | 3 | 10h | ⏳ |
| **[Fase 4](tasks/phase-4-cli.md)** | CLI y Tooling | 3 | 7h | ⏳ |
| **[Fase 5](tasks/phase-5-testing.md)** | Testing y Optimización | 4 | 13h | ⏳ |

**Tiempo Total Estimado:** ~55 horas

---

## Resumen de Tareas por Agente

### @sql-specialist
- **0.4** Schema de Base de Datos
- **1.1** Módulo Database (parcial)

### @python-coder
- **1.1** Módulo Database (parcial)
- **1.2** Sistema de Colas
- **1.3** Gestión de Archivos
- **1.4** Procesamiento de Audio
- **2.1** Cliente Whisper
- **2.2** Worker (parcial)
- **3.1** Bot Telegram
- **3.2** Bot Discord
- **3.3** Progress Notifier
- **4.1** CLI
- **4.2** Logging
- **4.3** Utilidades
- **5.1** Tests Unitarios (parcial)
- **5.3** Optimizaciones

### @data-engineer
- **2.2** Worker (orquestación)
- **5.4** Documentación

### @tdd-architect
- **5.1** Tests Unitarios (diseño)
- **5.2** Tests Integración

### @phase1-auditor
- **1.1–1.4** Auditoría en frío post-implementación (todos los módulos de Fase 1)

### @code-reviewer
- Revisión de todos los módulos implementados

### @git-manager
- Commits semánticos en cada fase

---

## Flujo de Trabajo Recomendado

```
FASE 0: Infraestructura
└── @sql-specialist → Schema de BD

FASE 1: Core Asíncrono
├── @tdd-architect → Diseñar tests
├── @python-coder → Database, Queue, FileManager, AudioProcessor
├── @phase1-auditor → Auditoría en frío (spec → escenarios → ejecución → informe)
└── @code-reviewer → Revisión

FASE 2: Worker y Cliente
├── @python-coder → WhisperClient, Worker
└── @data-engineer → Orquestación

FASE 3: Bots
├── @python-coder → TelegramBot, DiscordBot, ProgressNotifier
└── @code-reviewer → Revisión

FASE 4: CLI y Tooling
├── @python-coder → CLI, Logging, Utilidades
└── @code-reviewer → Revisión final

FASE 5: Testing
├── @tdd-architect → Suite de tests
├── @python-coder → Implementación
└── @data-engineer → Documentación
```

---

## Definition of Done

Para cada tarea, debe cumplirse:

1. ✅ Código escrito y funcional
2. ✅ Tests unitarios (si aplica)
3. ✅ Documentación de funciones (docstrings)
4. ✅ Probado manualmente
5. ✅ Sin errores de linting (`flake8`, `black`)
6. ✅ Commit con mensaje descriptivo
7. ✅ Actualizar estado en documento de fase

---

## Convenciones de Código

- **Nombres:** snake_case para variables/funciones, PascalCase para clases
- **Imports:** Ordenar alfabéticamente, agrupar por stdlib, third-party, local
- **Tipado:** Usar type hints en todas las funciones públicas
- **Async:** Todas las operaciones de red deben ser async
- **Errores:** Usar excepciones personalizadas, no retornar None para errores
- **Idioma:** Código en inglés, comentarios y docstrings en español

---

## Priorización (MVP)

### Must Have
- Fase 0: Seguridad (.env)
- Fase 1: Database, Queue, FileManager básico
- Fase 2: Worker básico sin chunking
- Fase 3: Telegram bot básico
- Fase 4: CLI básico (process, status)

### Should Have
- Fase 1: Chunking, AudioProcessor completo
- Fase 2: Scripts, Docker
- Fase 3: Discord bot
- Fase 4: Métricas, utilidades

### Nice to Have
- Fase 3: Notificaciones de progreso detalladas
- Fase 4: Config management
- Fase 5: Tests completos, optimizaciones avanzadas

---

## Dependencias Externas

- Docker y Docker Compose
- FFmpeg instalado en sistema
- Python 3.9+
- Cuenta de Telegram Bot
- Cuenta de Discord Bot
- Modelo whisper descargado

---

**Última actualización:** 2026-03-13  
**Responsable:** @usuario  
**Estado:** En planificación

---

## Agentes del Sistema de Orquestación

Este proyecto utiliza el [Sistema de Orquestación de Agentes](/Users/andresrsotelo_mm/.config/opencode/agents/sistema-orquestacion-agentes.md) para coordinar el desarrollo.

### Agentes Disponibles

| Agente | Tipo | Especialización | Modelo |
|--------|------|-----------------|--------|
| **@data-engineer** | Primary/Subagent | Ingeniero de Datos Senior | kimi-k2.5 |
| **@tdd-architect** | Subagent | Diseño de suites de pruebas | kimi-k2.5 |
| **@python-coder** | Subagent | Desarrollo Python | qwen3-coder-next |
| **@sql-specialist** | Subagent | SQL y bases de datos | qwen3-coder-plus |
| **@code-reviewer** | Subagent | Revisión de código | glm-5 |
| **@git-manager** | Subagent | Control de versiones | MiniMax-M2.5 |
| **@config-guardian** | Subagent | Automatización de PRs | qwen3.5-plus |
| **@phase1-auditor** | Subagent | Auditoría independiente en frío — Fase 1 | kimi-k2.5 |

### Convenciones de Uso

1. **Invocación**: Usar `@nombre-agente` para invocar un agente específico
2. **Contexto**: Proporcionar el contexto completo del proyecto y la tarea actual
3. **Secuencia**: Seguir el orden TDD → Implementación → Revisión
4. **Commits**: Usar `@git-manager` para todos los commits con mensajes semánticos
5. **Documentación**: Todos los agentes generan salida en español
