# Advanced Discord Infrastructure & Security Bot

Bot público completo para Discord que configura y gestiona TODO un servidor de forma profesional con sistemas avanzados de seguridad, auto-moderación, y protecciones contra ataques.

## 🚀 Características Principales

### Infraestructura Completa
- **Deployment Automatizado**: Configura todo el servidor con un solo comando
- **11 Roles Jerárquicos**: Desde Server Owner hasta Unverified
- **8 Categorías Organizadas**: Info, General, OSINT, Análisis, Voice, Bot Commands, Staff, Admin
- **35+ Canales**: Completo sistema de canales incluyendo logs especializados
- **Webhooks Automáticos**: Para logging avanzado en tiempo real

### Sistema de Seguridad Avanzado

#### Anti-Raid Protection
- Detección automática de raids (10+ joins en 10 segundos)
- Lockdown automático del servidor
- Verificación de edad de cuentas (mínimo 7 días)
- Detección de cuentas sospechosas (sin avatar, muy nuevas)

#### Anti-Spam System
- Límite de 5 mensajes en 5 segundos
- Timeout automático por spam
- Sistema de warnings (3 strikes)
- Detección de flood de líneas y mensajes largos

#### Content Filtering
- **Bloqueador de invites**: Discord invite links automáticamente bloqueados
- **Scam Protection**: 13+ dominios de scam conocidos bloqueados
- **Profanity Filter**: Lista configurable de palabras prohibidas
- **Zalgo Text Detection**: Bloquea texto corrupto/zalgo
- **Excessive Caps**: Límite de 70% de mayúsculas
- **Emoji Spam**: Máximo 15 emojis por mensaje
- **Mass Mentions**: Máximo 5 menciones por mensaje

### Auto-Moderación de Discord

4 reglas de AutoMod configuradas automáticamente:
1. **Block Discord Invites**: Regex patterns para invites
2. **Block Scam Links**: Dominios de phishing/scam con timeout
3. **Block Mass Mentions**: Límite de menciones con block + timeout
4. **Profanity Filter**: Filtro de profanidad con alertas

### Sistema de Verificación

- Canal dedicado de verificación
- Reacción con ✅ para verificar
- Timeout de 60 minutos para verificar
- Kick automático si no verifica
- Rol "Unverified" asignado automáticamente
- Acceso limitado hasta verificar

### Sistema de Logging Completo

**6 Canales de Logs Especializados** con webhooks:
1. **audit-log**: Log general de todas las acciones
2. **message-logs**: Ediciones y eliminaciones de mensajes
3. **member-logs**: Joins, leaves, bans, unbans
4. **mod-logs**: Acciones de moderación (warns, timeouts, bans)
5. **security-logs**: Eventos de seguridad y raids
6. **voice-logs**: Actividad en canales de voz
7. **automod-logs**: Triggers de auto-moderación

### Sistema de Warnings

- Comando `/warn` para moderadores
- Sistema de 3 strikes
- Timeout automático al 3er warning
- DMs automáticos al usuario
- Log completo de todas las advertencias
- Reset de warnings después del timeout

### Monitoreo en Tiempo Real

**Background Tasks:**
- Limpieza de usuarios no verificados cada 5 minutos
- Monitor de seguridad cada 30 segundos
- Detección de raids en tiempo real
- Tracking de usuarios sospechosos

## 📋 Comandos

### Comandos de Administración

#### `/deploy`
Deployment completo del servidor. Ejecuta 4 fases:
1. **Purge**: Elimina todo (canales, categorías, roles, AutoMod)
2. **Roles**: Crea jerarquía de 11 roles
3. **Infrastructure**: Crea 8 categorías, 35+ canales, 5 webhooks
4. **AutoMod**: Configura 4 reglas de auto-moderación

**Requiere:** Administrator permission

#### `/verify`
Health check completo del servidor:
- Estado de roles (missing/extra)
- Estado de categorías
- Estado de canales
- Reglas de AutoMod activas
- Estado de lockdown
- Verificaciones pendientes
- Latencia del bot

**Requiere:** Administrator permission

#### `/lockdown <enabled: true/false>`
Activa/desactiva el modo lockdown:
- Cambia verification level a Highest
- Previene nuevos joins sospechosos
- Log en security-logs
- Notificación a administradores

**Requiere:** Administrator permission

### Comandos de Moderación

#### `/warn <user> <reason>`
Sistema de advertencias:
- Emite warning al usuario
- DM automático al usuario
- Contador de warnings (max 3)
- Timeout automático al 3er strike
- Log completo en mod-logs

**Requiere:** Moderate Members permission

## 🛡️ Configuración de Seguridad

### Configuraciones Anti-Spam
```python
SPAM_MESSAGE_THRESHOLD = 5       # Mensajes antes de considerar spam
SPAM_TIME_WINDOW = 5             # Segundos de ventana
SPAM_TIMEOUT_DURATION = 300      # Duración del timeout (segundos)
```

