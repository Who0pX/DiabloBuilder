# 🚀 Guía de Instalación Completa

## Tabla de Contenidos
1. [Requisitos Previos](#requisitos-previos)
2. [Crear el Bot en Discord](#crear-el-bot-en-discord)
3. [Configurar Intents](#configurar-intents)
4. [Instalar Dependencias](#instalar-dependencias)
5. [Configurar el Bot](#configurar-el-bot)
6. [Invitar el Bot a tu Servidor](#invitar-el-bot-a-tu-servidor)
7. [Ejecutar el Bot](#ejecutar-el-bot)
8. [Desplegar la Infraestructura](#desplegar-la-infraestructura)
9. [Verificar Instalación](#verificar-instalación)
10. [Troubleshooting](#troubleshooting)

---

## Requisitos Previos

### Sistema Operativo
- Windows 10/11
- macOS 10.15+
- Linux (Ubuntu 20.04+, Debian 10+, etc.)

### Software Requerido
- **Python 3.10 o superior**
  - Windows: Descarga de [python.org](https://www.python.org/downloads/)
  - macOS: `brew install python3`
  - Linux: `sudo apt install python3 python3-pip`

- **pip** (gestor de paquetes de Python)
  - Incluido con Python 3.10+

### Verificar Instalación de Python
```bash
python3 --version  # Debe mostrar 3.10 o superior
pip3 --version     # Debe mostrar versión de pip
```

---

## Crear el Bot en Discord

### Paso 1: Acceder al Portal de Desarrolladores
1. Ve a https://discord.com/developers/applications
2. Inicia sesión con tu cuenta de Discord
3. Haz clic en **"New Application"**
4. Ingresa un nombre para tu bot (ej: "Security Bot")
5. Acepta los términos y haz clic en **"Create"**

### Paso 2: Crear el Bot
1. En el menú lateral, selecciona **"Bot"**
2. Haz clic en **"Add Bot"**
3. Confirma haciendo clic en **"Yes, do it!"**
4. Tu bot ha sido creado exitosamente

### Paso 3: Obtener el Token
1. En la sección "Bot", busca **"TOKEN"**
2. Haz clic en **"Reset Token"**
3. Confirma la acción
4. Copia el token que aparece (¡IMPORTANTE: no lo compartas!)
5. Guárdalo en un lugar seguro

⚠️ **NUNCA compartas tu token con nadie. Es como una contraseña.**

---

## Configurar Intents

Los intents son permisos que el bot necesita para acceder a cierta información.

### Habilitar Intents Necesarios
1. En el portal de desarrolladores, ve a **"Bot"**
2. Desplázate hasta **"Privileged Gateway Intents"**
3. Habilita los siguientes intents:
   - ✅ **PRESENCE INTENT**
   - ✅ **SERVER MEMBERS INTENT**
   - ✅ **MESSAGE CONTENT INTENT**
4. Haz clic en **"Save Changes"**

### ¿Por qué necesitamos estos intents?
- **Presence**: Para ver el estado de los usuarios
- **Server Members**: Para eventos de join/leave y gestión de miembros
- **Message Content**: Para filtrar mensajes y auto-moderación

---

## Instalar Dependencias

### Opción 1: Usar requirements.txt (Recomendado)
```bash
# Navega al directorio del bot
cd /ruta/al/bot

# Instala las dependencias
pip3 install -r requirements.txt --break-system-packages
```

### Opción 2: Instalación Manual
```bash
pip3 install "discord.py>=2.3.0" --break-system-packages
```

### Verificar Instalación
```bash
python3 -c "import discord; print(discord.__version__)"
```
Debe mostrar una versión 2.3.0 o superior.

---

## Configurar el Bot

### Método 1: Variable de Entorno (Recomendado)

#### En Linux/macOS:
```bash
# Temporal (solo sesión actual)
export DISCORD_BOT_TOKEN="tu_token_aquí"

# Permanente (agrega a ~/.bashrc o ~/.zshrc)
echo 'export DISCORD_BOT_TOKEN="tu_token_aquí"' >> ~/.bashrc
source ~/.bashrc
```

#### En Windows (CMD):
```cmd
set DISCORD_BOT_TOKEN=tu_token_aquí
```

#### En Windows (PowerShell):
```powershell
$env:DISCORD_BOT_TOKEN="tu_token_aquí"

# Permanente
[Environment]::SetEnvironmentVariable("DISCORD_BOT_TOKEN", "tu_token_aquí", "User")
```

### Método 2: Archivo .env

1. Copia `.env.example` a `.env`:
```bash
cp .env.example .env
```

2. Edita `.env` y pega tu token:
```bash
DISCORD_BOT_TOKEN=tu_token_aquí
```

### Método 3: Directamente en el Código (NO Recomendado)

Edita `advanced_discord_bot.py` línea 16:
```python
DISCORD_TOKEN: str = "tu_token_aquí"
```

⚠️ **ADVERTENCIA**: No hagas commit de archivos con tokens a repositorios públicos.

---

## Invitar el Bot a tu Servidor

### Paso 1: Generar Link de Invitación
1. Ve al portal de desarrolladores
2. Selecciona tu aplicación
3. Ve a **"OAuth2"** → **"URL Generator"**
4. En **"SCOPES"**, selecciona:
   - ✅ `bot`
   - ✅ `applications.commands`
5. En **"BOT PERMISSIONS"**, selecciona:
   - ✅ **Administrator** (más fácil)
   
   O selecciona permisos específicos:
   - ✅ Manage Roles
   - ✅ Manage Channels
   - ✅ Kick Members
   - ✅ Ban Members
   - ✅ Manage Messages
   - ✅ Read Messages/View Channels
   - ✅ Send Messages
   - ✅ Manage Webhooks
   - ✅ Read Message History
   - ✅ Add Reactions
   - ✅ Use Slash Commands
   - ✅ Manage Guild
   - ✅ View Audit Log
   - ✅ Moderate Members

6. Copia la URL generada

### Paso 2: Invitar el Bot
1. Pega la URL en tu navegador
2. Selecciona el servidor donde quieres agregar el bot
3. Haz clic en **"Authorize"**
4. Completa el captcha
5. ¡Bot agregado exitosamente!

### Verificar que el Bot está en el Servidor
- El bot debe aparecer en la lista de miembros (sin conexión hasta que lo ejecutes)
- Debe tener el rol con los permisos que configuraste

---

## Ejecutar el Bot

### Ejecución Básica
```bash
python3 advanced_discord_bot.py
```

### Ejecución en Segundo Plano (Linux/macOS)
```bash
# Con nohup
nohup python3 advanced_discord_bot.py > bot.log 2>&1 &

# Con screen
screen -S discord-bot
python3 advanced_discord_bot.py
# Presiona Ctrl+A, luego D para detach

# Con tmux
tmux new -s discord-bot
python3 advanced_discord_bot.py
# Presiona Ctrl+B, luego D para detach
```

### Ejecución como Servicio (Linux Systemd)

1. Crea el archivo de servicio:
```bash
sudo nano /etc/systemd/system/discord-bot.service
```

2. Pega esta configuración (ajusta las rutas):
```ini
[Unit]
Description=Advanced Discord Bot
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/al/bot
Environment="DISCORD_BOT_TOKEN=tu_token"
ExecStart=/usr/bin/python3 /ruta/al/bot/advanced_discord_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Habilita y ejecuta el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable discord-bot
sudo systemctl start discord-bot
```

4. Ver logs:
```bash
sudo journalctl -u discord-bot -f
```

### Verificar que el Bot está Online
Debes ver en los logs:
```
[2025-01-28 10:30:47.456] [INFO] [infra.bot] Ready: BotName (ID: 123456789)
[2025-01-28 10:30:47.457] [INFO] [infra.bot] Guilds: 1
```

En Discord, el bot debe aparecer **ONLINE** (punto verde).

---

## Desplegar la Infraestructura

### Paso 1: Ejecutar el Comando Deploy
1. En tu servidor de Discord, escribe:
```
/deploy
```

2. El bot responderá con un mensaje efímero confirmando el inicio

### Paso 2: Monitorear el Progreso
El bot creará un canal temporal `deployment-progress` donde verás:
- **Phase 1**: Purge (eliminación de estructura existente)
- **Phase 2**: Role Hierarchy (creación de roles)
- **Phase 3**: Channel Infrastructure (canales y webhooks)
- **Phase 4**: Auto-Moderation (reglas de AutoMod)

### Paso 3: Verificar Completado
Al finalizar:
- El canal `deployment-progress` se eliminará
- Se creará `deployment-complete` con el resumen completo
- Verás estadísticas como:
  - Roles creados: 11
  - Categorías: 8
  - Canales: 35+
  - Webhooks: 5
  - AutoMod Rules: 4
  - Duración: ~30-60 segundos

### ¿Qué se Creó?

**Roles:**
- Server Owner, Co-Owner, Head Admin
- Admin, Senior Mod, Moderator, Helper
- Verified, Member, Unverified, Bots

**Categorías y Canales:**
- SERVER INFO: rules, verify, welcome, announcements, updates, roles
- GENERAL: general, casual, media, questions
- OSINT OPERATIONS: osint-general, tools-resources, geoint, socmint, investigations
- ANALYSIS & REPORTS: threat-intel, reports, data-analysis
- VOICE CHANNELS: general-voice, meeting-room, study-room
- BOT COMMANDS: bot-commands, bot-spam
- STAFF AREA: staff-chat, staff-voice
- ADMINISTRATION: admin-chat, 7 canales de logs

**AutoMod Rules:**
1. Block Discord Invites
2. Block Scam Links
3. Block Mass Mentions
4. Profanity Filter

---

## Verificar Instalación

### Comando de Verificación
```
/verify
```

Este comando te mostrará:
- ✅ Estado de roles (11 esperados, 11 encontrados)
- ✅ Estado de categorías (8 esperadas, 8 encontradas)
- ✅ Estado de canales (35+ esperados, 35+ encontrados)
- ✅ AutoMod Rules: 4
- ✅ Lockdown: INACTIVE
- ✅ Pending Verifications: 0

**Health Status:**
- `[PERFECT]`: Todo funcionando correctamente
- `[MINOR ISSUES]`: Algunos componentes faltantes
- `[CRITICAL]`: Muchos componentes faltantes, redeploy recomendado

### Verificaciones Manuales

#### 1. Verificar Roles
- Ve a Configuración del Servidor → Roles
- Debe haber 11 roles (+ @everyone)
- Orden correcto (Server Owner en la cima)

#### 2. Verificar Canales
- Cuenta las categorías: debe haber 8
- Cuenta los canales: debe haber 35+
- Verifica que los permisos estén correctos

#### 3. Verificar AutoMod
- Ve a Configuración del Servidor → AutoMod
- Debe haber 4 reglas activas:
  - Block Discord Invites
  - Block Scam Links
  - Block Mass Mentions
  - Profanity Filter

#### 4. Verificar Webhooks
- Ve a Configuración del Servidor → Integraciones → Webhooks
- Debe haber 5 webhooks para logs

#### 5. Probar Verificación
1. Crea una cuenta de prueba o pide a alguien que se una
2. El usuario debe recibir rol "Unverified"
3. Mensaje de bienvenida en #welcome
4. Al reaccionar con ✅ en #verify:
   - Pierde rol "Unverified"
   - Recibe rol "Member"
   - Log en member-logs

#### 6. Probar Auto-Moderación
Intenta (con cuenta de prueba):
- Enviar un discord.gg/xxxxx → Debe ser bloqueado
- Enviar un link de scam → Debe ser bloqueado + timeout
- @mention 6+ personas → Debe ser bloqueado + timeout
- Enviar profanidad → Debe ser bloqueado

#### 7. Probar Logging
- Edita un mensaje → Debe aparecer en message-logs
- Elimina un mensaje → Debe aparecer en message-logs
- Únete/sal de voz → Debe aparecer en voice-logs

---

## Troubleshooting

### El bot no se conecta

**Error:** `LoginFailure: Improper token has been passed`

**Solución:**
1. Verifica que el token es correcto
2. Asegúrate de no tener espacios antes/después del token
3. El token debe tener ~70 caracteres
4. Regenera el token si es necesario

---

**Error:** `Privileged intent provided is not enabled or whitelisted`

**Solución:**
1. Ve al portal de desarrolladores
2. Bot → Privileged Gateway Intents
3. Habilita los 3 intents mencionados
4. Reinicia el bot

---

### Los comandos no aparecen

**Problema:** Los slash commands no se ven en Discord

**Solución:**
1. Espera 5-10 minutos (pueden tardar en sincronizarse)
2. Verifica en los logs: `Synced X commands globally`
3. Si no aparecen, reinicia el bot
4. Verifica que invitaste el bot con el scope `applications.commands`
5. Reinstala el bot si es necesario

---

### AutoMod no funciona

**Problema:** Las reglas de AutoMod no se aplican

**Soluciones posibles:**

1. **Verificar Server Boost Level:**
   - Algunas reglas requieren nivel 2+ de boost
   - Si no tienes boost, algunas reglas pueden fallar

2. **Verificar Permisos:**
   - El bot necesita "Manage Guild" permission
   - Verifica en Configuración → Roles → Bot Role

3. **Conflictos con otras reglas:**
   - Si tienes otras reglas de AutoMod, pueden conflictuar
   - Intenta deshabilitarlas temporalmente

4. **Redeploy:**
   ```
   /deploy
   ```

---

### Logs no aparecen

**Problema:** No se registran eventos en los canales de logs

**Solución:**
1. Verifica que los webhooks existen:
   ```
   /verify
   ```
2. Verifica permisos del bot en canales de logs
3. Reinicia el bot
4. Si persiste, ejecuta `/deploy` nuevamente

---

### Spam detection muy agresiva/permisiva

**Problema:** El bot banea usuarios legítimos o no detecta spam

**Solución:**
Ajusta las configuraciones en `advanced_discord_bot.py`:

```python
class Config:
    # Hacer MENOS agresivo (más mensajes permitidos)
    SPAM_MESSAGE_THRESHOLD = 10  # Era 5
    SPAM_TIME_WINDOW = 10        # Era 5
    
    # Hacer MÁS agresivo (menos mensajes permitidos)
    SPAM_MESSAGE_THRESHOLD = 3   # Era 5
    SPAM_TIME_WINDOW = 3         # Era 5
```

Reinicia el bot después de los cambios.

---

### Raid detection falsos positivos

**Problema:** El bot activa lockdown cuando no hay raid

**Solución:**
Ajusta la sensibilidad:

```python
class Config:
    # Menos sensible (requiere más joins)
    RAID_JOIN_THRESHOLD = 20     # Era 10
    RAID_JOIN_WINDOW = 15        # Era 10
    
    # Más sensible (requiere menos joins)
    RAID_JOIN_THRESHOLD = 5      # Era 10
    RAID_JOIN_WINDOW = 5         # Era 10
```

---

### Usuario no puede verificarse

**Problema:** El usuario reacciona con ✅ pero nada pasa

**Solución:**
1. Verifica que el emoji es exactamente ✅ (checkmark verde)
2. Verifica que el canal es #verify
3. Verifica que el bot tiene permisos para:
   - Manage Roles
   - Read Message History
4. Verifica que los roles "Unverified" y "Member" existen
5. Verifica que el rol del bot está por encima de "Unverified" y "Member"

---

### El bot se desconecta constantemente

**Problema:** El bot se cae o reinicia frecuentemente

**Posibles causas:**

1. **Conexión inestable:**
   - Verifica tu conexión a internet
   - Usa un VPS o servidor dedicado

2. **Errores no manejados:**
   - Revisa los logs para ver el error específico
   - Reporta bugs encontrados

3. **Rate limiting:**
   - El bot hace demasiadas requests
   - Ya tiene protección, pero verifica logs

4. **Memoria insuficiente:**
   - El bot necesita ~100-200MB RAM
   - Verifica con `htop` o `top`

---

### Mensajes duplicados en logs

**Problema:** Los eventos se registran múltiples veces

**Solución:**
1. Verifica que solo hay una instancia del bot corriendo:
   ```bash
   ps aux | grep advanced_discord_bot.py
   ```
2. Mata instancias duplicadas:
   ```bash
   pkill -f advanced_discord_bot.py
   ```
3. Inicia solo una instancia

---

### No puedo ejecutar /deploy

**Problema:** El comando da error de permisos

**Solución:**
1. Verifica que tienes el permiso de Administrator en Discord
2. Verifica que el bot tiene el permiso de Administrator
3. Verifica que el rol del bot está por encima de todos los demás
4. Intenta kick y re-invitar el bot con permisos correctos

---

## Comandos Útiles

### Verificar estado del servicio (Linux)
```bash
sudo systemctl status discord-bot
```

### Ver logs en tiempo real
```bash
# Si usaste systemd
sudo journalctl -u discord-bot -f

# Si usaste nohup
tail -f bot.log

# Si usaste screen
screen -r discord-bot

# Si usaste tmux
tmux attach -t discord-bot
```

### Reiniciar el bot
```bash
# Si usaste systemd
sudo systemctl restart discord-bot

# Si ejecutaste manualmente
# Ctrl+C en la terminal donde corre
# Luego ejecuta nuevamente
python3 advanced_discord_bot.py
```

### Detener el bot
```bash
# Si usaste systemd
sudo systemctl stop discord-bot

# Si usaste screen
screen -r discord-bot
# Luego Ctrl+C

# Si usaste tmux
tmux attach -t discord-bot
# Luego Ctrl+C

# Si usaste nohup
pkill -f advanced_discord_bot.py
```

---

## Mantenimiento

### Actualizar el Bot
```bash
# Detener el bot
sudo systemctl stop discord-bot  # O Ctrl+C

# Backup del archivo actual
cp advanced_discord_bot.py advanced_discord_bot.py.backup

# Reemplazar con nueva versión
# (copia el nuevo archivo)

# Reiniciar
sudo systemctl start discord-bot  # O python3 advanced_discord_bot.py
```

### Backup de Configuración
```bash
# Crear backup
tar -czf discord-bot-backup-$(date +%Y%m%d).tar.gz \
  advanced_discord_bot.py \
  .env \
  requirements.txt \
  README.md

# Restaurar backup
tar -xzf discord-bot-backup-20250128.tar.gz
```

### Logs de Auditoría
El bot guarda automáticamente logs en:
- Console output (stdout)
- Security logs en Discord
- Mod logs en Discord
- Audit log en Discord

Para logs persistentes del sistema, redirige stdout:
```bash
python3 advanced_discord_bot.py >> bot.log 2>&1
```

---

## Recursos Adicionales

### Enlaces Útiles
- [Discord Developer Portal](https://discord.com/developers/applications)
- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [Discord API Documentation](https://discord.com/developers/docs/)
- [Discord AutoMod Guide](https://support.discord.com/hc/en-us/articles/4421269296535)

### Comunidades
- [discord.py Server](https://discord.gg/dpy)
- [Discord Developers](https://discord.gg/discord-developers)

---

## Próximos Pasos

Una vez instalado exitosamente:

1. **Personaliza el Bot:**
   - Ajusta los mensajes de bienvenida
   - Modifica las reglas
   - Ajusta las configuraciones de seguridad

2. **Asigna Roles:**
   - Da roles de staff a tus moderadores
   - Configura permisos específicos

3. **Prueba Todas las Funciones:**
   - Sistema de verificación
   - Auto-moderación
   - Comandos de moderación
   - Sistema de logs

4. **Monitorea:**
   - Revisa los logs regularmente
   - Ajusta configuraciones según necesites
   - Reporta bugs o problemas

---

¡Felicidades! Tu servidor ahora tiene un sistema completo de seguridad y moderación. 🎉
