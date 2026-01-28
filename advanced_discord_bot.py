import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import logging
import os
import sys
import re
import json
import hashlib
import random
import string
from typing import Dict, Optional, Final, Tuple, List, Set, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import IntEnum
from collections import defaultdict, deque
import traceback

DISCORD_TOKEN: str = ""

class ExitCode(IntEnum):
    SUCCESS = 0
    MISSING_TOKEN = 1
    INVALID_TOKEN = 2
    AUTH_FAILURE = 3
    FATAL_ERROR = 4

@dataclass(frozen=True)
class Config:
    TOKEN_MIN_LENGTH: Final[int] = 50
    BATCH_SIZE: Final[int] = 25
    MAX_CONCURRENT: Final[int] = 10
    BASE_DELAY: Final[float] = 0.05
    MAX_RETRIES: Final[int] = 5
    INITIAL_BACKOFF: Final[float] = 0.5
    MAX_BACKOFF: Final[float] = 30.0
    BACKOFF_MULTIPLIER: Final[float] = 2.0
    DEPLOY_TIMEOUT: Final[int] = 600
    HEALTH_CHECK_INTERVAL: Final[int] = 300
    
    # Anti-Spam Configuration
    SPAM_MESSAGE_THRESHOLD: Final[int] = 5
    SPAM_TIME_WINDOW: Final[int] = 5
    SPAM_PUNISHMENT: Final[str] = "timeout"
    SPAM_TIMEOUT_DURATION: Final[int] = 300
    
    # Anti-Raid Configuration
    RAID_JOIN_THRESHOLD: Final[int] = 10
    RAID_JOIN_WINDOW: Final[int] = 10
    RAID_ACCOUNT_AGE_MIN: Final[int] = 604800  # 7 days in seconds
    
    # Message Filtering
    MAX_MENTIONS: Final[int] = 5
    MAX_EMOJIS: Final[int] = 15
    MAX_CAPS_PERCENTAGE: Final[int] = 70
    MAX_MESSAGE_LENGTH: Final[int] = 2000
    MAX_LINES: Final[int] = 20
    
    # Link Protection
    ALLOW_LINKS_ROLES: Final[Tuple[str, ...]] = ("Verified", "Helper", "Moderator", "Senior Mod", "Admin", "Head Admin", "Co-Owner", "Server Owner")
    WHITELIST_DOMAINS: Final[Tuple[str, ...]] = ("discord.com", "discord.gg", "github.com", "youtube.com", "twitter.com", "twitch.tv")
    
    # Verification
    VERIFICATION_TIMEOUT: Final[int] = 300
    UNVERIFIED_KICK_AFTER: Final[int] = 3600
    VERIFICATION_EMOJI: Final[str] = "✅"
    
    # Warning System
    MAX_WARNINGS: Final[int] = 3
    WARNING_MUTE_DURATION: Final[int] = 1800
    
    # Auto-Moderation Rules
    BLOCK_INVITE_LINKS: Final[bool] = True
    BLOCK_SUSPICIOUS_LINKS: Final[bool] = True
    BLOCK_MASS_MENTIONS: Final[bool] = True
    BLOCK_EXCESSIVE_CAPS: Final[bool] = True
    BLOCK_SPAM: Final[bool] = True
    FILTER_PROFANITY: Final[bool] = True
    BLOCK_ZALGO: Final[bool] = True
    DETECT_MASS_EMOJIS: Final[bool] = True

def init_logger() -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '[%(asctime)s.%(msecs)03d] [%(levelname)-8s] [%(name)s] %(message)s',
        '%Y-%m-%d %H:%M:%S'
    ))
    logger = logging.getLogger('infra.bot')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger

log: Final[logging.Logger] = init_logger()

@dataclass(frozen=True)
class RoleDef:
    name: str
    color: int
    perms: discord.Permissions
    pos: int
    hoist: bool = True
    mentionable: bool = False

@dataclass(frozen=True)
class ChanDef:
    name: str
    cat: str
    topic: str = ""
    msg: str = ""
    readonly: bool = False
    slow: int = 0
    voice: bool = False

@dataclass(frozen=True)
class CatDef:
    name: str
    pos: int
    roles: Tuple[str, ...]

@dataclass
class DeploymentState:
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    progress_channel_id: Optional[int] = None
    created_roles: List[str] = field(default_factory=list)
    created_categories: List[str] = field(default_factory=list)
    created_channels: List[str] = field(default_factory=list)
    deleted_channels: int = 0
    deleted_roles: int = 0
    phase: str = "init"
    error: Optional[str] = None
    automod_rules: List[int] = field(default_factory=list)
    webhooks_created: int = 0

@dataclass
class SecurityState:
    """Track security events and user violations"""
    spam_tracker: Dict[int, deque] = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=10)))
    raid_joins: deque = field(default_factory=lambda: deque(maxlen=50))
    warning_counts: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    muted_users: Set[int] = field(default_factory=set)
    lockdown_active: bool = False
    verification_pending: Dict[int, datetime] = field(default_factory=dict)
    user_message_cache: Dict[int, List[str]] = field(default_factory=lambda: defaultdict(list))
    suspicious_users: Set[int] = field(default_factory=set)

@dataclass
class LogChannels:
    """Store log channel IDs and webhooks"""
    message_log: Optional[discord.Webhook] = None
    member_log: Optional[discord.Webhook] = None
    mod_log: Optional[discord.Webhook] = None
    security_log: Optional[discord.Webhook] = None
    voice_log: Optional[discord.Webhook] = None

RULES_TEXT: Final[str] = """**SERVER REGULATIONS**

**PROHIBITED:**
- Disclosure of PII or private information
- NSFW, violent, or illegal content
- Malicious tool usage or attacks
- Harassment or coordinated raids
- Spam, flooding, or excessive caps
- Discord invite links
- Suspicious or scam links
- Mass mentions or pings
- Alternate accounts to evade bans

**OSINT GUIDELINES:**
- Defensive research only
- Public sources exclusively
- Respect privacy boundaries
- Document methodology

**ENFORCEMENT:**
- Violations = immediate action
- 3 warnings = temporary ban
- Serious violations = permanent ban
- All actions logged

By participating, you agree to these terms."""

INVITE_PATTERNS: Final[Tuple[str, ...]] = (
    r"discord\.gg/[a-zA-Z0-9]+",
    r"discord\.com/invite/[a-zA-Z0-9]+",
    r"discordapp\.com/invite/[a-zA-Z0-9]+",
)

SCAM_DOMAINS: Final[Tuple[str, ...]] = (
    "discordgift.com", "discord-nitro.com", "steamcommuntiy.com",
    "steampovered.com", "discordapp.ru", "discord-give.com",
    "discrd.gift", "dlscord.com", "discorcl.gift", "steam-nitro.com",
    "free-discord-nitro.com", "discord-gifts.com", "steamcommunuty.com",
)

PROFANITY_LIST: Final[Tuple[str, ...]] = (
    "fuck", "shit", "bitch", "asshole", "dick", "pussy",
    "cunt", "fag", "nigger", "retard", "whore", "slut"
)

WELCOME_MESSAGE: Final[str] = """Welcome to **{server_name}**, {user_mention}!

Please complete the following steps:
1. Read <#rules> for server regulations
2. Verify in <#verify> to gain access
3. Assign roles in <#roles>
4. Introduce yourself in <#general>

**Quick Info:**
- Total Members: {member_count}
- Server Created: {server_created}

Enjoy your stay and follow the rules!"""

VERIFICATION_MESSAGE: Final[str] = """**VERIFICATION REQUIRED**

To gain full access to the server, react with ✅ below.

By verifying, you confirm that you:
- Have read and agree to all server rules
- Are not using an alternate account to evade bans
- Will not engage in malicious activities
- Are 13+ years old (Discord TOS requirement)

**Note:** Accounts younger than 7 days may require additional verification.
**Timeout:** You have 60 minutes to verify or you will be kicked."""

def base_perms() -> discord.Permissions:
    return discord.Permissions(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        add_reactions=True,
        use_external_emojis=True,
        embed_links=True,
        attach_files=True,
        connect=True,
        speak=True,
        use_voice_activation=True,
        use_application_commands=True,
        create_public_threads=True,
        create_private_threads=True,
        send_messages_in_threads=True
    )

def admin_perms() -> discord.Permissions:
    return discord.Permissions(administrator=True)