### Configuraciones Anti-Raid
```python
RAID_JOIN_THRESHOLD = 10         # Joins para considerar raid
RAID_JOIN_WINDOW = 10            # Segundos de ventana
RAID_ACCOUNT_AGE_MIN = 604800    # Edad mínima cuenta (7 días)
```

### Límites de Mensajes
```python
MAX_MENTIONS = 5                 # Menciones máximas
MAX_EMOJIS = 15                  # Emojis máximos
MAX_CAPS_PERCENTAGE = 70         # Porcentaje máximo de mayúsculas
MAX_MESSAGE_LENGTH = 2000        # Longitud máxima
MAX_LINES = 20                   # Líneas máximas
```

### Verificación
```python
VERIFICATION_TIMEOUT = 300       # Timeout para reaccionar (segundos)
UNVERIFIED_KICK_AFTER = 3600     # Kick si no verifica (1 hora)
```

### Sistema de Warnings
```python
MAX_WARNINGS = 3                 # Warnings antes de timeout
WARNING_MUTE_DURATION = 1800     # Duración del timeout (30 min)
```

## 🔧 Instalación y Uso

### Requisitos
```bash
pip install discord.py --break-system-packages
```

### Configuración

1. **Obtener Token del Bot:**
   - Ve a https://discord.com/developers/applications
   - Crea una nueva aplicación
   - Ve a "Bot" y crea un bot
   - Copia el token

2. **Configurar Intents:**
   En el portal de desarrolladores, habilita:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent

3. **Invitar Bot:**
   Usa este link (reemplaza CLIENT_ID):
   ```
   https://discord.com/api/oauth2/authorize?client_id=CLIENT_ID&permissions=8&scope=bot%20applications.commands
   ```

4. **Configurar Token:**
   ```python
   DISCORD_TOKEN = "tu_token_aqui"
   ```
   O usar variable de entorno:
   ```bash
   export DISCORD_BOT_TOKEN="tu_token_aqui"
   ```

5. **Ejecutar:**
   ```bash
   python advanced_discord_bot.py
   ```

### Primer Uso

1. Invita el bot a tu servidor
2. Asegúrate que el bot tenga permisos de Administrador
3. Ejecuta `/deploy` en cualquier canal
4. Espera 30-60 segundos para que complete
5. El bot creará un canal "deployment-complete" con el resumen
6. ¡Listo! Tu servidor está completamente configurado

## 📊 Estructura del Servidor

### Categorías y Canales

**SERVER INFO** (Todos)
- rules: Reglas del servidor
- verify: Verificación con ✅
- welcome: Mensajes de bienvenida
- announcements: Anuncios importantes
- updates: Updates y changelog
- roles: Info de roles

**GENERAL** (Member+)
- general: Chat principal (slowmode 5s)
- casual: Off-topic (slowmode 3s)
- media: Imágenes y videos (slowmode 10s)
- questions: Preguntas y ayuda

**OSINT OPERATIONS** (Verified+)
- osint-general: Discusión general OSINT
- tools-resources: Herramientas y recursos
- geoint: Inteligencia geoespacial
- socmint: Social media intelligence
- investigations: Colaboración en investigaciones

**ANALYSIS & REPORTS** (Verified+)
- threat-intel: Inteligencia de amenazas
- reports: Reportes de investigaciones
- data-analysis: Análisis de datos

**VOICE CHANNELS** (Member+)
- general-voice: Voz general
- meeting-room: Sala de reuniones
- study-room: Sala de estudio

**BOT COMMANDS** (Member+)
- bot-commands: Comandos de bots
- bot-spam: Testing de bots

**STAFF AREA** (Helper+)
- staff-chat: Chat privado del staff
- staff-voice: Voz del staff

**ADMINISTRATION** (Admin+)
- admin-chat: Chat de administración
- audit-log: Log de auditoría
- message-logs: Logs de mensajes
- member-logs: Logs de miembros
- mod-logs: Logs de moderación
- security-logs: Logs de seguridad
- voice-logs: Logs de voz
- automod-logs: Logs de AutoMod
- reports-inbox: Reportes de usuarios

### Jerarquía de Roles

1. **Server Owner** (Administrator)
2. **Co-Owner** (Administrator)
3. **Head Admin** (Administrator)
4. **Admin** (Mod Perms)
5. **Senior Mod** (Mod Perms)
6. **Moderator** (Mod Perms)
7. **Helper** (Mod Perms)
8. **Verified** (Base Perms)
9. **Member** (Base Perms)
10. **Unverified** (View Only)
11. **Bots** (Bot Perms)

## 🔍 Event Handlers Implementados

### Eventos de Miembros
- `on_member_join`: Welcome, verificación, anti-raid
- `on_member_remove`: Logging, cleanup
- `on_member_ban`: Logging con razón
- `on_member_unban`: Logging

### Eventos de Mensajes
- `on_message`: Filtrado completo, anti-spam, content moderation
- `on_message_delete`: Logging con contenido
- `on_message_edit`: Logging de cambios

### Eventos de Voz
- `on_voice_state_update`: Join, leave, move, mute, deafen, stream, video

