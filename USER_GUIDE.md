# CoC-Event-Registration Bot - Benutzerhandbuch

Dieses Handbuch erklärt, wie du den CoC-Event-Registration Discord Bot verwenden kannst.

## Inhaltsverzeichnis

- [Organisatoren-Befehle](#organisatoren-befehle)
- [Clan-Leiter-Befehle](#clan-leiter-befehle)
- [Allgemeine Befehle](#allgemeine-befehle)
- [Interaktive UI-Elemente](#interaktive-ui-elemente)
- [Workflow-Beispiele](#workflow-beispiele)
- [Wartelisten-System](#wartelisten-system)
- [Log-Management](#log-management)
- [Häufig gestellte Fragen](#häufig-gestellte-fragen)

## Organisatoren-Befehle

Als Organisator (mit der Rolle `Organizer`) hast du Zugriff auf folgende Befehle:

### Event-Verwaltung

- `/create_event name:Event-Name date:YYYY-MM-DD time:HH:MM description:Beschreibung` - Erstellt ein neues Event mit Standardwerten für CoC, aktuelles Datum und 20:00 Uhr
- `/delete_event` - Löscht das aktuelle Event mit Bestätigungsdialog
- `/open_registration` - Passt die maximale Teamgröße an (erhöht von 9 auf 18 oder entfernt das Limit)
- `/close` - Schließt die Anmeldungen für das Event (keine neuen Teams können sich anmelden)
- `/open` - Öffnet die Anmeldungen für das Event wieder nach einer Schließung

### Team-Verwaltung

- `/admin_add_team team_name:Name size:5 discord_id:Optional discord_name:Optional force_waitlist:False` - Fügt ein Team direkt hinzu
- `/admin_team_edit team_name:Name new_size:7 reason:Optional` - Ändert die Größe eines Teams mit optionalem Grund
- `/admin_team_remove team_name:Name` - Entfernt ein Team vom Event oder der Warteliste
- `/reset_team_assignment user:@Username` - Setzt die Teamzuweisung eines Nutzers zurück

### Informationen und Export

- `/admin_waitlist` - Zeigt die vollständige Warteliste mit Details an
- `/admin_user_assignments` - Zeigt alle Benutzer-Team-Zuweisungen an
- `/admin_get_user_id user:@Username` - Gibt die Discord ID eines Benutzers zurück
- `/export_teams` - Exportiert alle Teams als CSV-Datei
- `/admin_help` - Zeigt alle Admin-Befehle an

### System-Verwaltung

- `/sync_commands clear_cache:False` - Synchronisiert die Slash-Commands mit der Discord API
- `/export_log` - Exportiert die Log-Datei für Fehleranalyse
- `/clear_log` - Löscht den Inhalt der Log-Datei mit Bestätigungsdialog
- `/import_log append:True` - Importiert eine Log-Datei
- `/clear_messages count:5 reason:Optional` - Löscht die angegebene Anzahl der letzten Nachrichten im Kanal (neu!)

## Clan-Leiter-Befehle

Als Clan-Leiter (mit der Rolle `Clan Rep`) hast du Zugriff auf folgende Befehle:

### Team-Verwaltung

- `/register_team team_name:Name size:5` - Registriert dein Team oder aktualisiert die Teamgröße
- `/edit` - Öffnet ein Modal zum Bearbeiten der Teamgröße
- `/unregister team_name:Optional` - Meldet dein Team vom Event ab mit Bestätigungsdialog

## Allgemeine Befehle

Diese Befehle sind für alle Nutzer verfügbar:

- `/show_event` - Zeigt das aktuelle Event mit interaktiven Buttons an
- `/team_list` - Zeigt eine formatierte Liste aller registrierten Teams
- `/find search_term:Suchbegriff` - Findet ein Team oder einen Spieler im Event
- `/help` - Zeigt Hilfe-Informationen an mit Bestätigungsdialog
- `/update` - Aktualisiert die Event-Details im Kanal

## Interaktive UI-Elemente

Der Bot bietet moderne Discord UI-Komponenten für eine bessere Benutzerinteraktion:

### Event-Anzeige Buttons

- **Team anmelden** - Öffnet ein Formular zur Anmeldung deines Teams
- **Team abmelden** - Startet den Prozess zur Abmeldung deines Teams
- **Team-Info** - Zeigt Informationen zu deinem angemeldeten Team
- **Team bearbeiten** - Öffnet ein Formular zum Ändern der Teamgröße
- **Admin** - Zeigt Admin-Optionen für Organisatoren

### Bestätigungsdialoge

Für kritische Aktionen werden Bestätigungsdialoge angezeigt:
- **Team-Abmeldung** - Bestätigung vor der Abmeldung eines Teams
- **Event-Löschung** - Bestätigung vor dem Löschen eines Events
- **Log-Bereinigung** - Bestätigung vor dem Löschen von Log-Daten
- **Nachrichten löschen** - Bestätigung vor dem Löschen von Kanal-Nachrichten (neu!)

### Modals (Formulare)

- **Event-Erstellung** - Formular zum Erstellen eines neuen Events
- **Team-Registrierung** - Formular zur Anmeldung oder Aktualisierung eines Teams
- **Team-Bearbeitung** - Formular zum Ändern der Teamgröße

## Workflow-Beispiele

### Für Organisatoren: Event erstellen und verwalten

1. Erstelle ein neues Event mit `/create_event` (nutze die neuen Vorlagen für einfachere Eingabe)
2. Passe die Anzahl der verfügbaren Plätze an mit `/open_registration`
3. Überwache die Anmeldungen mit `/show_event` und `/team_list`
4. Verwalte Teams mit `/admin_add_team`, `/admin_team_edit` und `/admin_team_remove`
5. Überprüfe die Warteliste mit `/admin_waitlist`
6. Exportiere die Teilnehmerliste mit `/export_teams`
7. Halte den Kanal sauber mit `/clear_messages` (neu!)

### Für Clan-Leiter: Team anmelden und verwalten

1. Melde dein Team an mit `/register_team` oder über die Buttons in der Event-Anzeige
2. Ändere die Größe deines Teams bei Bedarf mit `/edit`
3. Zeige eine Liste aller Teams an mit `/team_list`
4. Melde dein Team bei Bedarf ab mit `/unregister`

## Wartelisten-System

Der Bot verfügt über ein fortschrittliches Wartelisten-Management:

- **Automatische Platzierung**: Teams werden automatisch auf die Warteliste gesetzt, wenn das Event voll ist
- **Automatisches Nachrücken**: Teams rücken automatisch nach, wenn Plätze frei werden
- **Priorisierung**: Teams auf der Warteliste werden nach Anmeldezeitpunkt sortiert
- **Benachrichtigungen**: Teamleiter erhalten automatisch DMs, wenn ihr Team vom Event-Status oder der Warteliste betroffen ist
- **Einheitliche Verwaltung**: Teams werden als Einheit betrachtet, unabhängig davon, ob sie im Event oder auf der Warteliste sind

## Log-Management

Der Bot bietet umfassende Logging-Funktionen:

- **Ausführliches Logging**: Alle wichtigen Aktionen werden in der Log-Datei `discord_bot.log` dokumentiert
- **Log-Kanal**: Wichtige Ereignisse werden zusätzlich im Discord-Kanal `log` gepostet
- **Automatische Backups**: Log-Dateien werden automatisch gesichert im Ordner `log_backups`
- **Export-Funktion**: Logs können mit `/export_log` als Datei exportiert werden
- **Import-Funktion**: Logs können mit `/import_log` wiederhergestellt werden
- **Bereinigung**: Logs können mit `/clear_log` zurückgesetzt werden

## Häufig gestellte Fragen

**F: Wie melde ich mein Team an?**  
A: Verwende den Befehl `/register_team team_name:Dein-Team-Name size:Anzahl` oder klicke auf den Anmelde-Button in der Event-Anzeige.

**F: Was passiert, wenn das Event voll ist?**  
A: Dein Team wird automatisch auf die Warteliste gesetzt und rückt nach, sobald Plätze frei werden.

**F: Kann ich die Größe meines Teams ändern?**  
A: Ja, verwende den Befehl `/edit` oder klicke auf den "Team bearbeiten"-Button in der Event-Anzeige.

**F: Wie sehe ich, welche Teams angemeldet sind?**  
A: Verwende den Befehl `/team_list`, um eine vollständige Liste aller Teams zu sehen.

**F: Mein Team ist auf der Warteliste. Wie erfahre ich, wenn wir nachrücken?**  
A: Du erhältst automatisch eine DM-Benachrichtigung, wenn dein Team vom Bot ins Event aufgenommen wird.

**F: Ich habe mich versehentlich mit einem falschen Team angemeldet. Was kann ich tun?**  
A: Melde dich mit `/unregister` ab und registriere dich dann erneut mit dem korrekten Team.

**F: Warum werden meine Slash-Befehle nicht angezeigt?**  
A: Ein Administrator muss den Befehl `/sync_commands` ausführen, um die Befehle zu aktualisieren.

**F: Was passiert, wenn ich die Größe meines Teams erhöhe?**  
A: Der Bot prüft, ob genügend Plätze im Event verfügbar sind. Falls nicht, wird dein Team teilweise oder vollständig auf die Warteliste gesetzt.

**F: Kann ich Nachrichten im Kanal löschen?**  
A: Als Administrator kannst du mit dem neuen Befehl `/clear_messages` mehrere Nachrichten gleichzeitig löschen.

**F: Wie funktionieren die Bestätigungsdialoge?**  
A: Bei kritischen Aktionen zeigt der Bot einen Dialog mit "Bestätigen" und "Abbrechen" Buttons. Diese Dialoge haben einen Timeout von 1 Stunde.

---

Für weitere Unterstützung wende dich an einen Server-Administrator oder Entwickler.