# Einrichtung des CoC-Event-Registration Discord Bots

Diese Anleitung hilft dir bei der Einrichtung des CoC-Event-Registration Discord Bots.

## Voraussetzungen

- Python 3.8 oder höher
- Discord Bot Token (erstellt über das [Discord Developer Portal](https://discord.com/developers/applications))
- Discord Server mit Administrator-Berechtigungen

## Installations-Schritte

### 1. Repository klonen

```bash
git clone https://github.com/FVollbrecht/CoC-Event-Registration.git
cd CoC-Event-Registration
```

### 2. Virtuelle Umgebung erstellen (empfohlen)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Abhängigkeiten installieren

```bash
# Erforderliche Pakete
pip install discord.py>=2.0.0 python-dotenv>=0.19.2 aiohttp>=3.8.1

# Optional für Voice-Support (nicht notwendig für die Kernfunktionalität)
pip install pynacl>=1.5.0
```

### 4. Umgebungsvariablen einrichten

Erstelle eine Datei `.env` im Hauptverzeichnis mit folgendem Inhalt:

```
DISCORD_TOKEN=dein_bot_token
ORGANIZER_ROLE=Organizer
CLAN_REP_ROLE=Clan Rep
LOG_CHANNEL=log
```

Ersetze `dein_bot_token` mit deinem eigenen Discord Bot Token.

### 5. Datenstruktur initialisieren

```bash
# Initialisiere die Datenstruktur
python initialize_data.py
```

### 6. Bot starten

```bash
python bot.py
```

## Konfiguration auf dem Discord-Server

1. **Rollen einrichten:**
   - Erstelle eine Rolle `Organizer` für Administratoren
   - Erstelle eine Rolle `Clan Rep` für Teamleiter

2. **Kanäle einrichten:**
   - Erstelle einen Textkanal `registration` für die Hauptfunktionalität
   - Erstelle einen Textkanal `log` für das Logging

3. **Bot-Berechtigungen:**
   - Stelle sicher, dass der Bot Nachrichten lesen und schreiben, Reaktionen hinzufügen, Dateien anhängen und Einbettungen senden darf

## Testen der Installation

Nach dem Start des Bots kannst du die folgenden Befehle testen:

1. `/sync_commands` - Synchronisiert die Slash-Commands mit der Discord API
2. `/help` - Zeigt die Hilfe an
3. `/create_event` - Erstellt ein Testevent

## Fehlerbehebung

- **Bot startet nicht**: Überprüfe, ob das Token korrekt ist und der Bot die richtigen Intents hat
- **Slash-Commands werden nicht angezeigt**: Führe `/sync_commands` aus oder überprüfe die Bot-Berechtigungen
- **Datenbank-Fehler**: Stelle sicher, dass `event_data.pkl` existiert und schreibbar ist

Weitere Fehlerbehebungstipps findest du in der README.md