### Eventos de Reacciones
- `on_raw_reaction_add`: Sistema de verificación

### Background Tasks
- `cleanup_verification`: Cada 5 minutos
- `security_monitor`: Cada 30 segundos

## ⚙️ Personalización

### Modificar Roles
Edita la tupla `ROLES`:
```python
ROLES: Final[Tuple[RoleDef, ...]] = (
    RoleDef("Nombre", 0xCOLOR, perms(), posicion),
    # ...
)
```

### Modificar Canales
Edita la tupla `CHANNELS`:
```python
CHANNELS: Final[Tuple[ChanDef, ...]] = (
    ChanDef("nombre", "CATEGORIA", "topic", "mensaje", readonly, slowmode, voice),
    # ...
)
```

### Modificar Filtros
Edita las listas:
```python
SCAM_DOMAINS: Final[Tuple[str, ...]] = (...)
PROFANITY_LIST: Final[Tuple[str, ...]] = (...)
WHITELIST_DOMAINS: Final[Tuple[str, ...]] = (...)
```

### Ajustar Configuraciones
Modifica la clase `Config`:
```python
@dataclass(frozen=True)
class Config:
    SPAM_MESSAGE_THRESHOLD = 5  # Cambiar según necesites
    # ...
```

## 🐛 Troubleshooting

### El bot no responde a comandos
- Verifica que los intents estén habilitados
- Asegúrate que el bot tenga permisos de Administrator
- Revisa los logs para errores

### AutoMod no funciona
- Las reglas de AutoMod requieren Discord nivel Server Boost 2+
- Verifica que el bot tenga "Manage Guild" permission
- Algunas reglas pueden fallar silenciosamente si hay conflictos

### Raid detection muy sensible
- Ajusta `RAID_JOIN_THRESHOLD` y `RAID_JOIN_WINDOW` en Config
- Aumenta `RAID_ACCOUNT_AGE_MIN` si hay muchos falsos positivos

### Logs no aparecen
- Verifica que los webhooks se crearon correctamente
- Revisa permisos del bot en canales de logs
- Chequea que `bot.log_channels` esté poblado

## 📝 Logs y Monitoreo

El bot usa logging profesional:
```
[2025-01-28 10:30:45.123] [INFO    ] [infra.bot] Token loaded (70 chars)
[2025-01-28 10:30:47.456] [INFO    ] [infra.bot] Ready: BotName (ID: 123456789)
[2025-01-28 10:30:47.457] [INFO    ] [infra.bot] Guilds: 5
```

Niveles de log:
- `INFO`: Operaciones normales
- `WARNING`: Eventos importantes (spam, raid)
- `ERROR`: Errores recuperables
- `CRITICAL`: Errores fatales

## 🔐 Seguridad

### Protecciones Implementadas

1. **Rate Limiting**: Exponential backoff con respeto de Discord rate limits
2. **Resilient Operations**: Reintentos automáticos con backoff
3. **Input Validation**: Validación de tokens, permisos, etc.
4. **Error Handling**: Try-catch comprehensivo en todos los eventos
5. **Privilege Checking**: Verificación de permisos en cada comando
6. **Anti-Exploit**: Protección contra exploits conocidos

### Mejores Prácticas

1. **Nunca** compartas el token del bot
2. Usa variables de entorno para el token
3. Mantén el bot actualizado
4. Revisa los logs regularmente
5. Ajusta las configuraciones según tu comunidad
6. Haz backups de las configuraciones importantes

## 📈 Estadísticas y Métricas

El bot trackea:
- Warnings por usuario
- Mensajes por usuario (últimos 10)
- Joins por tiempo (últimos 50)
- Usuarios en verificación pendiente
- Usuarios sospechosos
- Estado de lockdown

Accede con `/verify` para ver estadísticas actuales.

## 🤝 Soporte

Para reportar bugs o sugerir features, contacta al administrador del servidor.

## 📜 Licencia

Código proporcionado como está. Úsalo bajo tu propia responsabilidad.

## ⚡ Performance

- **Concurrent Operations**: 10 operaciones simultáneas
- **Batch Processing**: Operaciones en lotes de 25
- **Message Cache**: 10,000 mensajes
- **Spam Detection**: O(1) lookup
- **Memory Efficient**: Deques con límites
- **Fast Startup**: <5 segundos típicamente

## 🎯 Roadmap / Futuras Mejoras

Posibles mejoras futuras:
- [ ] Sistema de tickets automatizado
- [ ] Niveles y experiencia
- [ ] Roles auto-asignables
- [ ] Comandos de música
- [ ] Sistema de economía
- [ ] Backup automático de configuración
- [ ] Dashboard web
- [ ] Integración con APIs externas
- [ ] Machine learning para detección de spam
- [ ] Soporte multi-idioma

---

**Bot creado con:** discord.py 2.x  
**Python version:** 3.10+  
**Última actualización:** 2025

**¡Disfruta de tu servidor completamente configurado y protegido!**
