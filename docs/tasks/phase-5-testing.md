# Fase 5: Testing y Optimización

**Objetivo:** Implementar tests completos, optimizaciones y documentación final

**Tiempo Estimado:** 13 horas
**Dependencias:** Fases 1-4 completadas

---

## Tarea 5.1: Tests Unitarios

**Objetivo:** Cobertura de código core

- [ ] **5.1.1** Configurar pytest
  - [ ] Añadir `pytest`, `pytest-asyncio`, `pytest-cov` a requirements.txt
  - [ ] Crear `pytest.ini`
  - [ ] Crear `tests/` directory
  
- [ ] **5.1.2** Tests para `database.py`
  - [ ] Setup/teardown de DB en memoria
  - [ ] Test CRUD de jobs
  - [ ] Test cache
  - [ ] Test rate limiting
  
- [ ] **5.1.3** Tests para `job_queue.py`
  - [ ] Test enqueue/dequeue
  - [ ] Test priorización
  - [ ] Test reintentos
  
- [ ] **5.1.4** Tests para `file_manager.py`
  - [ ] Test locks
  - [ ] Test hash
  - [ ] Test cleanup
  
- [ ] **5.1.5** Tests para `audio_processor.py`
  - [ ] Mock ffmpeg
  - [ ] Test validación
  - [ ] Test chunking
  
- [ ] **5.1.6** Ejecutar tests
  - [ ] `pytest tests/ -v --cov=src`
  - [ ] Meta: >80% cobertura

**Archivos:** `tests/test_*.py`, `pytest.ini`  
**Dependencias:** Fases 1-2  
**Tiempo estimado:** 4 horas  
**Agentes Asignados:** @tdd-architect + @python-coder

---

## Tarea 5.2: Tests de Integración

**Objetivo:** Flujo end-to-end

- [ ] **5.2.1** Tests para worker
  - [ ] Crear archivo de audio de prueba
  - [ ] Encolar
  - [ ] Ejecutar worker
  - [ ] Verificar resultado
  
- [ ] **5.2.2** Mock de servidor whisper
  - [ ] Crear servidor HTTP mock
  - [ ] Responder con transcripción fija
  - [ ] Test worker completo con mock
  
- [ ] **5.2.3** Tests e2e para bots (opcional)
  - [ ] Mock de APIs de Telegram/Discord
  - [ ] Enviar mensaje de prueba
  - [ ] Verificar que job se crea

**Archivos:** `tests/integration/`, `tests/mocks/`  
**Dependencias:** 5.1  
**Tiempo estimado:** 3 horas  
**Agente Asignado:** @tdd-architect

---

## Tarea 5.3: Optimizaciones

**Objetivo:** Mejoras de performance

- [ ] **5.3.1** Cache de transcripciones
  - [ ] Implementar tabla `transcription_cache`
  - [ ] Calcular SHA256 de archivo antes de procesar
  - [ ] Si hash existe: retornar transcripción cacheada
  - [ ] Actualizar access_count y last_accessed
  
- [ ] **5.3.2** Batch processing
  - [ ] Si hay múltiples archivos pequeños (<5MB):
  - [ ] Procesar en paralelo (hasta 3 simultáneos)
  - [ ] Cuidado con rate limits de whisper
  
- [ ] **5.3.3** Compresión de audio
  - [ ] Antes de enviar a whisper, comprimir si >20MB
  - [ ] Usar opus o mp3 con bitrate reducido
  - [ ] Verificar que calidad sigue siendo aceptable
  
- [ ] **5.3.4** Graceful shutdown
  - [ ] Capturar SIGTERM y SIGINT
  - [ ] Terminar job actual
  - [ ] Guardar estado de jobs incompletos
  - [ ] Liberar lock
  - [ ] Cerrar conexiones

**Archivos:** Modificar `src/worker.py`, `src/database.py`  
**Dependencias:** Fases 1-3  
**Tiempo estimado:** 3 horas  
**Agente Asignado:** @python-coder

---

## Tarea 5.4: Documentación

**Objetivo:** Guías completas

- [ ] **5.4.1** Actualizar `README.md`
  - [ ] Instalación paso a paso
  - [ ] Configuración de .env
  - [ ] Uso básico (CLI)
  - [ ] Configuración de bots
  - [ ] Troubleshooting común
  
- [ ] **5.4.2** Crear `docs/INSTALL.md`
  - [ ] Requisitos del sistema
  - [ ] Instalación de Docker
  - [ ] Instalación de Python y dependencias
  - [ ] Configuración de cron
  
- [ ] **5.4.3** Crear `docs/API.md`
  - [ ] Documentar clases principales
  - [ ] Ejemplos de uso
  - [ ] Diagrama de arquitectura
  
- [ ] **5.4.4** Actualizar `AGENTS.md`
  - [ ] Nueva estructura de carpetas
  - [ ] Comandos actualizados
  - [ ] Convenciones de código
  
- [ ] **5.4.5** Crear `docs/TROUBLESHOOTING.md`
  - [ ] Servidor whisper no responde
  - [ ] Archivos stuck en processing
  - [ ] Rate limiting excedido
  - [ ] Docker issues
  - [ ] Cómo leer logs

**Archivos:** `README.md`, `docs/*.md`  
**Dependencias:** Todas las anteriores  
**Tiempo estimado:** 3 horas  
**Agente Asignado:** @data-engineer

---

## Agentes Asignados

| Tarea | Agente | Justificación |
|-------|--------|---------------|
| 5.1 Tests Unitarios | **@tdd-architect** + **@python-coder** | Diseño TDD + implementación |
| 5.2 Tests Integración | **@tdd-architect** | E2E, mocks |
| 5.3 Optimizaciones | **@python-coder** | Cache, batch processing |
| 5.4 Documentación | **@data-engineer** | Arquitectura, guías |

---

## Flujo de Testing Recomendado

```
1. @tdd-architect → Diseñar tests (pre-implementación)
2. @python-coder → Implementar código para pasar tests
3. @code-reviewer → Revisar implementación y tests
4. Ejecutar: pytest tests/ -v --cov=src
5. Meta: >80% cobertura
```

---

[Volver al índice](../tasks.md)
