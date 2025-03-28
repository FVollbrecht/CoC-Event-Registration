#!/usr/bin/env python3

import pickle
import os
import logging
import asyncio
import threading
import shutil
from datetime import datetime
import discord
from discord import Embed
import io

# Discord log channel handler
discord_log_channel = None

# Erstelle einen benutzerdefinierten Log-Handler für Discord
class DiscordLogHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.log_messages = []
        self.log_lock = threading.Lock()

    def emit(self, record):
        # Formatiere die Log-Nachricht
        msg = self.format(record)
        # Füge sie der Liste hinzu (Thread-sicher)
        with self.log_lock:
            self.log_messages.append((record.levelname, msg))
    
    def get_logs(self, max_count=5):
        with self.log_lock:
            # Kopiere bis zu max_count Nachrichten aus der Liste
            result = self.log_messages[:max_count]
            # Entferne die kopierten Nachrichten aus der Liste
            self.log_messages = self.log_messages[len(result):]
            return result

# Erstelle einen globalen Handler, der später initialisiert wird
discord_handler = DiscordLogHandler()
discord_handler.setLevel(logging.INFO)
discord_handler.setFormatter(logging.Formatter('%(message)s'))

# Setup logging
# Sicherstellen, dass die Datei existiert und beschreibbar ist
try:
    with open("discord_bot.log", "a") as f:
        f.write(f"--- Log Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
except Exception as e:
    print(f"Fehler beim Zugriff auf Log-Datei: {e}")

# Konfiguriere das Root-Logger für alle Module
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Formatierung für alle Log-Handler
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Handler für Konsole
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
root_logger.addHandler(console_handler)

# Handler für Datei
try:
    file_handler = logging.FileHandler("discord_bot.log", mode='a')
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
except Exception as e:
    print(f"Fehler beim Erstellen des File-Handlers: {e}")

# Füge den Discord-Handler zum Root-Logger hinzu
discord_handler.setFormatter(log_format)
root_logger.addHandler(discord_handler)

# Erstelle den event_bot-Logger als Kind des Root-Loggers
logger = logging.getLogger("event_bot")
logger.info("Logger initialisiert")

async def send_to_log_channel(message, level="INFO", guild=None):
    """
    Sendet eine Nachricht an den Log-Kanal
    
    Parameters:
    - message: Die zu sendende Nachricht
    - level: Der Log-Level (INFO, WARNING, ERROR, etc.)
    - guild: Die Guild, in der der Log-Kanal gesucht werden soll (optional)
    
    Returns:
    - True bei Erfolg, False bei Fehler
    """
    from config import LOG_CHANNEL_NAME, LOG_CHANNEL_ID
    global discord_log_channel
    
    # Log zuerst in die normale Logdatei
    if level == "INFO":
        logger.info(message)
    elif level == "WARNING":
        logger.warning(message)
    elif level == "ERROR":
        logger.error(message)
    elif level == "CRITICAL":
        logger.critical(message)
    else:
        logger.info(message)
    
    try:
        bot = get_bot()
        if not bot:
            return False
        
        # Wenn der Log-Kanal noch nicht gefunden wurde, versuche ihn zu finden
        if not discord_log_channel and (guild or LOG_CHANNEL_ID):
            if LOG_CHANNEL_ID:
                # Versuche, den Kanal über die ID zu finden
                discord_log_channel = bot.get_channel(LOG_CHANNEL_ID)
            elif guild:
                # Suche im angegebenen Guild nach dem Kanal
                discord_log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        
        # Versuche, die Nachricht zu senden, wenn der Kanal verfügbar ist
        if discord_log_channel:
            # Formatiere die Nachricht je nach Log-Level
            if level == "INFO":
                formatted_message = f"ℹ️ **INFO**: {message}"
            elif level == "WARNING":
                formatted_message = f"⚠️ **WARNUNG**: {message}"
            elif level == "ERROR":
                formatted_message = f"❌ **FEHLER**: {message}"
            elif level == "CRITICAL":
                formatted_message = f"🚨 **KRITISCH**: {message}"
            else:
                formatted_message = f"ℹ️ {message}"
            
            await discord_log_channel.send(formatted_message)
            return True
    except Exception as e:
        logger.error(f"Fehler beim Senden der Nachricht an den Log-Kanal: {e}")
    
    return False

def get_bot():
    """
    Hilfsfunktion, um eine Referenz auf das Bot-Objekt zu bekommen
    """
    try:
        import sys
        import bot
        return bot.bot if hasattr(bot, 'bot') else None
    except (ImportError, AttributeError) as e:
        logger.error(f"Kann Bot-Objekt nicht abrufen: {e}")
        return None

# Constants
SAVE_FILE = "event_data.pkl"

def load_data():
    """Load event data from pickle file"""
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'rb') as f:
                data = pickle.load(f)
                logger.info(f"Data loaded from {SAVE_FILE}")
                return data.get('event_data', {}), data.get('channel_id'), data.get('user_team_assignments', {})
        else:
            logger.info("No save file found, starting with empty data")
            return {}, None, {}
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return {}, None, {}