def mod_perms() -> discord.Permissions:
    p = base_perms()
    p.update(
        manage_messages=True,
        kick_members=True,
        ban_members=True,
        moderate_members=True,
        manage_threads=True,
        manage_nicknames=True,
        view_audit_log=True,
        mute_members=True,
        deafen_members=True,
        move_members=True,
        manage_emojis_and_stickers=True,
        view_guild_insights=True
    )
    return p

def bot_perms() -> discord.Permissions:
    p = base_perms()
    p.update(
        manage_messages=True,
        manage_channels=True,
        manage_roles=True,
        kick_members=True,
        ban_members=True,
        moderate_members=True,
        manage_webhooks=True,
        manage_threads=True,
        view_audit_log=True,
        manage_nicknames=True,
        manage_emojis_and_stickers=True,
        mute_members=True,
        deafen_members=True,
        move_members=True,
        manage_guild=True,
        view_guild_insights=True
    )
    return p

ROLES: Final[Tuple[RoleDef, ...]] = (
    RoleDef("Server Owner", 0x000001, admin_perms(), 11),
    RoleDef("Co-Owner", 0x2C2F33, admin_perms(), 10),
    RoleDef("Head Admin", 0xE74C3C, admin_perms(), 9),
    RoleDef("Admin", 0xE67E22, mod_perms(), 8),
    RoleDef("Senior Mod", 0xF39C12, mod_perms(), 7),
    RoleDef("Moderator", 0xF1C40F, mod_perms(), 6),
    RoleDef("Helper", 0x3498DB, mod_perms(), 5),
    RoleDef("Verified", 0x2ECC71, base_perms(), 4),
    RoleDef("Member", 0x95A5A6, base_perms(), 3),
    RoleDef("Unverified", 0x99AAB5, discord.Permissions(view_channel=True, read_message_history=True), 2, hoist=False),
    RoleDef("Bots", 0x5865F2, bot_perms(), 1, hoist=False, mentionable=True)
)

CATEGORIES: Final[Tuple[CatDef, ...]] = (
    CatDef("SERVER INFO", 0, ("Unverified", "Member", "Verified", "Helper", "Moderator", "Senior Mod", "Admin", "Head Admin", "Co-Owner", "Server Owner", "Bots")),
    CatDef("GENERAL", 1, ("Member", "Verified", "Helper", "Moderator", "Senior Mod", "Admin", "Head Admin", "Co-Owner", "Server Owner", "Bots")),
    CatDef("OSINT OPERATIONS", 2, ("Verified", "Helper", "Moderator", "Senior Mod", "Admin", "Head Admin", "Co-Owner", "Server Owner", "Bots")),
    CatDef("ANALYSIS & REPORTS", 3, ("Verified", "Helper", "Moderator", "Senior Mod", "Admin", "Head Admin", "Co-Owner", "Server Owner", "Bots")),
    CatDef("VOICE CHANNELS", 4, ("Member", "Verified", "Helper", "Moderator", "Senior Mod", "Admin", "Head Admin", "Co-Owner", "Server Owner", "Bots")),
    CatDef("BOT COMMANDS", 5, ("Member", "Verified", "Helper", "Moderator", "Senior Mod", "Admin", "Head Admin", "Co-Owner", "Server Owner", "Bots")),
    CatDef("STAFF AREA", 6, ("Helper", "Moderator", "Senior Mod", "Admin", "Head Admin", "Co-Owner", "Server Owner", "Bots")),
    CatDef("ADMINISTRATION", 7, ("Admin", "Head Admin", "Co-Owner", "Server Owner", "Bots"))
)

CHANNELS: Final[Tuple[ChanDef, ...]] = (
    ChanDef("rules", "SERVER INFO", "Server rules and community guidelines", RULES_TEXT, True),
    ChanDef("verify", "SERVER INFO", "Complete verification to access the server", VERIFICATION_MESSAGE, True),
    ChanDef("welcome", "SERVER INFO", "Welcome new members", "", True),
    ChanDef("announcements", "SERVER INFO", "Important server updates and announcements", "", True),
    ChanDef("updates", "SERVER INFO", "Feature updates and changelog", "", True),
    ChanDef("roles", "SERVER INFO", "Self-assignable roles and permissions info", "", True),
    ChanDef("general", "GENERAL", "Main discussion channel - stay on topic", "", False, 5),
    ChanDef("casual", "GENERAL", "Off-topic and casual conversations", "", False, 3),
    ChanDef("media", "GENERAL", "Share images, videos, and media", "", False, 10),
    ChanDef("questions", "GENERAL", "Ask questions and get help from the community", "", False, 0),
    ChanDef("osint-general", "OSINT OPERATIONS", "General OSINT discussion and techniques"),
    ChanDef("tools-resources", "OSINT OPERATIONS", "Share tools, scripts, and resources"),
    ChanDef("geoint", "OSINT OPERATIONS", "Geospatial intelligence and mapping"),
    ChanDef("socmint", "OSINT OPERATIONS", "Social media intelligence gathering"),
    ChanDef("investigations", "OSINT OPERATIONS", "Active investigation collaboration"),
    ChanDef("threat-intel", "ANALYSIS & REPORTS", "Threat intelligence sharing and analysis"),
    ChanDef("reports", "ANALYSIS & REPORTS", "Investigation reports and findings"),
    ChanDef("data-analysis", "ANALYSIS & REPORTS", "Data processing and statistical analysis"),
    ChanDef("general-voice", "VOICE CHANNELS", "", "", False, 0, True),
    ChanDef("meeting-room", "VOICE CHANNELS", "", "", False, 0, True),
    ChanDef("study-room", "VOICE CHANNELS", "", "", False, 0, True),
    ChanDef("bot-commands", "BOT COMMANDS", "Use bot commands here"),
    ChanDef("bot-spam", "BOT COMMANDS", "Bot spam and testing"),
    ChanDef("staff-chat", "STAFF AREA", "Private staff discussion"),
    ChanDef("staff-voice", "STAFF AREA", "", "", False, 0, True),
    ChanDef("admin-chat", "ADMINISTRATION", "Admin-only discussion"),
    ChanDef("audit-log", "ADMINISTRATION", "Complete audit log of all actions", "", True),
    ChanDef("message-logs", "ADMINISTRATION", "Message edit/delete logs", "", True),
    ChanDef("member-logs", "ADMINISTRATION", "Member join/leave/ban logs", "", True),
    ChanDef("mod-logs", "ADMINISTRATION", "Moderation action logs", "", True),
    ChanDef("security-logs", "ADMINISTRATION", "Security and anti-raid logs", "", True),
    ChanDef("voice-logs", "ADMINISTRATION", "Voice channel activity logs", "", True),
    ChanDef("automod-logs", "ADMINISTRATION", "Auto-moderation trigger logs", "", True),
    ChanDef("reports-inbox", "ADMINISTRATION", "User reports and tickets", "", True)
)

class ValidationError(Exception):
    pass

class RateLimitExceeded(Exception):
    pass

# Utility Functions
def get_token() -> str:
    t = DISCORD_TOKEN.strip() if DISCORD_TOKEN else os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not t:
        raise ValidationError("No token: set DISCORD_TOKEN in code or DISCORD_BOT_TOKEN env var")
    if len(t) < Config.TOKEN_MIN_LENGTH:
        raise ValidationError(f"Token too short: {len(t)} < {Config.TOKEN_MIN_LENGTH}")
    log.info(f"Token loaded ({len(t)} chars)")
    return t

def check_guild(g: discord.Guild) -> None:
    if not g.me:
        raise ValidationError("Bot member is None")
    if not g.me.guild_permissions.administrator:
        raise ValidationError("Bot needs administrator permissions")

def contains_invite_link(text: str) -> bool:
    """Check if message contains Discord invite links"""
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in INVITE_PATTERNS)

def contains_scam_link(text: str) -> bool:
    """Check if message contains known scam domains"""
    text_lower = text.lower()
    return any(domain in text_lower for domain in SCAM_DOMAINS)

def contains_profanity(text: str) -> bool:
    """Check if message contains profanity"""
    text_lower = text.lower()
    return any(word in text_lower for word in PROFANITY_LIST)

def calculate_caps_percentage(text: str) -> int:
    """Calculate percentage of uppercase letters"""
    if not text:
        return 0
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0
    caps = sum(1 for c in letters if c.isupper())
    return int((caps / len(letters)) * 100)

def contains_zalgo(text: str) -> bool:
    """Detect zalgo text (excessive combining characters)"""
    combining_chars = sum(1 for c in text if '\u0300' <= c <= '\u036f')
    return combining_chars > 10

