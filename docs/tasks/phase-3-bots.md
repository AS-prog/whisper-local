# Fase 3: Bots con Progreso

**Objetivo:** Implementar bots de Telegram y Discord con notificaciones de progreso

**Tiempo Estimado:** 10 horas
**Dependencias:** Fase 2 completada

---

## Tarea 3.1: Bot Telegram

**Objetivo:** Bot asíncrono con notificaciones

- [ ] **3.1.1** Configurar dependencias
  - [ ] Añadir `python-telegram-bot>=20.0` a requirements.txt
  - [ ] Instalar: `pip install python-telegram-bot`
  
- [ ] **3.1.2** Crear clase `TelegramBot`
  ```python
  class TelegramBot:
      def __init__(self, token: str, job_queue: JobQueue,
                   database: Database)
      async def start(self)
      async def stop(self)
      async def handle_voice(self, update: Update, 
                            context: ContextTypes.DEFAULT_TYPE)
      async def handle_status(self, update: Update,
                             context: ContextTypes.DEFAULT_TYPE)
      async def handle_transcribe(self, update: Update,
                                 context: ContextTypes.DEFAULT_TYPE)
      async def send_progress(self, chat_id: int, job_id: int,
                             progress: int)
  ```
  
- [ ] **3.1.3** Implementar comandos
  - [ ] `/start`: Mensaje de bienvenida + instrucciones
  - [ ] `/status`: Muestra colas y jobs del usuario
  - [ ] `/transcribe`: Fuerza procesamiento inmediato
  
- [ ] **3.1.4** Implementar manejo de notas de voz
  - [ ] Descargar archivo con `update.message.voice.get_file()`
  - [ ] Guardar en `inputs/pending/`
  - [ ] Verificar rate limit
  - [ ] Crear job en cola
  - [ ] Responder: "Archivo recibido. Posición en cola: X"
  
- [ ] **3.1.5** Implementar notificaciones de progreso
  - [ ] Registrar callback en JobQueue
  - [ ] Cuando progreso cambia:
    - [ ] Si 0%: "Procesando..."
    - [ ] Si cada 10%: Editar mensaje con "Progreso: X%"
    - [ ] Si 100%: "Completado!" + enviar transcripción
  - [ ] Manejar mensajes largos (>4096 caracteres)
    - [ ] Dividir en múltiples mensajes
    - [ ] O enviar como archivo
  
- [ ] **3.1.6** Implementar rate limiting
  - [ ] Antes de crear job: verificar rate limit
  - [ ] Si excedido: "Límite de 5 archivos/hora alcanzado"
  - [ ] Reset automático cada hora

**Archivos:** `src/telegram_bot.py`  
**Dependencias:** 1.2  
**Tiempo estimado:** 4 horas  
**Agente Asignado:** @python-coder

---

## Tarea 3.2: Bot Discord

**Objetivo:** Bot asíncrono con embeds

- [ ] **3.2.1** Configurar dependencias
  - [ ] Añadir `discord.py>=2.0` a requirements.txt
  - [ ] Instalar: `pip install discord.py`
  
- [ ] **3.2.2** Crear clase `DiscordBot`
  ```python
  class DiscordBot(discord.Client):
      def __init__(self, token: str, job_queue: JobQueue,
                   database: Database)
      async def on_ready(self)
      async def on_message(self, message: discord.Message)
      async def handle_attachment(self, message: discord.Message)
      async def handle_voice(self, message: discord.Message)
      async def slash_status(self, interaction: discord.Interaction)
      async def slash_transcribe(self, interaction: discord.Interaction)
      async def send_progress_embed(self, channel_id: int,
                                   job_id: int, progress: int)
  ```
  
- [ ] **3.2.3** Implementar listeners
  - [ ] `on_ready()`: Loguear conexión exitosa
  - [ ] `on_message()`:
    - [ ] Ignorar mensajes de bots
    - [ ] Si tiene attachments: procesar
    - [ ] Si es mensaje de voz: procesar
    
- [ ] **3.2.4** Implementar comandos slash
  - [ ] `/status`: Embed con estado de colas
  - [ ] `/transcribe`: Embed para forzar procesamiento
  - [ ] Registrar comandos en `setup_hook()`
  
- [ ] **3.2.5** Implementar manejo de archivos
  - [ ] Descargar attachment con `attachment.save()`
  - [ ] Validar formato de audio
  - [ ] Guardar en pending/
  - [ ] Crear job
  
- [ ] **3.2.6** Implementar notificaciones
  - [ ] Crear embed con barra de progreso
  - [ ] Editar embed cada 10%
  - [ ] Color del embed: azul (procesando), verde (completado), rojo (error)
  - [ ] Enviar transcripción como mensaje separado o archivo
  
- [ ] **3.2.7** Implementar rate limiting global
  - [ ] Semáforo: máximo 10 jobs simultáneos
  - [ ] Cola de espera si se excede

**Archivos:** `src/discord_bot.py`  
**Dependencias:** 1.2  
**Tiempo estimado:** 4 horas  
**Agente Asignado:** @python-coder

---

## Tarea 3.3: Integración de Progreso

**Objetivo:** Sistema unificado de notificaciones

- [ ] **3.3.1** Crear `ProgressNotifier`
  ```python
  class ProgressNotifier:
      def __init__(self, database: Database)
      def register_job(self, job_id: int, platform: str,
                      user_id: str, message_id: str = None)
      def update_progress(self, job_id: int, progress: int)
      def notify_completion(self, job_id: int, 
                           transcription: str)
      def notify_error(self, job_id: int, error: str)
  ```
  
- [ ] **3.3.2** Integrar con JobQueue
  - [ ] Cuando job cambia a processing: notificar inicio
  - [ ] Cuando progreso se actualiza: notificar
  - [ ] Cuando job completa: notificar resultado
  
- [ ] **3.3.3** Manejo de mensajes largos
  - [ ] Telegram: dividir en chunks de 4096 caracteres
  - [ ] Discord: dividir en chunks de 2000 caracteres
  - [ ] Opción: enviar como archivo .txt si >10 chunks

**Archivos:** `src/progress_notifier.py`  
**Dependencias:** 3.1, 3.2  
**Tiempo estimado:** 2 horas  
**Agente Asignado:** @python-coder

---

## Agentes Asignados

| Tarea | Agente | Justificación |
|-------|--------|---------------|
| 3.1 Bot Telegram | **@python-coder** | Async bots, python-telegram-bot |
| 3.2 Bot Discord | **@python-coder** | discord.py, embeds, slash commands |
| 3.3 Progress Notifier | **@python-coder** | Sistema unificado de notificaciones |

---

[Volver al índice](../tasks.md)
