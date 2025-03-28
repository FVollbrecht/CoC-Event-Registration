# CoC-Event-Registration Discord Bot

Ein fortschrittlicher Discord-Bot für die Verwaltung von Events mit umfassenden Funktionen für Teamregistrierung, Wartelisten-Management und administrative Aufgaben.

![Discord Bot](https://img.shields.io/badge/Discord-Bot-7289DA?style=for-the-badge&logo=discord)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Discord.py](https://img.shields.io/badge/Discord.py-2.0+-7289DA?style=for-the-badge&logo=discord&logoColor=white)

## Eigenschaften

- **Event-Management**: Erstellen, Anzeigen und Verwalten von Events mit detaillierten Informationen
- **Team-Registration**: Einfache Anmeldung und Verwaltung von Teams für Events
- **Automatische Warteliste**: Intelligente Verwaltung von Wartelisten, wenn ein Event ausgebucht ist
- **Admin-Befehle**: Umfangreiche administrative Möglichkeiten zur vollständigen Kontrolle des Events
- **Interaktive Benutzeroberfläche**: Moderne Discord UI-Komponenten (Buttons, Select-Menüs, Modals)
- **Robustes Logging**: Detailliertes Logging aller Aktivitäten für Nachvollziehbarkeit und Problemdiagnose
- **Team-ID-System**: Eindeutige Identifikatoren für Teams zur besseren Verwaltung
- **Auto-Nachrücken**: Automatisches Nachrücken von der Warteliste, wenn Plätze frei werden
- **Format-Erkennung**: Intelligente Erkennung und Unterstützung verschiedener Datenformate
- **Mehrsprachige Unterstützung**: Vorbereitet für mehrsprachige Implementierung

## Installation

### Voraussetzungen

- Python 3.8 oder höher
- Discord Bot Token
- Discord Server mit entsprechenden Berechtigungen

### Setup

1. Repository klonen:
   ```bash
   git clone https://github.com/FVollbrecht/CoC-Event-Registration.git
   cd CoC-Event-Registration
   ```

2. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```

3. Einrichtung der Umgebungsvariablen in `.env`:
   ```
   DISCORD_TOKEN=dein_bot_token
   ORGANIZER_ROLE=Organizer
   CLAN_REP_ROLE=Clan Rep
   LOG_CHANNEL=log
   ```

4. Bot starten:
   ```bash
   python bot.py
   ```

## Verwendung

### Event-Management Befehle

- `/create_event` - Erstellt ein neues Event mit Details wie Name, Datum, Zeit und Beschreibung
- `/delete_event` - Löscht das aktuelle Event (nur Admin)
- `/show_event` - Zeigt das aktuelle Event mit interaktiven Buttons an
- `/update` - Aktualisiert die Event-Details im Kanal
- `/open` - Öffnet die Anmeldungen für das Event wieder (nach Schließung)
- `/close` - Schließt die Anmeldungen für das Event

### Team-Management

- `/register_team` - Registriert ein Team oder aktualisiert die Teamgröße
- `/edit` - Bearbeitet die Größe des eigenen Teams über ein Modal
- `/unregister` - Meldet das eigene Team vom Event ab
- `/team_list` - Zeigt eine formatierte Liste aller registrierten Teams

### Admin-Befehle

- `/admin_team_edit` - Bearbeitet die Größe eines Teams (Admin-Befehl)
- `/admin_team_remove` - Entfernt ein Team vom Event oder der Warteliste
- `/admin_add_team` - Fügt ein Team direkt zum Event oder zur Warteliste hinzu
- `/admin_waitlist` - Zeigt die vollständige Warteliste mit Details an
- `/admin_user_assignments` - Zeigt alle Benutzer-Team-Zuweisungen an
- `/admin_get_user_id` - Gibt die Discord ID eines Benutzers zurück
- `/reset_team_assignment` - Setzt die Teamzuweisung eines Benutzers zurück
- `/export_teams` - Exportiert alle Teams als CSV-Datei

### Utility-Befehle

- `/help` - Zeigt Hilfe-Informationen an
- `/admin_help` - Zeigt Hilfe zu den verfügbaren Admin-Befehlen
- `/export_log` - Exportiert die Log-Datei
- `/clear_log` - Löscht den Inhalt der Log-Datei
- `/import_log` - Importiert eine Log-Datei
- `/sync_commands` - Synchronisiert die Slash-Commands mit der Discord API
- `/find` - Findet ein Team oder einen Spieler im Event

## Architektur

Der Bot verwendet eine modulare Architektur mit diesen Hauptkomponenten:

- **Bot-Klasse**: `EventBot` - Die Hauptklasse für den Discord-Bot
- **Datenmanagement**: Verwendet Pickle für persistente Datenspeicherung
- **UI-Komponenten**: Verschiedene Klassen für Discord UI-Elemente
- **Utilities**: Hilfsfunktionen für Log-Management, Team-IDs und mehr
- **Validierung**: Funktionen zur Validierung von Benutzereingaben
- **Event-Anzeige**: Funktionen zum Formatieren und Anzeigen von Event-Details

### Datenstruktur

Die Event-Daten werden in folgender Struktur gespeichert:

```python
{
    "name": "Event-Name",
    "date": "Event-Datum",
    "time": "Event-Zeit",
    "description": "Event-Beschreibung",
    "max_slots": 100,  # Maximale Teilnehmerzahl
    "slots_used": 0,   # Aktuell belegte Plätze
    "max_team_size": 10,  # Maximale Teamgröße
    "teams": {
        "Team1": {"size": 5, "id": "abcd1234"},  # Neues Format mit Team-IDs
        "Team2": {"size": 8, "id": "efgh5678"}
    },
    "registration_open": True,  # Ob Anmeldungen möglich sind
    "waitlist": [
        ("WaitTeam1", 5, "ijkl9012"),  # Format: (name, size, id)
        ("WaitTeam2", 3, "mnop3456")
    ],
    "created_at": "2025-03-28 09:00:00",
    "last_updated": "2025-03-28 10:00:00"
}
```

## Erweiterungsmöglichkeiten

- **Web-Interface**: Entwicklung eines Web-Dashboards zur Event-Verwaltung
- **Datenbankintegration**: Migration von Pickle zu einer relationalen Datenbank
- **Multi-Event-Unterstützung**: Verwaltung mehrerer gleichzeitiger Events
- **API-Integration**: Anbindung an externe APIs (z.B. für Spielstatistiken)
- **Turnier-Management**: Erweiterung für die Verwaltung von Turnieren mit Brackets
- **Automatisierte Erinnerungen**: Automatisches Senden von Erinnerungen vor Events

## Fehlerbehebung

### Häufige Probleme

- **Bot antwortet nicht**: Überprüfen Sie, ob der Bot online ist und die richtigen Berechtigungen hat
- **Befehle werden nicht angezeigt**: Führen Sie `/sync_commands` aus, um die Slash-Commands zu synchronisieren
- **Team kann nicht angemeldet werden**: Prüfen Sie, ob das Event bereits voll ist oder die Anmeldungen geschlossen sind
- **Wartelisten-Probleme**: Nutzen Sie `/admin_waitlist`, um die Warteliste zu inspizieren

### Logging

Der Bot verfügt über umfangreiche Logging-Funktionen:

- Logs werden in `discord_bot.log` gespeichert
- Wichtige Ereignisse werden zusätzlich im Discord-Kanal `log` dokumentiert
- Backup-Logs werden im Ordner `log_backups` aufbewahrt

## Beitrag zum Projekt

Beiträge sind willkommen! Hier sind einige Möglichkeiten, wie Sie zum Projekt beitragen können:

1. Fehler melden: Erstellen Sie ein Issue im GitHub-Repository
2. Funktionen vorschlagen: Teilen Sie Ihre Ideen über Issues mit
3. Code beitragen: Reichen Sie Pull Requests ein
4. Dokumentation verbessern: Ergänzen Sie die README oder erstellen Sie Wiki-Seiten

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe die [LICENSE](LICENSE)-Datei für Details.

## Kontakt

Für Fragen, Vorschläge oder Support kontaktieren Sie uns über GitHub Issues oder Discord.

---

Entwickelt mit ❤️ für die CoC-Community