def count_emojis(text: str) -> int:
    """Count emojis in text"""
    # Custom emoji pattern
    custom_emoji_pattern = r'<a?:\w+:\d+>'
    custom_emojis = len(re.findall(custom_emoji_pattern, text))
    
    # Unicode emoji (simplified check)
    unicode_emojis = sum(1 for c in text if ord(c) > 127000)
    
    return custom_emojis + unicode_emojis

async def resilient_operation(coro, operation_name: str, max_retries: int = Config.MAX_RETRIES) -> Tuple[bool, Optional[any]]:
    """Execute operation with exponential backoff and rate limit handling."""
    backoff = Config.INITIAL_BACKOFF
    
    for attempt in range(max_retries):
        try:
            result = await coro
            return True, result
        except discord.NotFound:
            log.debug(f"{operation_name}: Resource not found (likely already deleted)")
            return True, None
        except discord.Forbidden as e:
            log.error(f"{operation_name}: Forbidden - {e}")
            return False, None
        except discord.HTTPException as e:
            if e.status == 429:
                retry_after = float(e.response.headers.get('Retry-After', backoff))
                log.warning(f"{operation_name}: Rate limited, waiting {retry_after:.2f}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(retry_after)
                backoff = min(backoff * Config.BACKOFF_MULTIPLIER, Config.MAX_BACKOFF)
            elif 500 <= e.status < 600:
                log.warning(f"{operation_name}: Server error {e.status}, retrying in {backoff:.2f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * Config.BACKOFF_MULTIPLIER, Config.MAX_BACKOFF)
            else:
                log.error(f"{operation_name}: HTTP {e.status} - {e}")
                return False, None
        except Exception as e:
            log.error(f"{operation_name}: Unexpected error - {e}")
            if attempt == max_retries - 1:
                return False, None
            await asyncio.sleep(backoff)
            backoff = min(backoff * Config.BACKOFF_MULTIPLIER, Config.MAX_BACKOFF)
    
    return False, None

async def batch_delete(items: List, item_type: str, semaphore: asyncio.Semaphore, keep_ids: Set[int] = None) -> int:
    """Delete items in parallel batches with semaphore control."""
    keep_ids = keep_ids or set()
    items_to_delete = [item for item in items if item.id not in keep_ids]
    
    if not items_to_delete:
        return 0
    
    async def delete_single(item):
        async with semaphore:
            success, _ = await resilient_operation(
                item.delete(reason="Infrastructure cleanup"),
                f"Delete {item_type} {getattr(item, 'name', item.id)}"
            )
            await asyncio.sleep(Config.BASE_DELAY)
            return success
    
    results = await asyncio.gather(*[delete_single(item) for item in items_to_delete], return_exceptions=True)
    success_count = sum(1 for r in results if r is True)
    
    log.info(f"Deleted {success_count}/{len(items_to_delete)} {item_type}s")
    return success_count

async def purge_server(g: discord.Guild, state: DeploymentState, semaphore: asyncio.Semaphore) -> None:
    """Completely purge server infrastructure with parallel processing."""
    log.info(f"Initiating complete server purge: {g.name}")
    state.phase = "purge"
    
    keep_ids = {state.progress_channel_id} if state.progress_channel_id else set()
    
    # Delete AutoMod rules first
    try:
        automod_rules = await g.fetch_automod_rules()
        for rule in automod_rules:
            try:
                await rule.delete(reason="Infrastructure cleanup")
                log.info(f"Deleted AutoMod rule: {rule.name}")
            except:
                pass
    except:
        pass
    
    channels = [c for c in g.channels if not isinstance(c, discord.CategoryChannel)]
    categories = list(g.categories)
    roles = [r for r in g.roles if r.name != "@everyone" and not r.managed]
    
    log.info(f"Purging {len(channels)} channels, {len(categories)} categories, {len(roles)} roles")
    
    state.deleted_channels = await batch_delete(channels, "channel", semaphore, keep_ids)
    await asyncio.sleep(Config.BASE_DELAY * 2)
    
    state.deleted_channels += await batch_delete(categories, "category", semaphore, keep_ids)
    await asyncio.sleep(Config.BASE_DELAY * 2)
    
    sorted_roles = sorted(roles, key=lambda r: r.position, reverse=True)
    state.deleted_roles = await batch_delete(sorted_roles, "role", semaphore)
    
    log.info(f"Purge complete: {state.deleted_channels} channels, {state.deleted_roles} roles deleted")

def calc_overwrites(g: discord.Guild, role_map: Dict[str, discord.Role], allowed: Tuple[str, ...]) -> Dict[discord.Role, discord.PermissionOverwrite]:
    """Pre-compute permission overwrites for categories."""
    overwrites = {
        g.default_role: discord.PermissionOverwrite(
            view_channel=False,
            send_messages=False,
            connect=False,
            add_reactions=False,
            use_application_commands=False
        )
    }
    
    for role_name in allowed:
        if role := role_map.get(role_name):
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                connect=True,
                speak=True,
                use_voice_activation=True,
                add_reactions=True,
                embed_links=True,
                attach_files=True,
                use_external_emojis=True,
                use_application_commands=True,
                create_public_threads=True,
                send_messages_in_threads=True
            )
    
    return overwrites

async def build_roles(g: discord.Guild, state: DeploymentState, semaphore: asyncio.Semaphore) -> Dict[str, discord.Role]:
    """Build role hierarchy with parallel creation."""
    log.info("Building role hierarchy")
    state.phase = "roles"
    role_map: Dict[str, discord.Role] = {}
    
    sorted_roles = sorted(ROLES, key=lambda x: x.pos)
    
    async def create_role(role_def: RoleDef) -> Tuple[str, Optional[discord.Role]]:
        async with semaphore:
            success, role = await resilient_operation(
                g.create_role(
                    name=role_def.name,
                    color=discord.Color(role_def.color),
                    permissions=role_def.perms,
                    hoist=role_def.hoist,
                    mentionable=role_def.mentionable,
                    reason="Auto deployment"
                ),
                f"Create role {role_def.name}"
            )
            await asyncio.sleep(Config.BASE_DELAY)
            if success and role:
                log.info(f"[+] Role: {role_def.name}")
                return role_def.name, role
            else:
                log.error(f"[-] Role: {role_def.name}")
                return role_def.name, None
    
    results = await asyncio.gather(*[create_role(rd) for rd in sorted_roles])
    
    for name, role in results:
        if role:
            role_map[name] = role
            state.created_roles.append(name)
    
    if len(role_map) != len(ROLES):
        raise RuntimeError(f"Role creation failed: {len(role_map)}/{len(ROLES)} created")
    
    return role_map

async def build_infra(g: discord.Guild, role_map: Dict[str, discord.Role], state: DeploymentState, semaphore: asyncio.Semaphore) -> Tuple[int, int, LogChannels]:
    """Build complete channel infrastructure with parallel processing and webhooks."""
    log.info("Building infrastructure")
    state.phase = "infrastructure"
    cat_map: Dict[str, discord.CategoryChannel] = {}
    log_channels = LogChannels()
    
    sorted_categories = sorted(CATEGORIES, key=lambda x: x.pos)
    
    async def create_category(cat_def: CatDef) -> Tuple[str, Optional[discord.CategoryChannel]]:
        async with semaphore:
            overwrites = calc_overwrites(g, role_map, cat_def.roles)
            success, cat = await resilient_operation(
                g.create_category(
                    name=cat_def.name,
                    overwrites=overwrites,
                    position=cat_def.pos,
                    reason="Infrastructure deployment"
                ),
                f"Create category {cat_def.name}"
            )
            await asyncio.sleep(Config.BASE_DELAY)
            if success and cat:
                log.info(f"[+] Category: {cat_def.name}")
                return cat_def.name, cat
            else:
                log.error(f"[-] Category: {cat_def.name}")
                return cat_def.name, None
    
    cat_results = await asyncio.gather(*[create_category(cd) for cd in sorted_categories])
    
    for name, cat in cat_results:
        if cat:
            cat_map[name] = cat
            state.created_categories.append(name)
    
    if len(cat_map) != len(CATEGORIES):
        raise RuntimeError(f"Category creation failed: {len(cat_map)}/{len(CATEGORIES)} created")
    
    async def create_channel(chan_def: ChanDef) -> Tuple[str, bool]:
        cat = cat_map.get(chan_def.cat)
        if not cat:
            log.error(f"Category {chan_def.cat} not found for {chan_def.name}")
            return chan_def.name, False
        
        async with semaphore:
            try:
                if chan_def.voice:
                    success, chan = await resilient_operation(
                        g.create_voice_channel(
                            name=chan_def.name,
                            category=cat,
                            reason="Infrastructure deployment"
                        ),
                        f"Create voice channel {chan_def.name}"
                    )
                else:
                    success, chan = await resilient_operation(
                        g.create_text_channel(
                            name=chan_def.name,
                            category=cat,
                            topic=chan_def.topic or None,
                            slowmode_delay=chan_def.slow,
                            reason="Infrastructure deployment"
                        ),
                        f"Create text channel {chan_def.name}"
                    )
                    
                    if success and chan and chan_def.readonly:
                        await chan.set_permissions(
                            g.default_role,
                            send_messages=False,
                            add_reactions=False,
                            create_public_threads=False,
                            reason="Read-only channel"
                        )
                    
                    # Create webhooks for log channels
                    if success and chan and chan_def.name in ["message-logs", "member-logs", "mod-logs", "security-logs", "voice-logs"]:
                        try:
                            webhook = await chan.create_webhook(name=f"{chan_def.name}-webhook", reason="Logging webhook")
                            state.webhooks_created += 1
                            
                            if chan_def.name == "message-logs":
                                log_channels.message_log = webhook
                            elif chan_def.name == "member-logs":
                                log_channels.member_log = webhook
                            elif chan_def.name == "mod-logs":
                                log_channels.mod_log = webhook
                            elif chan_def.name == "security-logs":
                                log_channels.security_log = webhook
                            elif chan_def.name == "voice-logs":
                                log_channels.voice_log = webhook
                            
                            log.info(f"[+] Webhook created for {chan_def.name}")
                        except Exception as e:
                            log.error(f"Failed to create webhook for {chan_def.name}: {e}")
                    
                    if success and chan and chan_def.msg:
                        msg = await chan.send(chan_def.msg)
                        # Add reaction for verification channel
                        if chan_def.name == "verify":
                            await msg.add_reaction(Config.VERIFICATION_EMOJI)
                
                await asyncio.sleep(Config.BASE_DELAY)
                if success:
                    log.info(f"[+] Channel: {chan_def.name}")
                    return chan_def.name, True
                else:
                    log.error(f"[-] Channel: {chan_def.name}")
                    return chan_def.name, False
            except Exception as e:
                log.error(f"[-] Channel {chan_def.name}: {e}")
                return chan_def.name, False
    
    chan_results = await asyncio.gather(*[create_channel(ch) for ch in CHANNELS])
    
    success_count = sum(1 for _, success in chan_results if success)
    for name, success in chan_results:
        if success:
            state.created_channels.append(name)
    
    if success_count != len(CHANNELS):
        raise RuntimeError(f"Channel creation failed: {success_count}/{len(CHANNELS)} created")
    
    return len(cat_map), success_count, log_channels

async def setup_automod(g: discord.Guild, state: DeploymentState) -> int:
    """Setup comprehensive AutoMod rules"""
    log.info("Setting up AutoMod rules")
    state.phase = "automod"
    rules_created = 0
    
    try:
        # Rule 1: Block Discord Invites
        if Config.BLOCK_INVITE_LINKS:
            rule = await g.create_automod_rule(
                name="Block Discord Invites",
                event_type=discord.AutoModEventType.message_send,
                trigger_type=discord.AutoModTriggerType.keyword,
                trigger_metadata=discord.AutoModTriggerMetadata(
                    regex_patterns=[r"discord\.gg/.*", r"discord\.com/invite/.*", r"discordapp\.com/invite/.*"]
                ),
                actions=[
                    discord.AutoModAction(type=discord.AutoModActionType.block_message),
                    discord.AutoModAction(
                        type=discord.AutoModActionType.send_alert_message,
                        channel_id=discord.utils.get(g.text_channels, name="automod-logs").id if discord.utils.get(g.text_channels, name="automod-logs") else None
                    )
                ],
                enabled=True,
                exempt_roles=[role for role in g.roles if role.name in Config.ALLOW_LINKS_ROLES],
                exempt_channels=[],
                reason="Block unauthorized Discord invite links"
            )
            rules_created += 1
            state.automod_rules.append(rule.id)
            log.info("[+] AutoMod: Block Discord Invites")
        
        # Rule 2: Block Known Scam Links
        if Config.BLOCK_SUSPICIOUS_LINKS:
            scam_patterns = [domain.replace(".", r"\.") for domain in SCAM_DOMAINS]
            rule = await g.create_automod_rule(
                name="Block Scam Links",
                event_type=discord.AutoModEventType.message_send,
                trigger_type=discord.AutoModTriggerType.keyword,
                trigger_metadata=discord.AutoModTriggerMetadata(
                    regex_patterns=scam_patterns[:10]  # Discord limits patterns
                ),
                actions=[
                    discord.AutoModAction(type=discord.AutoModActionType.block_message),
                    discord.AutoModAction(
                        type=discord.AutoModActionType.send_alert_message,
                        channel_id=discord.utils.get(g.text_channels, name="security-logs").id if discord.utils.get(g.text_channels, name="security-logs") else None
                    ),
                    discord.AutoModAction(
                        type=discord.AutoModActionType.timeout,
                        duration=timedelta(minutes=10)
                    )
                ],
                enabled=True,
                exempt_roles=[role for role in g.roles if role.name in ("Admin", "Head Admin", "Co-Owner", "Server Owner")],
                exempt_channels=[],
                reason="Block known scam and phishing domains"
            )
            rules_created += 1
            state.automod_rules.append(rule.id)
            log.info("[+] AutoMod: Block Scam Links")
        
        # Rule 3: Block Mass Mentions
        if Config.BLOCK_MASS_MENTIONS:
            rule = await g.create_automod_rule(
                name="Block Mass Mentions",
                event_type=discord.AutoModEventType.message_send,
                trigger_type=discord.AutoModTriggerType.mention_spam,
                trigger_metadata=discord.AutoModTriggerMetadata(
                    mention_total_limit=Config.MAX_MENTIONS
                ),
                actions=[
                    discord.AutoModAction(type=discord.AutoModActionType.block_message),
                    discord.AutoModAction(
                        type=discord.AutoModActionType.timeout,
                        duration=timedelta(minutes=5)
                    )
                ],
                enabled=True,
                exempt_roles=[role for role in g.roles if role.name in ("Moderator", "Senior Mod", "Admin", "Head Admin", "Co-Owner", "Server Owner")],
                exempt_channels=[],
                reason="Prevent mass mention spam"
            )
            rules_created += 1
            state.automod_rules.append(rule.id)
            log.info("[+] AutoMod: Block Mass Mentions")
        
        # Rule 4: Profanity Filter
        if Config.FILTER_PROFANITY:
            rule = await g.create_automod_rule(
                name="Profanity Filter",
                event_type=discord.AutoModEventType.message_send,
                trigger_type=discord.AutoModTriggerType.keyword,
                trigger_metadata=discord.AutoModTriggerMetadata(
                    keyword_filter=list(PROFANITY_LIST)
                ),
                actions=[
                    discord.AutoModAction(type=discord.AutoModActionType.block_message),
                    discord.AutoModAction(
                        type=discord.AutoModActionType.send_alert_message,
                        channel_id=discord.utils.get(g.text_channels, name="automod-logs").id if discord.utils.get(g.text_channels, name="automod-logs") else None
                    )
                ],
                enabled=True,
                exempt_roles=[role for role in g.roles if role.name in ("Helper", "Moderator", "Senior Mod", "Admin", "Head Admin", "Co-Owner", "Server Owner")],
                exempt_channels=[],
                reason="Filter profanity and offensive language"
            )
            rules_created += 1
            state.automod_rules.append(rule.id)
            log.info("[+] AutoMod: Profanity Filter")
        
        log.info(f"Created {rules_created} AutoMod rules")
        return rules_created
        
    except Exception as e:
        log.error(f"AutoMod setup failed: {e}")
        return rules_created

class InfraBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()  # Need all intents for comprehensive moderation
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            max_messages=10000  # Keep message cache for better logging
        )
        self.deploy_lock = asyncio.Lock()
        self.deploy_semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT)
        self.deployment_states: Dict[int, DeploymentState] = {}
        self.security_states: Dict[int, SecurityState] = {}
        self.log_channels: Dict[int, LogChannels] = {}
        self.start_time = datetime.now(timezone.utc)

    async def setup_hook(self) -> None:
        try:
            synced = await self.tree.sync()
            log.info(f"Synced {len(synced)} commands globally")
        except Exception as e:
            log.error(f"Command sync failed: {e}")
        
        # Start background tasks
        self.cleanup_verification.start()
        self.security_monitor.start()

    async def on_ready(self) -> None:
        if not self.user:
            log.critical("User is None")
            await self.close()
            sys.exit(ExitCode.FATAL_ERROR)
        
        log.info(f"Ready: {self.user.name} (ID: {self.user.id})")
        log.info(f"Guilds: {len(self.guilds)}")
        log.info(f"Latency: {self.latency * 1000:.2f}ms")
        log.info(f"Caching {len(self.users)} users")
        
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="server security | /deploy"
            ),
            status=discord.Status.online
        )
        
        # Initialize security states for all guilds
        for guild in self.guilds:
            if guild.id not in self.security_states:
                self.security_states[guild.id] = SecurityState()
    
    @tasks.loop(minutes=5)
    async def cleanup_verification(self):
        """Remove unverified users after timeout"""
        for guild in self.guilds:
            security_state = self.security_states.get(guild.id)
            if not security_state:
                continue
            
            current_time = datetime.now(timezone.utc)
            to_remove = []
            
            for user_id, join_time in security_state.verification_pending.items():
                if (current_time - join_time).total_seconds() > Config.UNVERIFIED_KICK_AFTER:
                    member = guild.get_member(user_id)
                    if member:
                        try:
                            await member.kick(reason="Failed to verify within time limit")
                            log.info(f"Kicked unverified user: {member} ({member.id})")
                            to_remove.append(user_id)
                            
                            # Log to security
                            if webhook := self.log_channels.get(guild.id, LogChannels()).security_log:
                                embed = discord.Embed(
                                    title="Unverified User Kicked",
                                    description=f"**User:** {member.mention} (`{member.id}`)\n**Reason:** Failed to verify within {Config.UNVERIFIED_KICK_AFTER//60} minutes",
                                    color=0xE67E22,
                                    timestamp=current_time
                                )
                                await webhook.send(embed=embed)
                        except:
                            pass
            
            for user_id in to_remove:
                del security_state.verification_pending[user_id]
    
    @tasks.loop(seconds=30)
    async def security_monitor(self):
        """Monitor for raid attempts and suspicious activity"""
        for guild in self.guilds:
            security_state = self.security_states.get(guild.id)
            if not security_state:
                continue
            
            current_time = datetime.now(timezone.utc)
            
            # Check for raid (multiple joins in short time)
            recent_joins = [t for t in security_state.raid_joins if (current_time - t).total_seconds() < Config.RAID_JOIN_WINDOW]
            
            if len(recent_joins) >= Config.RAID_JOIN_THRESHOLD and not security_state.lockdown_active:
                # Activate raid protection
                security_state.lockdown_active = True
                log.warning(f"RAID DETECTED in {guild.name} - {len(recent_joins)} joins in {Config.RAID_JOIN_WINDOW}s")
                
                # Log to security channel
                if webhook := self.log_channels.get(guild.id, LogChannels()).security_log:
                    embed = discord.Embed(
                        title="[ALERT] RAID DETECTED",
                        description=f"**Joins:** {len(recent_joins)} in {Config.RAID_JOIN_WINDOW} seconds\n**Action:** Server lockdown activated\n**Status:** Monitoring for suspicious accounts",
                        color=0xFF0000,
                        timestamp=current_time
                    )
                    await webhook.send(embed=embed)
                
                # Enable verification requirement
                try:
                    await guild.edit(verification_level=discord.VerificationLevel.high)
                    log.info(f"Enabled high verification level for {guild.name}")
                except:
                    pass

