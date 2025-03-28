#!/usr/bin/env python3

import os
import logging

# Konfigurieren Sie das Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('config')

# Token aus Umgebungsvariable holen
# Wenn kein Token gefunden wird, kann es direkt hier angegeben werden (für lokale Entwicklung)
# WICHTIG: Geben Sie niemals Ihr Token in produktivem Code an!
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Access environment variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    logger.warning("DISCORD_BOT_TOKEN not found in environment variables")
    # Auskommentieren und Ihr Token hier für lokale Tests einfügen:
    # TOKEN = "your-token-here"

# Bot-Konfiguration
COMMAND_PREFIX = "!"  # Präfix für Legacy-Befehle
ORGANIZER_ROLE = "Orga-Team"  # Rolle für Organisatoren
CLAN_REP_ROLE = "Clan-Rep"  # Rolle für Clan-Repräsentanten

# Datei für die Pickle-Datenspeicherung (für die Legacy Bot-Version)
SAVE_FILE = "event_data.pkl"

# Event-Konfiguration
DEFAULT_MAX_SLOTS = 96  # Maximale Anzahl der Teilnehmer pro Event
DEFAULT_MAX_TEAM_SIZE = 9  # Maximale Größe eines Teams
EXPANDED_MAX_TEAM_SIZE = 18  # Erhöhte maximale Teamgröße nach /open_reg
WAITLIST_CHECK_INTERVAL = 60  # Überprüfungsintervall der Warteliste in Sekunden

# Admin-Konfiguration - IDs der Administratoren für DM-Kontexte
# Fügen Sie hier die IDs der Discord-Benutzer ein, die Admin-Rechte in DMs haben sollen
ADMIN_IDS = [
    # Beispiel: "123456789012345678" - Dies ist eine Discord-Benutzer-ID
]

# Entwicklungsumgebung für lokale Tests
DEBUG_MODE = os.environ.get('DEBUG_MODE', 'False').lower() == 'true'

# Kanal für Logs
LOG_CHANNEL_NAME = "log"  # Name des Kanals für Logs
LOG_CHANNEL_ID = None  # Wird zur Laufzeit gesetzt