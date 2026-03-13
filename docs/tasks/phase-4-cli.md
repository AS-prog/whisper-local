# Fase 4: CLI y Tooling

**Objetivo:** Implementar interfaz de línea de comandos y herramientas de observabilidad

**Tiempo Estimado:** 7 horas
**Dependencias:** Fase 3 completada

---

## Tarea 4.1: CLI

**Objetivo:** Interfaz de línea de comandos

- [ ] **4.1.1** Configurar dependencias
  - [ ] Añadir `click` o `typer` a requirements.txt
  - [ ] Instalar dependencia elegida
  
- [ ] **4.1.2** Crear `cli.py`
  ```python
  import click
  
  @click.group()
  def cli():
      pass
  
  @cli.command()
  @click.option('--enqueue-only', is_flag=True)
  @click.argument('files', nargs=-1)
  def process(files, enqueue_only):
      pass
  
  @cli.command()
  def status():
      pass
  
  @cli.command()
  def config():
      pass
  
  @cli.command()
  @click.option('--start/--stop', default=True)
  def worker(start):
      pass
  
  if __name__ == '__main__':
      cli()
  ```
  
- [ ] **4.1.3** Implementar `process`
  - [ ] Sin argumentos: procesar pending/
  - [ ] Con archivos: encolar archivos específicos
  - [ ] `--enqueue-only`: solo encolar, no procesar
  
- [ ] **4.1.4** Implementar `status`
  - [ ] Mostrar tabla: Queue | Pending | Processing | Completed
  - [ ] Mostrar últimos 10 jobs
  - [ ] Mostrar métricas del día
  
- [ ] **4.1.5** Implementar `config`
  - [ ] `config init`: Crear .env desde .env.example
  - [ ] `config show`: Mostrar configuración actual (sin tokens)
  - [ ] `config validate`: Verificar que todo esté configurado
  
- [ ] **4.1.6** Implementar `worker`
  - [ ] `worker --start`: Ejecutar `scripts/worker.sh`
  - [ ] `worker --stop`: Ejecutar `scripts/stop-worker.sh`
  - [ ] `worker --status`: Verificar si está corriendo

**Archivos:** `src/cli.py`  
**Dependencias:** Todas las anteriores  
**Tiempo estimado:** 3 horas  
**Agente Asignado:** @python-coder

---

## Tarea 4.2: Logging y Métricas

**Objetivo:** Observabilidad del sistema

- [ ] **4.2.1** Configurar logging
  - [ ] Crear `logger.py` con configuración JSON
  - [ ] Logs estructurados: timestamp, level, component, message
  - [ ] Rotación de logs: 10MB por archivo, máximo 5 archivos
  - [ ] Niveles: DEBUG (dev), INFO (prod), ERROR (siempre)
  
- [ ] **4.2.2** Añadir métricas
  - [ ] Tiempo promedio de procesamiento
  - [ ] Tasa de éxito/fallo
  - [ ] Archivos procesados por día
  - [ ] Uso de cache (hits/misses)
  
- [ ] **4.2.3** Exportar métricas
  - [ ] Comando: `whisper-local metrics --days 7 --format csv`
  - [ ] Formato: CSV o JSON
  - [ ] Incluir: fecha, métrica, valor

**Archivos:** `src/logger.py`, modificar `src/database.py`  
**Dependencias:** 1.1  
**Tiempo estimado:** 2 horas  
**Agente Asignado:** @python-coder

---

## Tarea 4.3: Utilidades de Mantenimiento

**Objetivo:** Herramientas de administración

- [ ] **4.3.1** Comando `cleanup`
  - [ ] `cleanup cache --days 30`: Borrar cache antiguo
  - [ ] `cleanup logs --days 7`: Archivar logs antiguos
  - [ ] `cleanup processing`: Resetear archivos stuck
  
- [ ] **4.3.2** Comando `retry`
  - [ ] `retry --failed`: Reencolar todos los failed
  - [ ] `retry --job-id ID`: Reencolar job específico
  
- [ ] **4.3.3** Comando `stats`
  - [ ] `stats --today`: Resumen del día
  - [ ] `stats --week`: Resumen de la semana
  - [ ] Mostrar: procesados, fallidos, tiempo promedio, usuarios activos

**Archivos:** `src/cli.py`  
**Dependencias:** 4.1  
**Tiempo estimado:** 2 horas  
**Agente Asignado:** @python-coder

---

## Agentes Asignados

| Tarea | Agente | Justificación |
|-------|--------|---------------|
| 4.1 CLI | **@python-coder** | Click/Typer, interfaz de usuario |
| 4.2 Logging | **@python-coder** | JSON logging, rotación, métricas |
| 4.3 Utilidades | **@python-coder** | Comandos de mantenimiento |

---

[Volver al índice](../tasks.md)