bot = InfraBot()

# EVENT HANDLERS

@bot.event
async def on_member_join(member: discord.Member) -> None:
    """Enhanced member join with security checks and welcome message"""
    g = member.guild
    security_state = bot.security_states.get(g.id)
    log_channels = bot.log_channels.get(g.id, LogChannels())
    
    if not security_state:
        security_state = SecurityState()
        bot.security_states[g.id] = security_state
    
    current_time = datetime.now(timezone.utc)
    
    # Track join for raid detection
    security_state.raid_joins.append(current_time)
    
    # Account age check
    account_age = (current_time - member.created_at).total_seconds()
    is_suspicious = account_age < Config.RAID_ACCOUNT_AGE_MIN
    has_avatar = member.avatar is not None
    
    if is_suspicious or not has_avatar:
        security_state.suspicious_users.add(member.id)
    
    # Assign Unverified role
    unverified_role = discord.utils.get(g.roles, name="Unverified")
    if unverified_role:
        try:
            await member.add_roles(unverified_role, reason="New member - pending verification")
            security_state.verification_pending[member.id] = current_time
        except:
            pass
    
    # Send welcome message
    welcome_channel = discord.utils.get(g.text_channels, name="welcome")
    if welcome_channel:
        try:
            welcome_text = WELCOME_MESSAGE.format(
                server_name=g.name,
                user_mention=member.mention,
                member_count=g.member_count,
                server_created=f"<t:{int(g.created_at.timestamp())}:D>"
            )
            await welcome_channel.send(welcome_text)
        except:
            pass
    
    # Log to member-logs
    if log_channels.member_log:
        embed = discord.Embed(
            title="Member Joined",
            color=0x2ECC71 if not is_suspicious else 0xE67E22,
            timestamp=current_time
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Member Count", value=f"`{g.member_count}`", inline=True)
        
        if is_suspicious:
            embed.add_field(name="[WARNING] Suspicious", value=f"Account age: {int(account_age/86400)} days", inline=False)
        if not has_avatar:
            embed.add_field(name="[WARNING] No Avatar", value="Default avatar detected", inline=False)
        
        await log_channels.member_log.send(embed=embed)
    
    log.info(f"Member joined: {member} ({member.id}) - Suspicious: {is_suspicious}")

@bot.event
async def on_member_remove(member: discord.Member) -> None:
    """Log member leaves/kicks"""
    g = member.guild
    security_state = bot.security_states.get(g.id)
    log_channels = bot.log_channels.get(g.id, LogChannels())
    
    if security_state and member.id in security_state.verification_pending:
        del security_state.verification_pending[member.id]
    
    if security_state and member.id in security_state.suspicious_users:
        security_state.suspicious_users.discard(member.id)
    
    if log_channels.member_log:
        embed = discord.Embed(
            title="Member Left",
            description=f"**User:** {member.mention} (`{member.id}`)\n**Roles:** {', '.join([r.mention for r in member.roles[1:]][:5])}",
            color=0xE74C3C,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await log_channels.member_log.send(embed=embed)
    
    log.info(f"Member left: {member} ({member.id})")

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    """Handle verification reactions"""
    if payload.member.bot:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    channel = guild.get_channel(payload.channel_id)
    if not channel or channel.name != "verify":
        return
    
    if str(payload.emoji) != Config.VERIFICATION_EMOJI:
        return
    
    security_state = bot.security_states.get(guild.id)
    if not security_state:
        return
    
    member = payload.member
    unverified_role = discord.utils.get(guild.roles, name="Unverified")
    member_role = discord.utils.get(guild.roles, name="Member")
    
    if not unverified_role or not member_role:
        return
    
    try:
        # Remove Unverified, add Member
        await member.remove_roles(unverified_role, reason="Verification completed")
        await member.add_roles(member_role, reason="Verification completed")
        
        # Remove from pending
        if member.id in security_state.verification_pending:
            del security_state.verification_pending[member.id]
        
        # Remove from suspicious if was there
        security_state.suspicious_users.discard(member.id)
        
        # Log success
        log_channels = bot.log_channels.get(guild.id, LogChannels())
        if log_channels.member_log:
            embed = discord.Embed(
                title="Member Verified",
                description=f"**User:** {member.mention} (`{member.id}`)\n**Status:** Full server access granted",
                color=0x2ECC71,
                timestamp=datetime.now(timezone.utc)
            )
            await log_channels.member_log.send(embed=embed)
        
        log.info(f"Member verified: {member} ({member.id})")
        
    except Exception as e:
        log.error(f"Verification failed for {member}: {e}")

@bot.event
async def on_message(message: discord.Message) -> None:
    """Comprehensive message filtering and anti-spam"""
    if message.author.bot or not message.guild:
        return
    
    guild = message.guild
    security_state = bot.security_states.get(guild.id)
    if not security_state:
        security_state = SecurityState()
        bot.security_states[guild.id] = security_state
    
    log_channels = bot.log_channels.get(guild.id, LogChannels())
    current_time = datetime.now(timezone.utc)
    
    # Bypass checks for staff
    staff_roles = {"Helper", "Moderator", "Senior Mod", "Admin", "Head Admin", "Co-Owner", "Server Owner"}
    is_staff = any(role.name in staff_roles for role in message.author.roles)
    
    if not is_staff:
        violations = []
        
        # Spam detection
        user_messages = security_state.spam_tracker[message.author.id]
        user_messages.append(current_time)
        
        recent_messages = [t for t in user_messages if (current_time - t).total_seconds() < Config.SPAM_TIME_WINDOW]
        if len(recent_messages) >= Config.SPAM_MESSAGE_THRESHOLD:
            violations.append("Spam detected")
            security_state.spam_tracker[message.author.id].clear()
        
        # Check for invite links
        if Config.BLOCK_INVITE_LINKS and contains_invite_link(message.content):
            violations.append("Unauthorized invite link")
        
        # Check for scam links
        if Config.BLOCK_SUSPICIOUS_LINKS and contains_scam_link(message.content):
            violations.append("Scam/phishing link detected")
        
        # Check excessive caps
        if Config.BLOCK_EXCESSIVE_CAPS:
            caps_percentage = calculate_caps_percentage(message.content)
            if caps_percentage > Config.MAX_CAPS_PERCENTAGE and len(message.content) > 10:
                violations.append(f"Excessive caps ({caps_percentage}%)")
        
        # Check zalgo text
        if Config.BLOCK_ZALGO and contains_zalgo(message.content):
            violations.append("Zalgo/corrupted text")
        
        # Check emoji spam
        if Config.DETECT_MASS_EMOJIS:
            emoji_count = count_emojis(message.content)
            if emoji_count > Config.MAX_EMOJIS:
                violations.append(f"Excessive emojis ({emoji_count})")
        
        # Check message length
        if len(message.content) > Config.MAX_MESSAGE_LENGTH:
            violations.append("Message too long")
        
        # Check line spam
        line_count = message.content.count('\n')
        if line_count > Config.MAX_LINES:
            violations.append(f"Excessive lines ({line_count})")
        
        # Handle violations
        if violations:
            try:
                await message.delete()
                
                # Issue warning
                security_state.warning_counts[message.author.id] += 1
                warning_count = security_state.warning_counts[message.author.id]
                
                # Send warning DM
                try:
                    await message.author.send(
                        f"**[WARNING {warning_count}/{Config.MAX_WARNINGS}]** Your message was removed from {guild.name}\n"
                        f"**Reason:** {', '.join(violations)}\n"
                        f"**Message:** {message.content[:100]}...\n\n"
                        f"Please review the server rules. Further violations may result in a timeout or ban."
                    )
                except:
                    pass
                
                # Apply punishment based on warning count
                if warning_count >= Config.MAX_WARNINGS:
                    # Timeout for repeated violations
                    timeout_duration = timedelta(seconds=Config.WARNING_MUTE_DURATION)
                    await message.author.timeout(timeout_duration, reason=f"Exceeded warning limit: {', '.join(violations)}")
                    security_state.warning_counts[message.author.id] = 0  # Reset after punishment
                    
                    log.info(f"Timed out {message.author} for {Config.WARNING_MUTE_DURATION}s: {violations}")
                
                # Log to mod logs
                if log_channels.mod_log:
                    embed = discord.Embed(
                        title="Message Removed - Violation",
                        color=0xE67E22,
                        timestamp=current_time
                    )
                    embed.add_field(name="User", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
                    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                    embed.add_field(name="Warnings", value=f"`{warning_count}/{Config.MAX_WARNINGS}`", inline=True)
                    embed.add_field(name="Violations", value=f"`{', '.join(violations)}`", inline=False)
                    embed.add_field(name="Message Content", value=f"```{message.content[:500]}```", inline=False)
                    
                    if warning_count >= Config.MAX_WARNINGS:
                        embed.add_field(name="Action Taken", value=f"Timed out for {Config.WARNING_MUTE_DURATION//60} minutes", inline=False)
                    
                    await log_channels.mod_log.send(embed=embed)
                
                log.info(f"Removed message from {message.author}: {violations}")
                
            except Exception as e:
                log.error(f"Error handling message violation: {e}")
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message: discord.Message) -> None:
    """Log deleted messages"""
    if message.author.bot or not message.guild:
        return
    
    log_channels = bot.log_channels.get(message.guild.id, LogChannels())
    if not log_channels.message_log:
        return
    
    embed = discord.Embed(
        title="Message Deleted",
        color=0xE74C3C,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
    embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="Content", value=f"```{message.content[:1000] if message.content else '[No text content]'}```", inline=False)
    
    if message.attachments:
        embed.add_field(name="Attachments", value=f"{len(message.attachments)} file(s)", inline=False)
    
    await log_channels.message_log.send(embed=embed)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
    """Log edited messages"""
    if before.author.bot or not before.guild or before.content == after.content:
        return
    
    log_channels = bot.log_channels.get(before.guild.id, LogChannels())
    if not log_channels.message_log:
        return
    
    embed = discord.Embed(
        title="Message Edited",
        color=0x3498DB,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
    embed.add_field(name="Author", value=f"{before.author.mention} (`{before.author.id}`)", inline=True)
    embed.add_field(name="Channel", value=before.channel.mention, inline=True)
    embed.add_field(name="Before", value=f"```{before.content[:500]}```", inline=False)
    embed.add_field(name="After", value=f"```{after.content[:500]}```", inline=False)
    embed.add_field(name="Jump", value=f"[Go to message]({after.jump_url})", inline=False)
    
    await log_channels.message_log.send(embed=embed)

@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User) -> None:
    """Log member bans"""
    log_channels = bot.log_channels.get(guild.id, LogChannels())
    if not log_channels.mod_log:
        return
    
    # Try to get ban reason from audit log
    reason = "No reason provided"
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                reason = entry.reason or "No reason provided"
                break
    except:
        pass
    
    embed = discord.Embed(
        title="Member Banned",
        description=f"**User:** {user.mention} (`{user.id}`)\n**Reason:** {reason}",
        color=0xFF0000,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await log_channels.mod_log.send(embed=embed)
    log.info(f"Member banned: {user} ({user.id}) - Reason: {reason}")

@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User) -> None:
    """Log member unbans"""
    log_channels = bot.log_channels.get(guild.id, LogChannels())
    if not log_channels.mod_log:
        return
    
    embed = discord.Embed(
        title="Member Unbanned",
        description=f"**User:** {user.mention} (`{user.id}`)",
        color=0x2ECC71,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await log_channels.mod_log.send(embed=embed)
    log.info(f"Member unbanned: {user} ({user.id})")

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
    """Log voice channel activity"""
    if member.bot:
        return
    
    log_channels = bot.log_channels.get(member.guild.id, LogChannels())
    if not log_channels.voice_log:
        return
    
    embed = discord.Embed(
        color=0x9B59B6,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
    
    if before.channel is None and after.channel is not None:
        # Joined voice
        embed.title = "Voice Channel Joined"
        embed.description = f"{member.mention} joined {after.channel.mention}"
        embed.color = 0x2ECC71
    elif before.channel is not None and after.channel is None:
        # Left voice
        embed.title = "Voice Channel Left"
        embed.description = f"{member.mention} left {before.channel.mention}"
        embed.color = 0xE74C3C
    elif before.channel != after.channel:
        # Moved channels
        embed.title = "Voice Channel Moved"
        embed.description = f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}"
        embed.color = 0x3498DB
    else:
        # State change (mute/deafen)
        changes = []
        if before.self_mute != after.self_mute:
            changes.append(f"Self Mute: {after.self_mute}")
        if before.self_deaf != after.self_deaf:
            changes.append(f"Self Deafen: {after.self_deaf}")
        if before.self_stream != after.self_stream:
            changes.append(f"Streaming: {after.self_stream}")
        if before.self_video != after.self_video:
            changes.append(f"Video: {after.self_video}")
        
        if changes:
            embed.title = "Voice State Changed"
            embed.description = f"{member.mention} in {after.channel.mention}\n" + "\n".join(changes)
        else:
            return
    
    await log_channels.voice_log.send(embed=embed)

# SLASH COMMANDS

@bot.tree.command(name="deploy", description="[ADMIN] Full server reconstruction - complete infrastructure deployment")
@app_commands.checks.has_permissions(administrator=True)
async def deploy(inter: discord.Interaction) -> None:
    g = inter.guild
    if not g:
        await inter.response.send_message("[ERROR] Must be executed in a guild", ephemeral=True)
        return
    
    try:
        check_guild(g)
    except ValidationError as e:
        await inter.response.send_message(f"[ERROR] Validation failed: {e}", ephemeral=True)
        return
    
    if bot.deploy_lock.locked():
        await inter.response.send_message("[WARNING] Deployment already in progress", ephemeral=True)
        return
    
    async with bot.deploy_lock:
        state = DeploymentState()
        bot.deployment_states[g.id] = state
        prog_channel: Optional[discord.TextChannel] = None
        
        try:
            await inter.response.send_message(
                "**DEPLOYMENT INITIATED**\nCreating monitoring channel...",
                ephemeral=True
            )
            
            prog_channel = await g.create_text_channel(
                "deployment-progress",
                reason=f"Deployment monitoring by {inter.user}"
            )
            state.progress_channel_id = prog_channel.id
            
            emb_start = discord.Embed(
                title="INFRASTRUCTURE DEPLOYMENT",
                description=f"**Executor:** {inter.user.mention} (`{inter.user.id}`)\n**Started:** <t:{int(state.start_time.timestamp())}:F>",
                color=0x3498DB,
                timestamp=state.start_time
            )
            emb_start.add_field(name="Status", value="Initializing...", inline=False)
            emb_start.set_footer(text=f"Guild: {g.name}")
            await prog_channel.send(embed=emb_start)
            
            log.info(f"Deployment started by {inter.user} ({inter.user.id}) in {g.name} ({g.id})")
            
            # Phase 1: Complete purge
            emb_p1 = discord.Embed(
                title="Phase 1: Complete Server Purge",
                description="Removing all existing infrastructure...",
                color=0xE74C3C,
                timestamp=datetime.now(timezone.utc)
            )
            msg_p1 = await prog_channel.send(embed=emb_p1)
            
            await purge_server(g, state, bot.deploy_semaphore)
            
            emb_p1.color = 0x2ECC71
            emb_p1.description = "[OK] Purge completed successfully"
            emb_p1.add_field(name="Channels Deleted", value=f"`{state.deleted_channels}`", inline=True)
            emb_p1.add_field(name="Roles Deleted", value=f"`{state.deleted_roles}`", inline=True)
            await msg_p1.edit(embed=emb_p1)
            
            # Phase 2: Role construction
            emb_p2 = discord.Embed(
                title="Phase 2: Role Hierarchy",
                description="Building role structure...",
                color=0xF39C12,
                timestamp=datetime.now(timezone.utc)
            )
            msg_p2 = await prog_channel.send(embed=emb_p2)
            
            role_map = await build_roles(g, state, bot.deploy_semaphore)
            
            emb_p2.color = 0x2ECC71
            emb_p2.description = "[OK] Role hierarchy completed"
            emb_p2.add_field(name="Roles Created", value=f"`{len(role_map)}`", inline=True)
            role_list = ", ".join([f"`{r}`" for r in state.created_roles[:10]])
            if len(state.created_roles) > 10:
                role_list += f" +{len(state.created_roles) - 10} more"
            emb_p2.add_field(name="Created Roles", value=role_list, inline=False)
            await msg_p2.edit(embed=emb_p2)
            
            # Phase 3: Infrastructure deployment
            emb_p3 = discord.Embed(
                title="Phase 3: Channel Infrastructure",
                description="Deploying categories, channels, and webhooks...",
                color=0x9B59B6,
                timestamp=datetime.now(timezone.utc)
            )
            msg_p3 = await prog_channel.send(embed=emb_p3)
            
            cats, chans, log_channels = await build_infra(g, role_map, state, bot.deploy_semaphore)
            bot.log_channels[g.id] = log_channels
            
            emb_p3.color = 0x2ECC71
            emb_p3.description = "[OK] Infrastructure deployment completed"
            emb_p3.add_field(name="Categories", value=f"`{cats}`", inline=True)
            emb_p3.add_field(name="Channels", value=f"`{chans}`", inline=True)
            emb_p3.add_field(name="Webhooks", value=f"`{state.webhooks_created}`", inline=True)
            await msg_p3.edit(embed=emb_p3)
            
            # Phase 4: AutoMod setup
            emb_p4 = discord.Embed(
                title="Phase 4: Auto-Moderation",
                description="Setting up AutoMod rules and security...",
                color=0x1ABC9C,
                timestamp=datetime.now(timezone.utc)
            )
            msg_p4 = await prog_channel.send(embed=emb_p4)
            
            automod_count = await setup_automod(g, state)
            
            emb_p4.color = 0x2ECC71
            emb_p4.description = "[OK] AutoMod configuration completed"
            emb_p4.add_field(name="Rules Created", value=f"`{automod_count}`", inline=True)
            await msg_p4.edit(embed=emb_p4)
            
            # Initialize security state
            bot.security_states[g.id] = SecurityState()
            
            # Cleanup and finalize
            if prog_channel:
                try:
                    await prog_channel.delete()
                except:
                    pass
            
            completion_channel = await g.create_text_channel(
                "deployment-complete",
                reason="Deployment completion report"
            )
            
            duration = (datetime.now(timezone.utc) - state.start_time).total_seconds()
            
            emb_final = discord.Embed(
                title="[SUCCESS] INFRASTRUCTURE DEPLOYMENT COMPLETE",
                description="Full server reconstruction finished successfully",
                color=0x2ECC71,
                timestamp=datetime.now(timezone.utc)
            )
            emb_final.add_field(name="Executor", value=f"{inter.user.mention}", inline=True)
            emb_final.add_field(name="Duration", value=f"`{duration:.2f}s`", inline=True)
            emb_final.add_field(name="Server", value=f"`{g.name}`", inline=True)
            emb_final.add_field(name="Roles Created", value=f"`{len(role_map)}`", inline=True)
            emb_final.add_field(name="Categories", value=f"`{cats}`", inline=True)
            emb_final.add_field(name="Channels", value=f"`{chans}`", inline=True)
            emb_final.add_field(name="Webhooks", value=f"`{state.webhooks_created}`", inline=True)
            emb_final.add_field(name="AutoMod Rules", value=f"`{automod_count}`", inline=True)
            emb_final.add_field(name="Channels Purged", value=f"`{state.deleted_channels}`", inline=True)
            emb_final.add_field(name="Roles Purged", value=f"`{state.deleted_roles}`", inline=True)
            emb_final.set_footer(text=f"Deployment ID: {g.id}")
            
            await completion_channel.send(embed=emb_final)
            log.info(f"Deployment complete: {duration:.2f}s - {cats} cats, {chans} chans, {len(role_map)} roles, {automod_count} automod rules")
            
        except Exception as e:
            state.error = str(e)
            log.error(f"Deployment failed: {e}\n{traceback.format_exc()}")
            
            try:
                emb_err = discord.Embed(
                    title="[FAILURE] DEPLOYMENT FAILED",
                    description=f"**Error:** `{str(e)[:500]}`",
                    color=0xE74C3C,
                    timestamp=datetime.now(timezone.utc)
                )
                emb_err.add_field(name="Phase", value=f"`{state.phase}`", inline=True)
                emb_err.add_field(name="Executor", value=f"{inter.user.mention}", inline=True)
                
                if prog_channel:
                    await prog_channel.send(embed=emb_err)
                else:
                    await inter.followup.send(embed=emb_err, ephemeral=True)
            except:
                pass
        finally:
            if g.id in bot.deployment_states:
                del bot.deployment_states[g.id]

@deploy.error
async def deploy_error(inter: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await inter.response.send_message("[ERROR] Administrator permission required", ephemeral=True)
    else:
        log.error(f"Command error: {error}\n{traceback.format_exc()}")

@bot.tree.command(name="lockdown", description="[ADMIN] Enable or disable server lockdown mode")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(enabled="Enable or disable lockdown")
async def lockdown(inter: discord.Interaction, enabled: bool) -> None:
    """Toggle server lockdown mode"""
    g = inter.guild
    if not g:
        await inter.response.send_message("[ERROR] Must be executed in a guild", ephemeral=True)
        return
    
    security_state = bot.security_states.get(g.id)
    if not security_state:
        security_state = SecurityState()
        bot.security_states[g.id] = security_state
    
    security_state.lockdown_active = enabled
    
    try:
        # Change verification level
        if enabled:
            await g.edit(verification_level=discord.VerificationLevel.highest)
            status = "ENABLED"
            color = 0xFF0000
        else:
            await g.edit(verification_level=discord.VerificationLevel.medium)
            status = "DISABLED"
            color = 0x2ECC71
        
        embed = discord.Embed(
            title=f"[{status}] Server Lockdown",
            description=f"**Status:** Lockdown {status.lower()}\n**Executor:** {inter.user.mention}",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        
        await inter.response.send_message(embed=embed)
        
        # Log to security
        log_channels = bot.log_channels.get(g.id, LogChannels())
        if log_channels.security_log:
            await log_channels.security_log.send(embed=embed)
        
        log.info(f"Lockdown {status} by {inter.user} in {g.name}")
        
    except Exception as e:
        await inter.response.send_message(f"[ERROR] Failed to change lockdown status: {e}", ephemeral=True)

@bot.tree.command(name="verify", description="[ADMIN] Comprehensive infrastructure health check and validation")
@app_commands.checks.has_permissions(administrator=True)
async def verify(inter: discord.Interaction) -> None:
    g = inter.guild
    if not g:
        await inter.response.send_message("[ERROR] Must be executed in a guild", ephemeral=True)
        return
    
    await inter.response.defer(ephemeral=True)
    
    expected_roles = {rd.name for rd in ROLES}
    current_roles = {r.name for r in g.roles if r.name != "@everyone" and not r.managed}
    missing_roles = list(expected_roles - current_roles)
    extra_roles = list(current_roles - expected_roles)
    
    expected_cats = {cd.name for cd in CATEGORIES}
    current_cats = {c.name for c in g.categories}
    missing_cats = list(expected_cats - current_cats)
    extra_cats = list(current_cats - expected_cats)
    
    expected_chans = {ch.name for ch in CHANNELS}
    current_chans = {c.name for c in g.channels if not isinstance(c, discord.CategoryChannel)}
    missing_chans = list(expected_chans - current_chans)
    extra_chans = list(current_chans - expected_chans)
    
    # Check AutoMod rules
    automod_rules = await g.fetch_automod_rules()
    automod_count = len(automod_rules)
    
    # Check security state
    security_state = bot.security_states.get(g.id)
    lockdown_status = security_state.lockdown_active if security_state else False
    pending_verifications = len(security_state.verification_pending) if security_state else 0
    
    total_issues = len(missing_roles) + len(missing_cats) + len(missing_chans)
    
    emb = discord.Embed(
        title="Infrastructure Health Report",
        description=f"**Server:** `{g.name}`\n**Verified:** <t:{int(datetime.now(timezone.utc).timestamp())}:F>",
        color=0x2ECC71 if total_issues == 0 else (0xE67E22 if total_issues < 5 else 0xE74C3C),
        timestamp=datetime.now(timezone.utc)
    )
    
    role_status = f"[OK] `{len(expected_roles)}` expected, `{len(current_roles)}` found"
    if missing_roles:
        role_status += f"\n[MISSING] {', '.join([f'`{r}`' for r in missing_roles[:5]])}"
        if len(missing_roles) > 5:
            role_status += f" +{len(missing_roles) - 5} more"
    if extra_roles:
        role_status += f"\n[EXTRA] {', '.join([f'`{r}`' for r in extra_roles[:5]])}"
        if len(extra_roles) > 5:
            role_status += f" +{len(extra_roles) - 5} more"
    emb.add_field(name="Roles", value=role_status, inline=False)
    
    cat_status = f"[OK] `{len(expected_cats)}` expected, `{len(current_cats)}` found"
    if missing_cats:
        cat_status += f"\n[MISSING] {', '.join([f'`{c}`' for c in missing_cats])}"
    if extra_cats:
        cat_status += f"\n[EXTRA] {', '.join([f'`{c}`' for c in extra_cats[:5]])}"
    emb.add_field(name="Categories", value=cat_status, inline=False)
    
    chan_status = f"[OK] `{len(expected_chans)}` expected, `{len(current_chans)}` found"
    if missing_chans:
        chan_status += f"\n[MISSING] {', '.join([f'`{c}`' for c in missing_chans[:10]])}"
        if len(missing_chans) > 10:
            chan_status += f" +{len(missing_chans) - 10} more"
    if extra_chans:
        chan_status += f"\n[EXTRA] {', '.join([f'`{c}`' for c in extra_chans[:10]])}"
        if len(extra_chans) > 10:
            chan_status += f" +{len(extra_chans) - 10} more"
    emb.add_field(name="Channels", value=chan_status, inline=False)
    
    # Security status
    security_status = f"AutoMod Rules: `{automod_count}`\n"
    security_status += f"Lockdown: `{'ACTIVE' if lockdown_status else 'INACTIVE'}`\n"
    security_status += f"Pending Verifications: `{pending_verifications}`"
    emb.add_field(name="Security Systems", value=security_status, inline=False)
    
    if total_issues == 0:
        health = "[PERFECT] Infrastructure is complete and healthy"
    elif total_issues < 5:
        health = f"[MINOR ISSUES] {total_issues} missing components"
    else:
        health = f"[CRITICAL] {total_issues} missing components, redeployment recommended"
    
    emb.add_field(name="Overall Health", value=health, inline=False)
    emb.set_footer(text=f"Guild ID: {g.id} | Latency: {bot.latency * 1000:.2f}ms")
    
    await inter.followup.send(embed=emb, ephemeral=True)
    log.info(f"Verification by {inter.user}: {total_issues} issues found in {g.name}")

@verify.error
async def verify_error(inter: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await inter.response.send_message("[ERROR] Administrator permission required", ephemeral=True)
    else:
        log.error(f"Verify error: {error}")

@bot.tree.command(name="warn", description="[MOD] Issue a warning to a user")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(user="User to warn", reason="Reason for warning")
async def warn(inter: discord.Interaction, user: discord.Member, reason: str) -> None:
    """Issue a warning to a user"""
    if user.bot:
        await inter.response.send_message("[ERROR] Cannot warn bots", ephemeral=True)
        return
    
    security_state = bot.security_states.get(inter.guild.id)
    if not security_state:
        security_state = SecurityState()
        bot.security_states[inter.guild.id] = security_state
    
    security_state.warning_counts[user.id] += 1
    warning_count = security_state.warning_counts[user.id]
    
    # Send DM to user
    try:
        await user.send(
            f"**[WARNING {warning_count}/{Config.MAX_WARNINGS}]** You have received a warning in {inter.guild.name}\n"
            f"**Reason:** {reason}\n"
            f"**Moderator:** {inter.user}\n\n"
            f"Please review the server rules. Further violations may result in a timeout or ban."
        )
    except:
        pass
    
    # Apply timeout if max warnings reached
    action_taken = None
    if warning_count >= Config.MAX_WARNINGS:
        timeout_duration = timedelta(seconds=Config.WARNING_MUTE_DURATION)
        await user.timeout(timeout_duration, reason=f"Exceeded warning limit: {reason}")
        security_state.warning_counts[user.id] = 0
        action_taken = f"Timed out for {Config.WARNING_MUTE_DURATION//60} minutes"
    
    embed = discord.Embed(
        title="Warning Issued",
        color=0xE67E22,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="User", value=f"{user.mention} (`{user.id}`)", inline=True)
    embed.add_field(name="Warnings", value=f"`{warning_count}/{Config.MAX_WARNINGS}`", inline=True)
    embed.add_field(name="Reason", value=f"`{reason}`", inline=False)
    embed.add_field(name="Moderator", value=inter.user.mention, inline=True)
    
    if action_taken:
        embed.add_field(name="Action Taken", value=action_taken, inline=False)
        embed.color = 0xFF0000
    
    await inter.response.send_message(embed=embed)
    
    # Log to mod logs
    log_channels = bot.log_channels.get(inter.guild.id, LogChannels())
    if log_channels.mod_log:
        await log_channels.mod_log.send(embed=embed)
    
    log.info(f"Warning issued to {user} by {inter.user}: {reason} ({warning_count}/{Config.MAX_WARNINGS})")

@warn.error
async def warn_error(inter: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await inter.response.send_message("[ERROR] Moderate members permission required", ephemeral=True)
    else:
        log.error(f"Warn error: {error}")

def main() -> int:
    try:
        token = get_token()
    except ValidationError as e:
        log.critical(f"Token validation failed: {e}")
        return ExitCode.MISSING_TOKEN
    
    try:
        bot.run(token, log_handler=None, reconnect=True)
        return ExitCode.SUCCESS
    except discord.LoginFailure:
        log.critical("Authentication failed: invalid token")
        return ExitCode.AUTH_FAILURE
    except KeyboardInterrupt:
        log.info("Shutdown requested by user")
        return ExitCode.SUCCESS
    except Exception as e:
        log.critical(f"Fatal error: {e}\n{traceback.format_exc()}")
        return ExitCode.FATAL_ERROR

if __name__ == "__main__":
    sys.exit(main())