def save_data(event_data, channel_id, user_team_assignments):
    """Save event data to pickle file"""
    try:
        data = {
            'event_data': event_data,
            'channel_id': channel_id,
            'user_team_assignments': user_team_assignments
        }
        with open(SAVE_FILE, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Data saved to {SAVE_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return False

def generate_team_id(team_name):
    """Generiert eine eindeutige ID für ein Team
    
    Parameters:
    - team_name: Der Name des Teams
    
    Returns:
    - Eine eindeutige ID für das Team (basierend auf Namen und Timestamp)
    """
    import hashlib
    import time
    
    # Kombiniere Team-Namen mit aktuellem Timestamp für Eindeutigkeit
    unique_base = f"{team_name}_{int(time.time())}"
    # Erstelle einen Hash für diesen String
    team_hash = hashlib.md5(unique_base.encode('utf-8')).hexdigest()
    # Verwende nur die ersten 10 Zeichen für eine kürzere ID
    short_id = team_hash[:10]
    
    logger.debug(f"Team-ID generiert: {short_id} für Team '{team_name}'")
    return short_id

def has_role(user, role_name):
    """Check if a user has a specific role or is in the ADMIN_IDS list
    
    Parameters:
    - user: Discord user or member object
    - role_name: The role name to check for
    
    Returns:
    - True if user has the role or is in ADMIN_IDS
    - False otherwise
    """
    from config import ADMIN_IDS
    
    try:
        # Wenn der Benutzer in ADMIN_IDS ist, immer True zurückgeben
        if hasattr(user, 'id') and str(user.id) in ADMIN_IDS:
            return True
            
        # Bei DMs ist user ein User-Objekt und kein Member-Objekt
        if not hasattr(user, 'roles'):
            # In DMs erlauben wir keine Rollenprüfung, außer für Admins (oben geprüft)
            return False
            
        # Normale Rollenprüfung für Server-Kontexte
        return any(role.name == role_name for role in user.roles)
    except Exception as e:
        logger.error(f"Error checking roles: {e}")
        return False

def parse_date(date_str):
    """Parse date string in format DD.MM.YYYY"""
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        return None

def format_event_details(event):
    """Format event details as Discord embed"""
    if not event:
        return "Kein aktives Event."
    
    # Prüfen, ob es ein echtes Event mit Inhalt ist
    if not event.get('name') or not event.get('date'):
        return "Kein aktives Event."
        
    embed = Embed(
        title=f"📅 Event: {event['name']}",
        description=event.get('description', 'Keine Beschreibung verfügbar'),
        color=discord.Color.blue()
    )
    
    # Add event details
    embed.add_field(name="📆 Datum", value=event['date'], inline=True)
    embed.add_field(name="⏰ Uhrzeit", value=event.get('time', 'keine Angabe'), inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer for alignment
    
    # Add team registration info
    embed.add_field(
        name="👥 Team-Anmeldungen",
        value=f"{event['slots_used']}/{event['max_slots']} Plätze belegt",
        inline=True
    )
    embed.add_field(
        name="🔢 Max. Teamgröße",
        value=str(event['max_team_size']),
        inline=True
    )
    embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer for alignment
    
    # Add registered teams
    teams_text = ""
    if event['teams']:
        for team_name, size in event['teams'].items():
            teams_text += f"• **{team_name}**: {size} {'Person' if size == 1 else 'Personen'}\n"
    else:
        teams_text = "Noch keine Teams angemeldet."
    
    embed.add_field(
        name=f"📋 Angemeldete Teams ({len(event['teams'])})",
        value=teams_text or "Keine Teams angemeldet",
        inline=False
    )
    
    # Add waitlist if exists
    if event['waitlist']:
        waitlist_text = ""
        for i, (team_name, size) in enumerate(event['waitlist']):
            waitlist_text += f"{i+1}. **{team_name}**: {size} {'Person' if size == 1 else 'Personen'}\n"
        
        embed.add_field(
            name=f"⏳ Warteliste ({len(event['waitlist'])})",
            value=waitlist_text,
            inline=False
        )
    
    # Add footer with instructions
    embed.set_footer(text="Verwende /reg um dein Team anzumelden oder /wl für die Warteliste.")
    
    return embed

def format_event_list(event):
    """Format event as plain text (fallback)"""
    if not event:
        return "Kein aktives Event."
    
    # Prüfen, ob es ein echtes Event mit Inhalt ist
    if not event.get('name') or not event.get('date'):
        return "Kein aktives Event."
    
    text = f"**📅 Event: {event['name']}**\n"
    text += f"📆 Datum: {event['date']}\n"
    text += f"⏰ Uhrzeit: {event.get('time', 'keine Angabe')}\n"
    text += f"📝 Beschreibung: {event.get('description', 'Keine Beschreibung verfügbar')}\n\n"
    
    text += f"👥 Team-Anmeldungen: {event['slots_used']}/{event['max_slots']} Plätze belegt\n"
    text += f"🔢 Max. Teamgröße: {event['max_team_size']}\n\n"
    
    text += f"📋 Angemeldete Teams ({len(event['teams'])}):\n"
    if event['teams']:
        for team_name, size in event['teams'].items():
            text += f"• {team_name}: {size} {'Person' if size == 1 else 'Personen'}\n"
    else:
        text += "Noch keine Teams angemeldet.\n"
    
    if event['waitlist']:
        text += f"\n⏳ Warteliste ({len(event['waitlist'])}):\n"
        for i, (team_name, size) in enumerate(event['waitlist']):
            text += f"{i+1}. {team_name}: {size} {'Person' if size == 1 else 'Personen'}\n"
    
    return text

# Konstanten für Log-Verwaltung
LOG_FILE_PATH = "discord_bot.log"
LOG_BACKUP_FOLDER = "log_backups"

def export_log_file():
    """Exportiert die aktuelle Log-Datei.
    
    Returns:
    - Pfad zur exportierten Log-Datei oder None bei Fehler
    """
    try:
        # Prüfen, ob die Log-Datei existiert
        if not os.path.exists(LOG_FILE_PATH):
            logger.error(f"Log-Datei {LOG_FILE_PATH} existiert nicht!")
            return None
        
        # Einen Buffer für den Log-Inhalt erstellen
        log_buffer = io.BytesIO()
        
        # Die Log-Datei ins Byte-Format kopieren
        with open(LOG_FILE_PATH, 'rb') as f:
            log_buffer.write(f.read())
        
        # Zeiger an den Anfang des Buffers setzen
        log_buffer.seek(0)
        
        # Zeitstempel für den Dateinamen
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        export_filename = f"log_export_{timestamp}.log"
        
        logger.info(f"Log-Datei erfolgreich exportiert: {export_filename}")
        
        return {
            'buffer': log_buffer,
            'filename': export_filename
        }
    
    except Exception as e:
        logger.error(f"Fehler beim Exportieren der Log-Datei: {e}")
        return None

def clear_log_file():
    """Löscht den Inhalt der Log-Datei, erstellt aber vorher ein Backup.
    
    Returns:
    - True bei Erfolg, False bei Fehler
    """
    try:
        # Prüfen, ob die Log-Datei existiert
        if not os.path.exists(LOG_FILE_PATH):
            logger.error(f"Log-Datei {LOG_FILE_PATH} existiert nicht!")
            return False
        
        # Backup-Ordner erstellen, falls nicht vorhanden
        if not os.path.exists(LOG_BACKUP_FOLDER):
            os.makedirs(LOG_BACKUP_FOLDER)
        
        # Zeitstempel für den Backup-Dateinamen
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"{LOG_BACKUP_FOLDER}/log_backup_{timestamp}.log"
        
        # Backup erstellen
        shutil.copy2(LOG_FILE_PATH, backup_filename)
        
        # Log-Datei leeren
        with open(LOG_FILE_PATH, 'w') as f:
            f.write(f"--- Log neu gestartet: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        
        logger.info(f"Log-Datei gelöscht und Backup erstellt: {backup_filename}")
        return True
    
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Log-Datei: {e}")
        return False

def import_log_file(file_content, append=True):
    """Importiert den Inhalt einer Log-Datei.
    
    Parameters:
    - file_content: Inhalt der zu importierenden Log-Datei (Bytes)
    - append: Ob der Inhalt an die bestehende Log-Datei angehängt werden soll (True)
              oder die bestehende überschrieben werden soll (False)
    
    Returns:
    - True bei Erfolg, False bei Fehler
    """
    try:
        # Modus basierend auf append-Parameter
        mode = 'a' if append else 'w'
        
        # Backup der aktuellen Log-Datei erstellen, falls sie überschrieben werden soll
        if not append and os.path.exists(LOG_FILE_PATH):
            # Backup-Ordner erstellen, falls nicht vorhanden
            if not os.path.exists(LOG_BACKUP_FOLDER):
                os.makedirs(LOG_BACKUP_FOLDER)
            
            # Zeitstempel für den Backup-Dateinamen
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename = f"{LOG_BACKUP_FOLDER}/log_backup_before_import_{timestamp}.log"
            
            # Backup erstellen
            shutil.copy2(LOG_FILE_PATH, backup_filename)
            logger.info(f"Backup vor Import erstellt: {backup_filename}")
        
        # Inhalt in die Log-Datei schreiben
        with open(LOG_FILE_PATH, mode) as f:
            if mode == 'w':
                # Neue Dateien beginnen mit einer Startmeldung
                f.write(f"--- Importierte Log-Datei: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            else:
                # Beim Anhängen eine Trennlinie einfügen
                f.write(f"\n--- Beginn importierter Logs: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            
            # Inhalt als Text konvertieren, falls er als Bytes vorliegt
            if isinstance(file_content, bytes):
                text_content = file_content.decode('utf-8', errors='replace')
            else:
                text_content = file_content
                
            f.write(text_content)
            
            if mode == 'a':
                # Beim Anhängen eine Endmarkierung einfügen
                f.write(f"\n--- Ende importierter Logs: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        
        logger.info("Log-Datei erfolgreich importiert")
        return True
    
    except Exception as e:
        logger.error(f"Fehler beim Importieren der Log-Datei: {e}")
        return False


# Hilfsfunktionen zur Formaterkennung

def is_using_team_ids(event):
    """
    Prüft, ob das Team-Dictionary das erweiterte Format mit IDs verwendet
    
    Parameters:
    - event: Das Event-Dictionary
    
    Returns:
    - True, wenn Team-IDs verwendet werden, False sonst
    """
    if not event or not event.get("teams") or not isinstance(event["teams"], dict) or len(event["teams"]) == 0:
        return False
    
    # Prüfe das Format der Team-Daten
    return isinstance(next(iter(event["teams"].values())), dict)

def is_using_waitlist_ids(event):
    """
    Prüft, ob die Warteliste das erweiterte Format mit IDs verwendet
    
    Parameters:
    - event: Das Event-Dictionary
    
    Returns:
    - True, wenn Waitlist-IDs verwendet werden, False sonst
    """
    if not event or not event.get("waitlist") or not isinstance(event["waitlist"], list) or len(event["waitlist"]) == 0:
        return False
    
    # Prüfe das Format der Wartelisten-Einträge
    return len(event["waitlist"][0]) > 2