# Agente: @phase1-auditor

**Tipo:** Subagente — Tester
**Modelo:** kimi-k2.5
**Ruta de configuración:** `~/.config/opencode/agents/phase1-auditor.md`

---

## Propósito

`@phase1-auditor` verifica que la implementación de Fase 1 funciona según las notas de la tarea. Su trabajo es:

1. Leer las notas (`docs/tasks/phase-1-core.md`)
2. Ejecutar el script de prueba existente (`tests/audit/cold_test_phase1.py`)
3. Reportar los resultados al orquestador

No escribe pruebas. No genera scripts. Solo replica y reporta.

---

## Módulos Verificados

| Módulo | Tarea | Comportamientos clave |
|--------|-------|-----------------------|
| `src/database.py` | §1.1 | CRUD jobs, cache hit/miss, rate limiting, métricas |
| `src/job_queue.py` | §1.2 | Orden FIFO, prioridad pending>big_files, reintentos×3 |
| `src/file_manager.py` | §1.3 | Estados pending→processing→processed, locks por PID, SHA256 |
| `src/audio_processor.py` | §1.4 | Validación de formatos, umbral 40MB, overlap 2s |

---

## Flujo de Trabajo

```
1. Lee docs/tasks/phase-1-core.md
2. Lee src/*.py  (confirma que las clases/métodos existen)
3. Ejecuta tests/audit/cold_test_phase1.py
4. Reporta resultado al orquestador
```

El agente no escribe ni modifica archivos. Solo lee, ejecuta y reporta.

---

## Script de Prueba

`tests/audit/cold_test_phase1.py` — 25+ verificaciones derivadas de las notas de la tarea.

```bash
# Ejecutar manualmente
python3 tests/audit/cold_test_phase1.py

# Exit code 0 → todo pasa
# Exit code 1 → hay fallos (ver stdout para detalle)
```

---

## Formato de Reporte

```
REPORTE DE PRUEBAS — FASE 1
════════════════════════════
Fecha: <TIMESTAMP>
Commit: <GIT_HASH>

MÓDULO              RESULTADO    DETALLE
database.py         ✅/❌        X/Y checks pasaron
job_queue.py        ✅/❌        X/Y checks pasaron
file_manager.py     ✅/❌        X/Y checks pasaron
audio_processor.py  ✅/❌        X/Y checks pasaron

VEREDICTO: LISTO PARA COMMIT / REQUIERE CORRECCIONES

FALLOS ENCONTRADOS:
  [módulo] método — observado vs. esperado según notas

SIGUIENTE PASO:
  LISTO       → @git-manager commit semántico
  CORRECCIONES → @python-coder lista de fallos
```

---

## Invocación

```
@phase1-auditor Verifica la implementación de Fase 1.
Notas: docs/tasks/phase-1-core.md
Script: tests/audit/cold_test_phase1.py
```

---

## Referencias

- Notas de la tarea: [`docs/tasks/phase-1-core.md`](../tasks/phase-1-core.md)
- Script de prueba: [`tests/audit/cold_test_phase1.py`](../../tests/audit/cold_test_phase1.py)
- Configuración: `~/.config/opencode/agents/phase1-auditor.md`
