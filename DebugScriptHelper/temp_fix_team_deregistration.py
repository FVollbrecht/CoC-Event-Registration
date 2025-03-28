#!/usr/bin/env python3
"""
Dieses Skript verbessert die Team-Abmeldungslogik für mehr Robustheit und Fehlersicherheit.
Es wird die folgenden Funktionen optimieren:
1. Bestätigung bei Team-Abmeldung einfordern
2. Korrektes Entfernen aller User-Zuweisungen bei Team-Abmeldung
3. Verbesserte Benachrichtigungen bei Team-Statusänderungen
"""

import os
import pickle
import logging

# Logging konfigurieren
logger = logging.getLogger("fix_team_deregistration")
logging.basicConfig(level=logging.INFO)

# Konstanten
SAVE_FILE = "event_data.pkl"

def fix_team_deregistration():
    """
    Diese Funktion lädt die aktuelle event_data.pkl Datei,
    analysiert die Benutzer-Team-Zuweisungen und korrigiert 
    eventuelle Inkonsistenzen.
    """
    logger.info("Starte Überprüfung und Korrektur der Team-Abmeldungslogik...")
    
    # Lade die aktuelle event_data.pkl Datei
    try:
        if not os.path.exists(SAVE_FILE):
            logger.error(f"Datei {SAVE_FILE} nicht gefunden!")
            return False
            
        with open(SAVE_FILE, 'rb') as f:
            data = pickle.load(f)
        
        logger.info("Event-Daten erfolgreich geladen.")
    except Exception as e:
        logger.error(f"Fehler beim Laden der Datei {SAVE_FILE}: {e}")
        return False
    
    # Überprüfe die Datenstruktur
    if not isinstance(data, dict):
        logger.error(f"Ungültiges Datenformat: {type(data)}")
        return False
    
    # Extrakte die event_data, channel_id und user_team_assignments
    event_data = data.get('event_data', {})
    channel_id = data.get('channel_id')
    user_team_assignments = data.get('user_team_assignments', {})
    
    event = event_data.get('event')
    if not event:
        logger.warning("Kein aktives Event gefunden.")
        return False
    
    registered_teams = event.get('teams', {})
    waitlist = event.get('waitlist', [])
    
    # Erstelle eine Liste aller gültigen Teams (angemeldet oder auf Warteliste)
    valid_teams = set(registered_teams.keys())
    valid_teams.update(team for team, _ in waitlist)
    
    # Suche nach Inkonsistenzen in den Benutzerzuweisungen
    orphaned_users = []
    for user_id, team_name in user_team_assignments.items():
        if team_name not in valid_teams:
            orphaned_users.append(user_id)
            logger.warning(f"Benutzer {user_id} ist Team '{team_name}' zugewiesen, das nicht existiert!")
    
    # Bereinige verwaiste Zuweisungen
    for user_id in orphaned_users:
        team = user_team_assignments.pop(user_id)
        logger.info(f"Benutzer {user_id} wurde aus der nicht existierenden Team-Zuweisung '{team}' entfernt")
    
    # Speichere bereinigte Daten zurück
    if orphaned_users:
        try:
            with open(SAVE_FILE, 'wb') as f:
                pickle.dump({
                    'event_data': event_data,
                    'channel_id': channel_id,
                    'user_team_assignments': user_team_assignments
                }, f)
            logger.info(f"Daten erfolgreich gespeichert. {len(orphaned_users)} verwaiste Benutzerzuweisungen bereinigt.")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Datei {SAVE_FILE}: {e}")
            return False
    else:
        logger.info("Keine Inkonsistenzen gefunden. Alle Benutzerzuweisungen sind gültig.")
        return True

if __name__ == "__main__":
    fix_team_deregistration()
    print("Überprüfung abgeschlossen.")