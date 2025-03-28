#!/usr/bin/env python3

import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import logging
import sys
import csv
import io

import pickle


from config import (
    TOKEN, COMMAND_PREFIX, ORGANIZER_ROLE, CLAN_REP_ROLE, 
    DEFAULT_MAX_SLOTS, DEFAULT_MAX_TEAM_SIZE, EXPANDED_MAX_TEAM_SIZE,
    WAITLIST_CHECK_INTERVAL, ADMIN_IDS
)
from utils import (
    load_data, save_data, format_event_details, format_event_list, 
    has_role, parse_date, logger, send_to_log_channel, discord_handler
)

# Check if token is available
if not TOKEN:
    logger.critical("No Discord bot token found. Set the DISCORD_BOT_TOKEN environment variable.")
    sys.exit(1)

# Set up Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True  # Add this to access member roles

# Initialize bot
class EventBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=COMMAND_PREFIX, intents=intents)
        
    async def setup_hook(self):
        await self.tree.sync()
        logger.info("Slash commands synced")

bot = EventBot()

# Load saved data
event_data, channel_id, user_team_assignments = load_data()
team_requester = {}  # Store users who requested waitlist spots

# Helper functions
def get_event():
    """Get the current event data"""
    # Defensive Programmierung: Stelle sicher, dass event_data existiert und ein Dictionary ist
    if not isinstance(event_data, dict):
        logger.error("event_data ist kein Dictionary")
        return {}
    
    # Greife auf den 'event'-Schlüssel in event_data zu
    event = event_data.get('event', {})
    
    # Prüfe, ob das Event alle erwarteten Schlüssel hat
    required_keys = ['name', 'date', 'teams', 'waitlist', 'max_slots', 'slots_used', 'max_team_size']
    for key in required_keys:
        if key not in event:
            logger.warning(f"Event fehlt Schlüssel: {key}")
            # Stelle default-Werte für wichtige Schlüssel bereit
            if key == 'teams':
                event['teams'] = {}
            elif key == 'waitlist':
                event['waitlist'] = []
            elif key in ['max_slots', 'slots_used', 'max_team_size']:
                event[key] = 0
            elif key in ['name', 'date']:
                event[key] = ""
    
    return event

def get_user_team(user_id):
    """Get the team name for a user"""
    return user_team_assignments.get(str(user_id))

# UI-Komponenten
class TeamRegistrationModal(ui.Modal):
    """Modal für die Team-Anmeldung"""
    def __init__(self, user):
        super().__init__(title="Team anmelden")
        self.user = user
        
        # Felder für Team-Name und -Größe
        self.team_name = ui.TextInput(
            label="Team-Name",
            placeholder="Gib den Namen deines Teams ein",
            required=True,
            min_length=2,
            max_length=30
        )
        self.add_item(self.team_name)
        
        self.team_size = ui.TextInput(
            label="Team-Größe",
            placeholder="Anzahl der Spieler ",
            required=True,
            min_length=1,
            max_length=2
        )
        self.add_item(self.team_size)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Definiere user_id aus der Interaktion
        user_id = str(interaction.user.id)
        
        # Verarbeite die Teamregistrierungslogik
        team_name = self.team_name.value.strip().lower()
        
        try:
            size = int(self.team_size.value)
        except ValueError:
            await interaction.response.send_message(
                "Bitte gib eine gültige Zahl für die Team-Größe ein.",
                ephemeral=True
            )
            return
        
        # Hole das aktive Event
        event = get_event()
        if not event:
            await interaction.response.send_message(
                "Es gibt derzeit kein aktives Event.",
                ephemeral=True
            )
            return
        
        max_team_size = event["max_team_size"]
        
        # Prüfe, ob der Nutzer bereits einem anderen Team zugewiesen ist
        if user_id in user_team_assignments and user_team_assignments[user_id] != team_name:
            assigned_team = user_team_assignments[user_id]
            await interaction.response.send_message(
                f"Du bist bereits dem Team '{assigned_team}' zugewiesen. Du kannst nur für ein Team anmelden.",
                ephemeral=True
            )
            return
        
        # Validiere Team-Größe
        if size <= 0 or size > max_team_size:
            await interaction.response.send_message(
                f"Die Teamgröße muss zwischen 1 und {max_team_size} liegen.",
                ephemeral=True
            )
            return
        
        # Prüfe, ob genügend Slots verfügbar sind
        current_size = event["teams"].get(team_name, 0)
        size_difference = size - current_size
        
        if size_difference > 0:
            # Prüfe, ob genügend Slots verfügbar sind
            if event["slots_used"] + size_difference > event["max_slots"]:
                # Verfügbare Slots berechnen
                available_slots = event["max_slots"] - event["slots_used"]
                
                if available_slots > 0:
                    # Teilweise anmelden und Rest auf Warteliste setzen
                    waitlist_size = size_difference - available_slots
                    
                    # Aktualisiere die angemeldete Teamgröße
                    event["slots_used"] += available_slots
                    event["teams"][team_name] = current_size + available_slots
                    
                    # Füge Rest zur Warteliste hinzu
                    # Prüfe, ob das Team bereits auf der Warteliste steht
                    team_on_waitlist = False
                    waitlist_index = -1
                    waitlist_team_size = 0
                    
                    for i, (wl_team, wl_size) in enumerate(event["waitlist"]):
                        if wl_team == team_name:
                            team_on_waitlist = True
                            waitlist_index = i
                            waitlist_team_size = wl_size
                            break
                    
                    if team_on_waitlist:
                        # Erhöhe die Größe des Teams auf der Warteliste
                        event["waitlist"][waitlist_index] = (team_name, waitlist_team_size + waitlist_size)
                        waitlist_message = f"Die bestehenden {waitlist_team_size} Plätze auf der Warteliste wurden um {waitlist_size} auf {waitlist_team_size + waitlist_size} erhöht."
                    else:
                        # Füge das Team zur Warteliste hinzu
                        event["waitlist"].append((team_name, waitlist_size))
                        waitlist_message = f"{waitlist_size} Spieler wurden auf die Warteliste gesetzt (Position {len(event['waitlist'])})."
                    
                    # Nutzer diesem Team zuweisen
                    user_team_assignments[user_id] = team_name
                    
                    # Speichere für Benachrichtigungen
                    team_requester[team_name] = interaction.user
                    
                    await interaction.response.send_message(
                        f"Team {team_name} wurde teilweise angemeldet. "
                        f"{current_size + available_slots} Spieler sind angemeldet und "
                        f"{waitlist_message}",
                        ephemeral=True
                    )
                    
                    # Log eintragen
                    await send_to_log_channel(
                        f"⚠️ Team teilweise angemeldet: {interaction.user.name} hat Team '{team_name}' teilweise angemeldet - {current_size + available_slots} Spieler registriert, {waitlist_size} auf Warteliste",
                        level="INFO",
                        guild=interaction.guild
                    )
                else:
                    # Empfehlen, die Warteliste zu nutzen
                    await interaction.response.send_message(
                        f"Es sind keine Slots mehr verfügbar. Du kannst dein Team mit dem Button 'Warteliste' auf die Warteliste setzen.",
                        ephemeral=True
                    )
                return
            
            # Genug Slots verfügbar
            event["slots_used"] += size_difference
            event["teams"][team_name] = size
            
            # Nutzer diesem Team zuweisen
            user_team_assignments[user_id] = team_name
            
            # Log eintragen
            await send_to_log_channel(
                f"✅ Team angemeldet: {interaction.user.name} hat Team '{team_name}' mit {size} Spielern angemeldet",
                level="INFO",
                guild=interaction.guild
            )
            
            await interaction.response.send_message(
                f"Team {team_name} wurde mit {size} Personen angemeldet.",
                ephemeral=True
            )
        elif size_difference < 0:
            # Team-Größe reduzieren
            event["slots_used"] += size_difference  # Wird negativ sein
            event["teams"][team_name] = size
            await interaction.response.send_message(
                f"Teamgröße für {team_name} wurde auf {size} aktualisiert.",
                ephemeral=True
            )
        else:
            # Größe unverändert
            await interaction.response.send_message(
                f"Team {team_name} ist bereits mit {size} Personen angemeldet.",
                ephemeral=True
            )
        
        # Speichere Daten nach jeder Änderung
        save_data(event_data, channel_id, user_team_assignments)
        
        # Update channel with latest event details
        if channel_id:
            channel = bot.get_channel(interaction.channel_id)
            if channel:
                await send_event_details(channel)

# Die TeamWaitlistModal-Klasse wurde entfernt, da die Warteliste jetzt automatisch verwaltet wird

class TeamEditModal(ui.Modal):
    """Modal zum Bearbeiten der Teamgröße"""
    def __init__(self, team_name, current_size, max_size, is_admin=False):
        super().__init__(title=f"Team {team_name} bearbeiten")
        self.team_name = team_name
        self.current_size = current_size
        self.is_admin = is_admin
        
        # Feld für die neue Teamgröße
        self.team_size = ui.TextInput(
            label="Neue Teamgröße",
            placeholder=f"Aktuelle Größe: {current_size} (Max: {max_size})",
            required=True,
            min_length=1,
            max_length=2,
            default=str(current_size)
        )
        self.add_item(self.team_size)
        
        # Für Admins: Optionales Feld für Kommentar/Grund
        if is_admin:
            self.reason = ui.TextInput(
                label="Grund für die Änderung (optional)",
                placeholder="z.B. 'Spieler hat abgesagt'",
                required=False,
                max_length=100
            )
            self.add_item(self.reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_size = int(self.team_size.value)
        except ValueError:
            await interaction.response.send_message(
                "Bitte gib eine gültige Zahl für die Teamgröße ein.",
                ephemeral=True
            )
            return
        
        # Rufe die Funktion auf, die die Teamgröße ändert
        result = await update_team_size(
            interaction, 
            self.team_name, 
            new_size, 
            is_admin=self.is_admin,
            reason=self.reason.value if self.is_admin and hasattr(self, 'reason') else None
        )

class AdminTeamCreateModal(ui.Modal):
    """Modal für Admins zum Hinzufügen eines Teams"""
    def __init__(self):
        super().__init__(title="Team hinzufügen")
        
        # Felder für Team-Name und -Größe
        self.team_name = ui.TextInput(
            label="Team-Name",
            placeholder="Gib den Namen des Teams ein",
            required=True,
            min_length=2,
            max_length=30
        )
        self.add_item(self.team_name)
        
        self.team_size = ui.TextInput(
            label="Team-Größe",
            placeholder="Anzahl der Spieler",
            required=True,
            min_length=1,
            max_length=2
        )
        self.add_item(self.team_size)
        
        self.discord_user = ui.TextInput(
            label="Discord-Nutzer (optional)",
            placeholder="Discord Nutzername oder ID für Teamzuweisung",
            required=False
        )
        self.add_item(self.discord_user)
        
        self.add_to_waitlist = ui.TextInput(
            label="Auf Warteliste?",
            placeholder="Ja/Nein (leer = automatisch)",
            required=False,
            max_length=5
        )
        self.add_item(self.add_to_waitlist)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Überprüfe Berechtigung
        if not has_role(interaction.user, ORGANIZER_ROLE):
            await interaction.response.send_message(
                f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können diese Aktion ausführen.",
                ephemeral=True
            )
            return
        
        team_name = self.team_name.value.strip().lower()
        
        try:
            size = int(self.team_size.value)
        except ValueError:
            await interaction.response.send_message(
                "Bitte gib eine gültige Zahl für die Team-Größe ein.",
                ephemeral=True
            )
            return
        
        # Prüfe Wartelisten-Option
        force_waitlist = False
        if self.add_to_waitlist.value.strip().lower() in ["ja", "yes", "true", "1", "y"]:
            force_waitlist = True
        
        # Discord-User prüfen
        discord_user_input = self.discord_user.value.strip()
        discord_user_id = None
        discord_username = None
        
        if discord_user_input:
            # Versuche, den Nutzer zu finden
            try:
                # Versuche als ID zu interpretieren
                if discord_user_input.isdigit():
                    user = await bot.fetch_user(int(discord_user_input))
                    discord_user_id = str(user.id)
                    discord_username = user.display_name
                else:
                    # Versuche Benutzer anhand des Namens zu finden
                    guild = interaction.guild
                    if guild:
                        found_members = [member for member in guild.members if 
                                         member.name.lower() == discord_user_input.lower() or 
                                         (member.nick and member.nick.lower() == discord_user_input.lower())]
                        
                        if found_members:
                            user = found_members[0]
                            discord_user_id = str(user.id)
                            discord_username = user.display_name
                        else:
                            await interaction.response.send_message(
                                f"Konnte keinen Nutzer mit dem Namen '{discord_user_input}' finden.",
                                ephemeral=True
                            )
                            return
            except Exception as e:
                logger.error(f"Fehler beim Suchen des Discord-Nutzers: {e}")
                await interaction.response.send_message(
                    f"Fehler beim Suchen des Discord-Nutzers: {e}",
                    ephemeral=True
                )
                return
        
        # Füge das Team hinzu
        result = await admin_add_team(
            interaction, 
            team_name, 
            size, 
            discord_user_id, 
            discord_username,
            force_waitlist
        )

class BaseView(ui.View):
    """Basis-View für alle Discord-UI-Komponenten mit erweitertem Timeout-Handling und Fehlerbehandlung"""
    def __init__(self, timeout=180, title="Interaktion"):
        super().__init__(timeout=timeout)
        self.has_responded = False  # Tracking-Variable für Interaktionen
        self.message = None
        self.timeout_title = title
    
    async def on_timeout(self):
        """Wird aufgerufen, wenn der Timeout abläuft"""
        try:
            # Buttons deaktivieren
            for child in self.children:
                child.disabled = True
            
            # Ursprüngliche Nachricht editieren, falls möglich
            if hasattr(self, 'message') and self.message:
                try:
                    await self.message.edit(
                        content=f"⏱️ **Zeitüberschreitung** - Die {self.timeout_title}-Anfrage ist abgelaufen. Bitte starte den Vorgang neu.",
                        view=self
                    )
                except discord.errors.NotFound:
                    # Nachricht existiert nicht mehr, ignorieren
                    logger.debug(f"Timeout-Nachricht konnte nicht editiert werden: Nachricht nicht gefunden")
                except discord.errors.Forbidden:
                    # Keine Berechtigung, ignorieren
                    logger.debug(f"Timeout-Nachricht konnte nicht editiert werden: Keine Berechtigung")
        except Exception as e:
            # Allgemeine Fehlerbehandlung als Fallback
            logger.warning(f"Fehler beim Timeout-Handling: {e}")
    
    def store_message(self, interaction):
        """Speichert die Nachricht für spätere Aktualisierungen"""
        self.message = interaction.message
        return self.message
    
    def check_response(self, interaction, store_msg=True):
        """Überprüft, ob die Interaktion bereits beantwortet wurde
        
        Parameters:
        - interaction: Discord-Interaktion
        - store_msg: Ob die Nachrichten-Referenz gespeichert werden soll
        
        Returns:
        - True, wenn die Interaktion bereits beantwortet wurde
        - False, wenn die Interaktion noch nicht beantwortet wurde
        """
        # Speichere die ursprüngliche Nachricht für spätere Aktualisierungen
        if store_msg:
            self.store_message(interaction)
        
        if self.has_responded:
            return True
            
        self.has_responded = True
        return False
    
    async def handle_already_responded(self, interaction, message="Diese Aktion wird bereits verarbeitet..."):
        """Einheitliche Behandlung für bereits beantwortete Interaktionen
        
        Parameters:
        - interaction: Discord-Interaktion
        - message: Optionale Nachricht, die gesendet werden soll
        """
        try:
            await interaction.followup.send(message, ephemeral=True)
        except Exception:
            pass  # Ignoriere Fehler hier, um andere Funktionalität nicht zu beeinträchtigen


class BaseConfirmationView(BaseView):
    """Basis-View für alle Bestätigungsdialoge mit Timeout-Handling und Response-Tracking"""
    def __init__(self, timeout=180, title="Bestätigung"):
        super().__init__(timeout=timeout, title=title)


class AdminTeamSelector(BaseView):
    """Auswahl eines Teams für die Bearbeitung durch Admins"""
    def __init__(self, for_removal=False):
        super().__init__(timeout=60, title="Admin-Teamauswahl")
        self.selected_team = None
        self.for_removal = for_removal  # Flag, ob die Auswahl für die Abmeldung ist
        
        # Dropdown für die Teamauswahl
        options = self.get_team_options()
        
        # Prüfe, ob Optionen vorhanden sind
        if not options:
            # Füge eine Dummy-Option hinzu, wenn keine Teams vorhanden sind
            options = [
                discord.SelectOption(
                    label="Keine Teams verfügbar",
                    value="no_teams",
                    description="Es sind keine Teams zum Bearbeiten verfügbar"
                )
            ]
        
        self.teams_select = ui.Select(
            placeholder="Wähle ein Team aus",
            options=options,
            custom_id="team_selector"
        )
        self.teams_select.callback = self.team_selected
        self.add_item(self.teams_select)
    
    def get_team_options(self):
        """Erstellt die Liste der Teams für das Dropdown"""
        event = get_event()
        if not event:
            return []
        
        team_options = []
        
        # Liste der angemeldeten Teams
        for team_name, size in event["teams"].items():
            team_options.append(
                discord.SelectOption(
                    label=f"{team_name} ({size} Personen)",
                    value=team_name,
                    description=f"Angemeldet mit {size} Personen"
                )
            )
        
        # Liste der Teams auf der Warteliste
        for i, (team_name, size) in enumerate(event["waitlist"]):
            team_options.append(
                discord.SelectOption(
                    label=f"{team_name} ({size} Personen)",
                    value=f"waitlist_{team_name}",
                    description=f"Auf Warteliste (Position {i+1})",
                    emoji="⏳"
                )
            )
        
        return team_options
    
    async def team_selected(self, interaction: discord.Interaction):
        """Callback für die Teamauswahl"""
        selected_value = self.teams_select.values[0]
        
        if selected_value == "no_teams":
            await interaction.response.send_message(
                "Es sind keine Teams zum Bearbeiten verfügbar.",
                ephemeral=True
            )
            return
        
        # Prüfe, ob es sich um ein Team auf der Warteliste handelt
        if selected_value.startswith("waitlist_"):
            team_name = selected_value[9:]  # Entferne "waitlist_" Präfix
            is_waitlist = True
        else:
            team_name = selected_value
            is_waitlist = False
        
        # Hole Informationen zum ausgewählten Team
        event = get_event()
        if not event:
            await interaction.response.send_message(
                "Es gibt derzeit kein aktives Event.",
                ephemeral=True
            )
            return
        
        # Wenn die Auswahl für das Abmelden des Teams ist
        if self.for_removal:
            # Bestätigungsdialog anzeigen
            embed = discord.Embed(
                title="⚠️ Team wirklich abmelden?",
                description=f"Bist du sicher, dass du das Team **{team_name}** abmelden möchtest?\n\n"
                           f"Diese Aktion kann nicht rückgängig gemacht werden!",
                color=discord.Color.red()
            )
            
            # Erstelle die Bestätigungsansicht
            view = TeamUnregisterConfirmationView(team_name, is_admin=True)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return
        
        # Ansonsten normale Bearbeitung (für Teamgröße ändern)
        if is_waitlist:
            # Suche Team in der Warteliste
            team_found = False
            team_size = 0
            position = 0
            for i, (wl_team, wl_size) in enumerate(event["waitlist"]):
                if wl_team == team_name:
                    team_found = True
                    team_size = wl_size
                    position = i + 1
                    break
            
            if not team_found:
                await interaction.response.send_message(
                    f"Team {team_name} wurde nicht auf der Warteliste gefunden.",
                    ephemeral=True
                )
                return
            
            # Erstelle ein Modal zur Bearbeitung des Teams auf der Warteliste
            modal = TeamEditModal(team_name, team_size, event["max_team_size"], is_admin=True)
            await interaction.response.send_modal(modal)
        else:
            # Suche Team in den angemeldeten Teams
            if team_name not in event["teams"]:
                await interaction.response.send_message(
                    f"Team {team_name} wurde nicht gefunden.",
                    ephemeral=True
                )
                return
            
            team_size = event["teams"][team_name]
            
            # Erstelle ein Modal zur Bearbeitung des angemeldeten Teams
            modal = TeamEditModal(team_name, team_size, event["max_team_size"], is_admin=True)
            await interaction.response.send_modal(modal)

class EventActionView(BaseView):
    """View mit Buttons für Event-Aktionen"""
    def __init__(self, event, user_has_admin=False, user_has_clan_rep=False, has_team=False, team_name=None):
        super().__init__(timeout=300, title="Event-Aktionen")  # 5 Minuten Timeout
        self.team_name = team_name
        
        # Team anmelden Button (nur für Clan-Rep)
        register_button = ui.Button(
            label="Team anmelden",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id=f"event_register",
            disabled=not user_has_clan_rep or has_team
        )
        register_button.callback = self.register_callback
        self.add_item(register_button)
        
        # Team abmelden Button (nur für Clan-Rep mit Team)
        if has_team and team_name:
            unregister_button = ui.Button(
                label="Team abmelden",
                emoji="❌",
                style=discord.ButtonStyle.danger,
                custom_id=f"event_unregister",
                disabled=not user_has_clan_rep
            )
            unregister_button.callback = self.unregister_callback
            self.add_item(unregister_button)
        
        # Warteliste wird automatisch verwaltet, daher kein Button mehr erforderlich
        
        # Team-Info für alle sichtbar
        team_info_button = ui.Button(
            label="Mein Team", 
            emoji="👥",
            style=discord.ButtonStyle.primary,
            custom_id=f"event_teaminfo"
        )
        team_info_button.callback = self.team_info_callback
        self.add_item(team_info_button)
        
        # Team bearbeiten Button (für Clan-Rep mit Team und Admins)
        if (user_has_clan_rep and has_team) or user_has_admin:
            edit_button = ui.Button(
                label="Team bearbeiten", 
                emoji="✏️",
                style=discord.ButtonStyle.primary,
                custom_id=f"event_edit_team"
            )
            edit_button.callback = self.edit_team_callback
            self.add_item(edit_button)
            
            # Team abmelden Button (für Clan-Rep mit Team)
            if user_has_clan_rep and has_team:
                unregister_button = ui.Button(
                    label="Team abmelden", 
                    emoji="❌",
                    style=discord.ButtonStyle.danger,
                    custom_id=f"event_unregister_team"
                )
                unregister_button.callback = self.unregister_callback
                self.add_item(unregister_button)
        
        # Admin-Aktionen (nur für Admins)
        if user_has_admin:
            admin_button = ui.Button(
                label="Admin", 
                emoji="⚙️",
                style=discord.ButtonStyle.danger,
                custom_id=f"event_admin"
            )
            admin_button.callback = self.admin_callback
            self.add_item(admin_button)
    
    async def register_callback(self, interaction: discord.Interaction):
        """Callback für Team-Registrierung-Button"""
        user_id = str(interaction.user.id)
        
        # Prüfe, ob der Benutzer bereits einem Team zugewiesen ist
        if user_id in user_team_assignments:
            team_name = user_team_assignments[user_id]
            await interaction.response.send_message(
                f"Du bist bereits dem Team '{team_name}' zugewiesen. Du kannst nicht erneut registrieren.",
                ephemeral=True
            )
            # Log für Versuch einer doppelten Registrierung
            await send_to_log_channel(
                f"ℹ️ Registrierungsversuch abgelehnt: Benutzer {interaction.user.name} ({interaction.user.id}) ist bereits Team '{team_name}' zugewiesen",
                level="INFO",
                guild=interaction.guild
            )
            return
        
        # Überprüfe Berechtigung mit der verbesserten has_role-Funktion
        # Die has_role-Funktion berücksichtigt jetzt auch ADMIN_IDs in DM-Kontexten
        if not has_role(interaction.user, CLAN_REP_ROLE):
            await interaction.response.send_message(
                f"Nur Mitglieder mit der Rolle '{CLAN_REP_ROLE}' können Teams anmelden.",
                ephemeral=True
            )
            # Log für unberechtigten Zugriff
            await send_to_log_channel(
                f"🚫 Unberechtigter Zugriffsversuch: {interaction.user.name} ({interaction.user.id}) hat versucht, ein Team zu registrieren ohne die Rolle '{CLAN_REP_ROLE}'",
                level="WARNING",
                guild=interaction.guild
            )
            return
        
        # Öffne ein Modal für die Team-Anmeldung
        modal = TeamRegistrationModal(interaction.user)
        await interaction.response.send_modal(modal)
        
        # Log für Registrierungsversuch
        await send_to_log_channel(
            f"🔄 Registrierungsvorgang gestartet: {interaction.user.name} ({interaction.user.id}) öffnet das Team-Registrierungsformular",
            level="INFO",
            guild=interaction.guild
        )
    
    async def unregister_callback(self, interaction: discord.Interaction):
        """Callback für Team-Abmeldung-Button"""
        user_id = str(interaction.user.id)
        
        # Überprüfe Berechtigung mit der verbesserten has_role-Funktion
        if not has_role(interaction.user, CLAN_REP_ROLE):
            await interaction.response.send_message(
                f"Nur Mitglieder mit der Rolle '{CLAN_REP_ROLE}' können Teams abmelden.",
                ephemeral=True
            )
            # Log für unberechtigten Zugriff
            await send_to_log_channel(
                f"🚫 Unberechtigter Zugriffsversuch: {interaction.user.name} ({interaction.user.id}) hat versucht, ein Team abzumelden ohne die Rolle '{CLAN_REP_ROLE}'",
                level="WARNING",
                guild=interaction.guild
            )
            return
        
        team_name = user_team_assignments.get(user_id)
        
        if not team_name:
            await interaction.response.send_message(
                "Du bist keinem Team zugewiesen.",
                ephemeral=True
            )
            # Log für fehlgeschlagene Abmeldung
            await send_to_log_channel(
                f"ℹ️ Abmeldungsversuch abgelehnt: Benutzer {interaction.user.name} ({interaction.user.id}) ist keinem Team zugewiesen",
                level="INFO",
                guild=interaction.guild
            )
            return
            
        event = get_event()
        if not event:
            await interaction.response.send_message("Es gibt kein aktives Event.", ephemeral=True)
            await send_to_log_channel(
                f"⚠️ Abmeldungsversuch fehlgeschlagen: Kein aktives Event vorhanden (Benutzer: {interaction.user.name})",
                level="WARNING",
                guild=interaction.guild
            )
            return
            
        # Prüfe, ob das Team angemeldet ist oder auf der Warteliste steht
        team_registered = team_name in event["teams"]
        team_on_waitlist = False
        
        for i, (wl_team, _) in enumerate(event["waitlist"]):
            if wl_team == team_name:
                team_on_waitlist = True
                break
                
        if team_registered or team_on_waitlist:
            # Bestätigungsdialog anzeigen
            embed = discord.Embed(
                title="⚠️ Team wirklich abmelden?",
                description=f"Bist du sicher, dass du dein Team **{team_name}** abmelden möchtest?\n\n"
                           f"Diese Aktion kann nicht rückgängig gemacht werden!",
                color=discord.Color.red()
            )
            
            # Erstelle die Bestätigungsansicht
            view = TeamUnregisterConfirmationView(team_name, is_admin=False)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            # Log für Abmeldebestätigungsdialog
            status = "registriert" if team_registered else "auf der Warteliste"
            await send_to_log_channel(
                f"🔄 Abmeldungsprozess gestartet: {interaction.user.name} ({interaction.user.id}) will Team '{team_name}' abmelden (Status: {status})",
                level="INFO",
                guild=interaction.guild
            )
        else:
            await interaction.response.send_message(
                f"Team {team_name} ist weder angemeldet noch auf der Warteliste.",
                ephemeral=True
            )
            # Log für fehlgeschlagene Abmeldung
            await send_to_log_channel(
                f"⚠️ Abmeldungsversuch fehlgeschlagen: Team '{team_name}' von {interaction.user.name} ({interaction.user.id}) ist weder angemeldet noch auf der Warteliste",
                level="WARNING",
                guild=interaction.guild
            )
    
    # Die waitlist_callback-Methode wurde entfernt, da die Warteliste jetzt automatisch verwaltet wird
    
    async def team_info_callback(self, interaction: discord.Interaction):
        """Callback für Team-Info-Button"""
        # Sende eine ephemeral Nachricht mit Team-Informationen
        await interaction.response.defer(ephemeral=True)
        
        global user_team_assignments
        event = get_event()
        user_id = str(interaction.user.id)
        
        # Hole das Team des Users
        team_name = user_team_assignments.get(user_id)
        team_size = None
        if team_name and event and team_name in event["teams"]:
            team_size = event["teams"][team_name]
        
        if not team_name or not team_size:
            embed = discord.Embed(
                title="ℹ️ Team-Information",
                description="Du bist aktuell keinem Team zugewiesen.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Was kannst du tun?",
                value=f"• **Team erstellen**: Nutze den Button 'Team anmelden'\n"
                      f"• **Team beitreten**: Bitte den Teamleiter, dich einzuladen\n"
                      f"• **Hilfe erhalten**: Nutze `/help` für mehr Informationen",
                inline=False
            )
        else:
            embed = discord.Embed(
                title=f"👥 Team: {team_name}",
                description=f"Du bist Mitglied des Teams **{team_name}**.",
                color=discord.Color.green()
            )
            
            # Team-Größe
            embed.add_field(
                name="📊 Team-Größe",
                value=f"{team_size} {'Person' if team_size == 1 else 'Personen'}",
                inline=True
            )
            
            # Füge Event-Informationen hinzu
            if event:
                embed.add_field(
                    name="🎮 Event",
                    value=f"{event['name']} ({event['date']}, {event['time']})",
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def edit_team_callback(self, interaction: discord.Interaction):
        """Callback für Team-Bearbeiten-Button"""
        user_id = str(interaction.user.id)
        
        # Verbesserte Rollenprüfung mit has_role (berücksichtigt ADMIN_IDs in DMs)
        is_admin = has_role(interaction.user, ORGANIZER_ROLE)
        is_clan_rep = has_role(interaction.user, CLAN_REP_ROLE)
        
        # Prüfe zuerst, ob es überhaupt ein aktives Event gibt
        event = get_event()
        if not event:
            await interaction.response.send_message(
                "Es gibt derzeit kein aktives Event.",
                ephemeral=True
            )
            await send_to_log_channel(
                f"⚠️ Team-Bearbeitungsversuch fehlgeschlagen: Kein aktives Event vorhanden (Benutzer: {interaction.user.name})",
                level="WARNING",
                guild=interaction.guild
            )
            return
        
        if is_admin:
            # Prüfe, ob es Teams gibt
            if not event["teams"] and not event["waitlist"]:
                await interaction.response.send_message(
                    "Es sind keine Teams zum Bearbeiten vorhanden.",
                    ephemeral=True
                )
                await send_to_log_channel(
                    f"ℹ️ Admin-Team-Bearbeitungsversuch fehlgeschlagen: Keine Teams vorhanden (Admin: {interaction.user.name})",
                    level="INFO",
                    guild=interaction.guild
                )
                return
                
            # Admins sehen alle Teams zur Auswahl
            view = AdminTeamSelector()
            await interaction.response.send_message(
                "Wähle das Team, das du bearbeiten möchtest:",
                view=view,
                ephemeral=True
            )
            
            # Log für Admin-Team-Bearbeitung
            await send_to_log_channel(
                f"👤 Admin-Teambearbeitungsprozess gestartet: {interaction.user.name} ({interaction.user.id}) wählt ein Team zur Bearbeitung",
                level="INFO",
                guild=interaction.guild
            )
        elif is_clan_rep:
            # Clan-Reps können nur ihr eigenes Team bearbeiten
            team_name = user_team_assignments.get(user_id)
            
            if not team_name:
                await interaction.response.send_message(
                    "Du bist keinem Team zugewiesen.",
                    ephemeral=True
                )
                await send_to_log_channel(
                    f"ℹ️ Team-Bearbeitungsversuch abgelehnt: Benutzer {interaction.user.name} ({interaction.user.id}) ist keinem Team zugewiesen",
                    level="INFO",
                    guild=interaction.guild
                )
                return
            
            # Prüfe, ob das Team angemeldet ist oder auf der Warteliste steht
            team_size = None
            is_on_waitlist = False
            
            if team_name in event["teams"]:
                team_size = event["teams"][team_name]
            else:
                for wl_team, wl_size in event["waitlist"]:
                    if wl_team == team_name:
                        team_size = wl_size
                        is_on_waitlist = True
                        break
            
            if team_size is None:
                await interaction.response.send_message(
                    f"Team {team_name} wurde nicht gefunden.",
                    ephemeral=True
                )
                await send_to_log_channel(
                    f"⚠️ Team-Bearbeitungsversuch fehlgeschlagen: Team '{team_name}' von {interaction.user.name} ({interaction.user.id}) nicht gefunden",
                    level="WARNING",
                    guild=interaction.guild
                )
                return
            
            # Öffne das Modal zur Teambearbeitung
            modal = TeamEditModal(team_name, team_size, event["max_team_size"])
            await interaction.response.send_modal(modal)
            
            # Log für Team-Bearbeitung
            status = "auf der Warteliste" if is_on_waitlist else "registriert"
            await send_to_log_channel(
                f"🔄 Team-Bearbeitungsprozess gestartet: {interaction.user.name} ({interaction.user.id}) bearbeitet Team '{team_name}' (Status: {status}, Aktuelle Größe: {team_size})",
                level="INFO",
                guild=interaction.guild
            )
        else:
            await interaction.response.send_message(
                f"Nur Mitglieder mit der Rolle '{CLAN_REP_ROLE}' oder '{ORGANIZER_ROLE}' können Teams bearbeiten.",
                ephemeral=True
            )
            # Log für unberechtigten Zugriff
            await send_to_log_channel(
                f"🚫 Unberechtigter Zugriffsversuch: {interaction.user.name} ({interaction.user.id}) hat versucht, ein Team zu bearbeiten ohne die erforderlichen Rollen",
                level="WARNING",
                guild=interaction.guild
            )
    
    async def admin_callback(self, interaction: discord.Interaction):
        """Callback für Admin-Button"""
        await interaction.response.defer(ephemeral=True)
        
        # Verbesserte Rollenprüfung mit has_role (berücksichtigt ADMIN_IDs in DMs)
        if not has_role(interaction.user, ORGANIZER_ROLE):
            await interaction.followup.send(
                f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können diese Aktion ausführen.",
                ephemeral=True
            )
            # Log für unberechtigten Zugriff
            await send_to_log_channel(
                f"🚫 Unberechtigter Zugriffsversuch: {interaction.user.name} ({interaction.user.id}) hat versucht, auf Admin-Funktionen zuzugreifen ohne die Rolle '{ORGANIZER_ROLE}'",
                level="WARNING",
                guild=interaction.guild
            )
            return
        
        # Prüfe, ob es ein aktives Event gibt
        event = get_event()
        if not event:
            await interaction.followup.send("Es gibt kein aktives Event.", ephemeral=True)
            await send_to_log_channel(
                f"⚠️ Admin-Zugriff bei fehlendem Event: {interaction.user.name} ({interaction.user.id}) hat versucht, auf Admin-Funktionen zuzugreifen, aber es gibt kein aktives Event",
                level="WARNING",
                guild=interaction.guild
            )
            return
        
        # Erstelle ein Embed mit Admin-Aktionen
        embed = discord.Embed(
            title="⚙️ Admin-Aktionen",
            description="Wähle eine der folgenden Aktionen:",
            color=discord.Color.dark_red()
        )
        
        # Erstelle ein View mit Admin-Aktionen
        view = AdminActionView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        # Log für Admin-Panel-Zugriff
        await send_to_log_channel(
            f"👤 Admin-Panel geöffnet: {interaction.user.name} ({interaction.user.id}) hat das Admin-Panel für das Event '{event['name']}' geöffnet",
            level="INFO",
            guild=interaction.guild
        )

class AdminActionView(BaseView):
    """View mit Buttons für Admin-Aktionen"""
    def __init__(self):
        super().__init__(timeout=180, title="Admin-Aktionen")  # 3 Minuten Timeout
        
        # Open Registration
        open_reg_button = ui.Button(
            label="Registrierung öffnen", 
            emoji="🔓",
            style=discord.ButtonStyle.primary,
            custom_id=f"admin_openreg"
        )
        open_reg_button.callback = self.open_reg_callback
        self.add_item(open_reg_button)
        
        # Manage Teams
        manage_teams_button = ui.Button(
            label="Teams verwalten", 
            emoji="👥",
            style=discord.ButtonStyle.primary,
            custom_id=f"admin_manage_teams"
        )
        manage_teams_button.callback = self.manage_teams_callback
        self.add_item(manage_teams_button)
        
        # Add Team Button
        add_team_button = ui.Button(
            label="Team hinzufügen", 
            emoji="➕",
            style=discord.ButtonStyle.success,
            custom_id=f"admin_add_team"
        )
        add_team_button.callback = self.add_team_callback
        self.add_item(add_team_button)
        
        # Remove Team Button
        remove_team_button = ui.Button(
            label="Team abmelden", 
            emoji="❌",
            style=discord.ButtonStyle.danger,
            custom_id=f"admin_remove_team"
        )
        remove_team_button.callback = self.remove_team_callback
        self.add_item(remove_team_button)
        
        # Delete Event
        delete_button = ui.Button(
            label="Event löschen", 
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id=f"admin_delete"
        )
        delete_button.callback = self.delete_callback
        self.add_item(delete_button)
    
    async def open_reg_callback(self, interaction: discord.Interaction):
        """Callback für Registrierung öffnen"""
        # Verhindere doppelte Antworten
        if self.check_response(interaction):
            await self.handle_already_responded(interaction)
            return
            
        # Überprüfe Berechtigung
        if not has_role(interaction.user, ORGANIZER_ROLE):
            await interaction.response.send_message(
                f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können diese Aktion ausführen.",
                ephemeral=True
            )
            # Log für unberechtigten Zugriff
            await send_to_log_channel(
                f"🚫 Unberechtigter Zugriffsversuch: {interaction.user.name} ({interaction.user.id}) hat versucht, die Registrierung zu öffnen ohne die Rolle '{ORGANIZER_ROLE}'",
                level="WARNING",
                guild=interaction.guild
            )
            return
        
        # Hole das aktive Event
        event = get_event()
        if not event:
            await interaction.response.send_message("Es gibt kein aktives Event.", ephemeral=True)
            await send_to_log_channel(
                f"⚠️ Registrierungsöffnung fehlgeschlagen: Kein aktives Event vorhanden (Admin: {interaction.user.name})",
                level="WARNING",
                guild=interaction.guild
            )
            return
        
        # Speichere die alte Teamgröße für das Logging
        old_max_size = event["max_team_size"]
        
        # Aktualisiere die maximale Teamgröße
        event["max_team_size"] = EXPANDED_MAX_TEAM_SIZE
        save_data(event_data, channel_id, user_team_assignments)
        
        embed = discord.Embed(
            title="🔓 Maximale Teamgröße erhöht",
            description=f"Die maximale Teamgröße wurde auf {EXPANDED_MAX_TEAM_SIZE} erhöht.",
            color=discord.Color.green()
        )
        
        # Benachrichtige auch im öffentlichen Channel
        channel = bot.get_channel(interaction.channel_id)
        if channel:
            await channel.send(
                f"📢 **Ankündigung**: Die maximale Teamgröße für das Event '{event['name']}' "
                f"wurde auf {EXPANDED_MAX_TEAM_SIZE} erhöht!"
            )
        
        # Log für erfolgreiche Registrierungsöffnung
        await send_to_log_channel(
            f"🔓 Registrierung geöffnet: {interaction.user.name} ({interaction.user.id}) hat die maximale Teamgröße von {old_max_size} auf {EXPANDED_MAX_TEAM_SIZE} erhöht für Event '{event['name']}'",
            level="INFO",
            guild=interaction.guild
        )
            
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def manage_teams_callback(self, interaction: discord.Interaction):
        """Callback für Team-Verwaltung"""
        # Verhindere doppelte Antworten
        if self.check_response(interaction):
            await self.handle_already_responded(interaction)
            return
            
        # Überprüfe Berechtigung
        if not has_role(interaction.user, ORGANIZER_ROLE):
            await interaction.response.send_message(
                f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können diese Aktion ausführen.",
                ephemeral=True
            )
            return
        
        # Erstelle ein Embed mit der Team-Übersicht
        event = get_event()
        if not event:
            await interaction.response.send_message("Es gibt kein aktives Event.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="👥 Team-Verwaltung",
            description=f"Hier kannst du alle Teams für das Event **{event['name']}** verwalten.",
            color=discord.Color.blue()
        )
        
        # Angemeldete Teams
        teams_text = ""
        if event["teams"]:
            for team_name, size in event["teams"].items():
                teams_text += f"• **{team_name}**: {size} {'Person' if size == 1 else 'Personen'}\n"
        else:
            teams_text = "Noch keine Teams angemeldet."
        
        embed.add_field(
            name=f"📋 Angemeldete Teams ({len(event['teams'])})",
            value=teams_text,
            inline=False
        )
        
        # Warteliste
        if event["waitlist"]:
            waitlist_text = ""
            for i, (team_name, size) in enumerate(event["waitlist"]):
                waitlist_text += f"{i+1}. **{team_name}**: {size} {'Person' if size == 1 else 'Personen'}\n"
            
            embed.add_field(
                name=f"⏳ Warteliste ({len(event['waitlist'])})",
                value=waitlist_text,
                inline=False
            )
        
        # Erstelle die Team-Auswahl
        view = AdminTeamSelector()
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )
    
    async def add_team_callback(self, interaction: discord.Interaction):
        """Callback zum Hinzufügen eines Teams"""
        # Verhindere doppelte Antworten
        if self.check_response(interaction, store_msg=False):
            await self.handle_already_responded(interaction)
            return
            
        # Überprüfe Berechtigung
        if not has_role(interaction.user, ORGANIZER_ROLE):
            await interaction.response.send_message(
                f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können diese Aktion ausführen.",
                ephemeral=True
            )
            return
        
        # Öffne ein Modal zum Hinzufügen eines Teams
        modal = AdminTeamCreateModal()
        await interaction.response.send_modal(modal)
    
    async def remove_team_callback(self, interaction: discord.Interaction):
        """Callback für Team abmelden"""
        # Verhindere doppelte Antworten
        if self.check_response(interaction):
            await self.handle_already_responded(interaction)
            return
            
        # Überprüfe Berechtigung
        if not has_role(interaction.user, ORGANIZER_ROLE):
            await interaction.response.send_message(
                f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können diese Aktion ausführen.",
                ephemeral=True
            )
            return
        
        # Hole das aktive Event
        event = get_event()
        if not event:
            await interaction.response.send_message("Es gibt kein aktives Event.", ephemeral=True)
            return
        
        # Zeige eine Team-Auswahl an
        embed = discord.Embed(
            title="❌ Team abmelden",
            description="Wähle ein Team aus, das du abmelden möchtest.",
            color=discord.Color.red()
        )
        
        # Erstelle die Team-Auswahl mit for_removal=True
        view = AdminTeamSelector(for_removal=True)
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )
        
    async def delete_callback(self, interaction: discord.Interaction):
        """Callback für Event löschen"""
        # Verhindere doppelte Antworten
        if self.check_response(interaction):
            await self.handle_already_responded(interaction)
            return
            
        # Überprüfe Berechtigung
        if not has_role(interaction.user, ORGANIZER_ROLE):
            await interaction.response.send_message(
                f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können diese Aktion ausführen.",
                ephemeral=True
            )
            return
        
        # Hole das aktive Event
        event = get_event()
        if not event:
            await interaction.response.send_message("Es gibt kein aktives Event.", ephemeral=True)
            return
        
        # Zeige eine Bestätigungsanfrage
        embed = discord.Embed(
            title="⚠️ Event wirklich löschen?",
            description=f"Bist du sicher, dass du das Event **{event['name']}** löschen möchtest?\n\n"
                        f"Diese Aktion kann nicht rückgängig gemacht werden! Alle Team-Anmeldungen und Wartelisten-Einträge werden gelöscht.",
            color=discord.Color.red()
        )
        
        view = DeleteConfirmationView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class TeamUnregisterConfirmationView(BaseConfirmationView):
    """View für die Bestätigung einer Team-Abmeldung"""
    def __init__(self, team_name, is_admin=False):
        super().__init__(title="Team-Abmeldung")
        self.team_name = team_name.strip().lower() if team_name else ""
        self.is_admin = is_admin
    
    @ui.button(label="Ja, Team abmelden", style=discord.ButtonStyle.danger)
    async def confirm_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Callback für Bestätigung der Team-Abmeldung"""
        if not self.team_name:
            await interaction.response.send_message(
                "Fehler: Kein Team-Name angegeben.", 
                ephemeral=True
            )
            return
        
        # Verhindere doppelte Antworten
        if self.check_response(interaction):
            try:
                await interaction.followup.send(
                    "Diese Aktion wird bereits verarbeitet...",
                    ephemeral=True
                )
            except Exception:
                pass  # Ignoriere Fehler hier, um andere Funktionalität nicht zu beeinträchtigen
            return
        
        # Deaktiviere die Buttons, um Doppelklicks zu verhindern
        for child in self.children:
            child.disabled = True
        
        # Warte-Nachricht senden
        await interaction.response.edit_message(
            content="⏳ Verarbeite Team-Abmeldung...", 
            view=self
        )
        
        try:
            # Hole Event-Daten, um Team-Gesamtgröße zu ermitteln (angemeldet + Warteliste)
            event = get_event()
            total_size = 0
            registered_size = 0
            waitlist_size = 0
            
            if event:
                # Größe im registrierten Team
                if self.team_name in event.get("teams", {}):
                    registered_size = event["teams"][self.team_name]
                    total_size += registered_size
                
                # Größe auf der Warteliste
                for wl_team, wl_size in event.get("waitlist", []):
                    if wl_team == self.team_name:
                        waitlist_size = wl_size
                        total_size += waitlist_size
                        break
            
            # Führe die Teamgrößenänderung auf 0 durch (was zur Abmeldung führt)
            success = await update_team_size(
                interaction, 
                self.team_name, 
                0, 
                is_admin=self.is_admin,
                reason="Team manuell abgemeldet"
            )
            
            if success:
                # Erfolgsnachricht mit vollständiger Teamgröße
                size_info = ""
                if registered_size > 0 and waitlist_size > 0:
                    size_info = f" ({registered_size} angemeldet, {waitlist_size} auf Warteliste, {total_size} insgesamt)"
                elif registered_size > 0:
                    size_info = f" ({registered_size} Spieler)"
                elif waitlist_size > 0:
                    size_info = f" ({waitlist_size} Spieler auf Warteliste)"
                
                embed = discord.Embed(
                    title="✅ Team abgemeldet",
                    description=f"Das Team **{self.team_name}**{size_info} wurde erfolgreich abgemeldet.",
                    color=discord.Color.green()
                )
                
                # Aktualisiere die Nachricht (nicht neue Antwort senden!)
                await interaction.edit_original_response(content=None, embed=embed, view=None)
                
                # Logging
                await send_to_log_channel(
                    f"✅ Team abgemeldet: Team '{self.team_name}'{size_info} wurde erfolgreich abgemeldet " + 
                    f"durch {'Admin' if self.is_admin else 'Benutzer'} {interaction.user.name}",
                    guild=interaction.guild
                )
            else:
                # Fehlermeldung
                embed = discord.Embed(
                    title="❌ Fehler",
                    description=f"Team {self.team_name} konnte nicht abgemeldet werden.",
                    color=discord.Color.red()
                )
                # Aktualisiere die Nachricht (nicht neue Antwort senden!)
                await interaction.edit_original_response(content=None, embed=embed, view=None)
                
                # Logging
                await send_to_log_channel(
                    f"❌ Fehler bei Abmeldung: Team '{self.team_name}' konnte nicht abgemeldet werden " + 
                    f"durch {'Admin' if self.is_admin else 'Benutzer'} {interaction.user.name}",
                    level="ERROR",
                    guild=interaction.guild
                )
        except Exception as e:
            # Fehlerbehandlung
            error_msg = str(e)
            logger.error(f"Fehler bei Bestätigung der Team-Abmeldung: {error_msg}")
            
            try:
                # Versuche, die ursprüngliche Nachricht zu aktualisieren
                error_embed = discord.Embed(
                    title="❌ Fehler bei der Team-Abmeldung",
                    description=f"Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es später erneut.",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(content=None, embed=error_embed, view=None)
            except Exception:
                # Falls das nicht klappt, ignoriere den Fehler
                pass
    
    @ui.button(label="Abbrechen", style=discord.ButtonStyle.secondary)
    async def cancel_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Callback für Abbruch der Team-Abmeldung"""
        # Verhindere doppelte Antworten
        if self.check_response(interaction):
            try:
                await interaction.followup.send(
                    "Diese Aktion wird bereits verarbeitet...",
                    ephemeral=True
                )
            except Exception:
                pass  # Ignoriere Fehler hier
            return
        
        # Deaktiviere die Buttons, um Doppelklicks zu verhindern
        for child in self.children:
            child.disabled = True
            
        # Log für abgebrochene Team-Abmeldung
        admin_or_user = "Admin" if self.is_admin else "Benutzer"
        await send_to_log_channel(
            f"🛑 Team-Abmeldung abgebrochen: {admin_or_user} {interaction.user.name} ({interaction.user.id}) hat die Abmeldung von Team '{self.team_name}' abgebrochen",
            level="INFO",
            guild=interaction.guild
        )
        
        embed = discord.Embed(
            title="🛑 Abmeldung abgebrochen",
            description=f"Die Abmeldung des Teams {self.team_name} wurde abgebrochen.",
            color=discord.Color.blue()
        )
        
        # Aktualisiere die Nachricht statt neue zu senden
        await interaction.response.edit_message(content=None, embed=embed, view=self)


class DeleteConfirmationView(BaseConfirmationView):
    """View für die Bestätigung einer Event-Löschung"""
    def __init__(self):
        super().__init__(title="Event-Löschung")
    
    @ui.button(label="Ja, Event löschen", style=discord.ButtonStyle.danger)
    async def confirm_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Callback für Bestätigung der Löschung"""
        global event_data, user_team_assignments
        
        # Verhindere doppelte Antworten
        if self.check_response(interaction):
            try:
                await interaction.followup.send(
                    "Diese Aktion wird bereits verarbeitet...",
                    ephemeral=True
                )
            except Exception:
                pass
            return
        
        # Deaktiviere Buttons
        for child in self.children:
            child.disabled = True
        
        # Warte-Nachricht senden
        await interaction.response.edit_message(
            content="⏳ Verarbeite Event-Löschung...", 
            view=self
        )
        
        try:
            # Lösche das Event
            event = get_event()
            if event:
                event_name = event['name']
                event_date = event.get('date', 'unbekannt')
                registered_teams = len(event["teams"])
                waitlist_teams = len(event["waitlist"])
                
                # Erstelle ein Log mit detaillierten Informationen zum Event
                log_message = (
                    f"🗑️ Event gelöscht: {interaction.user.name} ({interaction.user.id}) hat das Event '{event_name}' gelöscht\n"
                    f"Datum: {event_date}, Angemeldete Teams: {registered_teams}, Teams auf der Warteliste: {waitlist_teams}"
                )
                await send_to_log_channel(log_message, level="WARNING", guild=interaction.guild)
                
                # Jetzt löschen
                event_data.clear()
                user_team_assignments.clear()
                save_data(event_data, channel_id, user_team_assignments)
                
                embed = discord.Embed(
                    title="✅ Event gelöscht",
                    description="Das Event wurde erfolgreich gelöscht.",
                    color=discord.Color.green()
                )
                
                # Aktualisiere die Bestätigungsnachricht
                await interaction.edit_original_response(content=None, embed=embed, view=None)
                
                # Benachrichtige auch im öffentlichen Channel
                channel = bot.get_channel(interaction.channel_id)
                if channel:
                    await channel.send(f"📢 **Information**: Das Event '{event_name}' wurde gelöscht.")
            else:
                embed = discord.Embed(
                    title="❌ Fehler",
                    description="Es gibt kein aktives Event zum Löschen.",
                    color=discord.Color.red()
                )
                
                await send_to_log_channel(
                    f"⚠️ Event-Löschungsversuch fehlgeschlagen: Kein aktives Event vorhanden (Admin: {interaction.user.name})",
                    level="WARNING", 
                    guild=interaction.guild
                )
                
                # Aktualisiere die Bestätigungsnachricht
                await interaction.edit_original_response(content=None, embed=embed, view=None)
        except Exception as e:
            logger.error(f"Fehler bei Event-Löschung: {e}")
            try:
                error_embed = discord.Embed(
                    title="❌ Fehler bei der Event-Löschung",
                    description=f"Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es später erneut.",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(content=None, embed=error_embed, view=None)
            except Exception:
                pass
    
    @ui.button(label="Abbrechen", style=discord.ButtonStyle.secondary)
    async def cancel_callback(self, interaction: discord.Interaction, button: ui.Button):
        """Callback für Abbruch der Löschung"""
        # Verhindere doppelte Antworten
        if self.check_response(interaction):
            try:
                await interaction.followup.send(
                    "Diese Aktion wird bereits verarbeitet...",
                    ephemeral=True
                )
            except Exception:
                pass
            return
        
        # Deaktiviere die Buttons
        for child in self.children:
            child.disabled = True
        
        # Hole das aktive Event für Logging
        event = get_event()
        if event:
            event_name = event['name']
            # Log für abgebrochene Event-Löschung
            await send_to_log_channel(
                f"🛑 Event-Löschung abgebrochen: {interaction.user.name} ({interaction.user.id}) hat die Löschung von Event '{event_name}' abgebrochen",
                level="INFO",
                guild=interaction.guild
            )
        
        embed = discord.Embed(
            title="🛑 Löschung abgebrochen",
            description="Die Löschung des Events wurde abgebrochen.",
            color=discord.Color.blue()
        )
        
        # Aktualisiere die Nachricht statt neue zu senden
        await interaction.response.edit_message(content=None, embed=embed, view=self)

async def send_team_dm_notification(team_name, message):
    """
    Sendet eine DM-Benachrichtigung an den Teamleiter.
    
    Parameters:
    - team_name: Name des Teams
    - message: Nachricht, die gesendet werden soll
    """
    # Suche nach dem Benutzer, der das Team erstellt hat
    team_leader_id = None
    for uid, tname in user_team_assignments.items():
        if tname == team_name:
            team_leader_id = uid
            break
    
    if team_leader_id:
        try:
            # Versuche, den Benutzer zu erreichen
            user = await bot.fetch_user(int(team_leader_id))
            if user:
                await user.send(message)
                logger.info(f"DM Benachrichtigung an {user.name} für Team {team_name} gesendet")
        except discord.errors.Forbidden:
            logger.warning(f"Konnte keine DM an Benutzer {team_leader_id} senden (Team {team_name})")
        except Exception as e:
            logger.error(f"Fehler beim Senden der DM an Benutzer {team_leader_id}: {e}")


async def update_team_size(interaction, team_name, new_size, is_admin=False, reason=None):
    """
    Aktualisiert die Größe eines Teams und verwaltet die Warteliste entsprechend.
    
    Parameters:
    - interaction: Discord-Interaktion
    - team_name: Name des Teams
    - new_size: Neue Teamgröße
    - is_admin: Ob die Änderung von einem Admin durchgeführt wird
    - reason: Optionaler Grund für die Änderung (nur für Admins)
    
    Returns:
    - True bei Erfolg, False bei Fehler
    """
    # Defensive Programmierung - Validiere Eingaben
    if not isinstance(team_name, str) or not team_name.strip():
        logger.error(f"Ungültiger Team-Name: {team_name}")
        await interaction.response.send_message(
            "Ungültiger Team-Name.",
            ephemeral=True
        )
        return False
    
    team_name = team_name.strip().lower()
    
    try:
        new_size = int(new_size)
    except (ValueError, TypeError):
        logger.error(f"Ungültige Teamgröße: {new_size}")
        await interaction.response.send_message(
            "Die Teamgröße muss eine ganze Zahl sein.",
            ephemeral=True
        )
        return False
    
    event = get_event()
    if not event:
        await interaction.response.send_message(
            "Es gibt derzeit kein aktives Event.",
            ephemeral=True
        )
        return False
    
    user_id = str(interaction.user.id)
    
    # Prüfe Berechtigungen
    if not is_admin and (not has_role(interaction.user, CLAN_REP_ROLE) or 
                          user_team_assignments.get(user_id) != team_name):
        await interaction.response.send_message(
            "Du kannst nur dein eigenes Team bearbeiten.",
            ephemeral=True
        )
        return False
    
    max_team_size = event.get("max_team_size", 0)
    
    # Validiere neue Teamgröße
    if new_size < 0:
        await interaction.response.send_message(
            "Die Teamgröße kann nicht negativ sein.",
            ephemeral=True
        )
        return False
    
    if new_size > max_team_size and not is_admin:
        await interaction.response.send_message(
            f"Die maximale Teamgröße beträgt {max_team_size}.",
            ephemeral=True
        )
        return False
    
    # Prüfe, ob das Team angemeldet ist oder auf der Warteliste steht
    team_registered = team_name in event.get("teams", {})
    team_on_waitlist = False
    waitlist_index = -1
    waitlist_size = 0
    
    for i, (wl_team, wl_size) in enumerate(event["waitlist"]):
        if wl_team == team_name:
            team_on_waitlist = True
            waitlist_index = i
            waitlist_size = wl_size
            break
            
    # Wenn Teamgröße 0 ist, Team automatisch abmelden
    if new_size == 0:
        # Überprüfe, ob das Team sowohl angemeldet als auch auf der Warteliste steht
        # damit wir die korrekte Gesamtgröße ermitteln können
        total_size = 0
        total_size_message = ""
        
        if team_registered:
            registered_size = event["teams"].pop(team_name)
            event["slots_used"] -= registered_size
            total_size += registered_size
            total_size_message = f"mit {registered_size} angemeldeten Spielern"
        
        # Prüfe, ob das Team auch auf der Warteliste steht
        if team_on_waitlist:
            event["waitlist"].pop(waitlist_index)
            total_size += waitlist_size
            if total_size_message:
                total_size_message += f" und {waitlist_size} auf der Warteliste (insgesamt {total_size})"
            else:
                total_size_message = f"mit {waitlist_size} Spielern auf der Warteliste"
        
        # Wenn kein Größentext gesetzt wurde, nutze die ermittelte Größe
        if not total_size_message and total_size > 0:
            total_size_message = f"mit {total_size} Spielern"
        
        # Finde alle Benutzer, die diesem Team zugewiesen sind, und entferne sie
        users_to_remove = []
        for uid, tname in user_team_assignments.items():
            if tname == team_name:
                users_to_remove.append(uid)
        
        for uid in users_to_remove:
            del user_team_assignments[uid]
            
        save_data(event_data, channel_id, user_team_assignments)
        
        # Freie Slots für die Warteliste verwenden, wenn Team angemeldet war
        if team_registered:
            free_slots = registered_size  # Nur registrierte Plätze freigeben
            await process_waitlist_after_change(interaction, free_slots)
        
        # Log für Team-Abmeldung
        admin_or_user = "Admin" if is_admin else "Benutzer"
        admin_name = getattr(interaction.user, "name", "Unbekannt")
        log_message = f"❌ Team abgemeldet: {admin_or_user} {admin_name} hat Team '{team_name}' {total_size_message} abgemeldet"
        if reason:
            log_message += f" (Grund: {reason})"
        await send_to_log_channel(log_message, guild=interaction.guild)
        
        # Nachricht senden
        message = f"Team {team_name} {total_size_message} wurde abgemeldet."
        if reason:
            message += f" Grund: {reason}"
            
        # Nutze followup bei modals/views, ansonsten response
        try:
            if hasattr(interaction, 'edit_original_response'):
                embed = discord.Embed(
                    title="✅ Team abgemeldet",
                    description=message,
                    color=discord.Color.green()
                )
                await interaction.edit_original_response(content=None, embed=embed, view=None)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except Exception as e:
            logger.error(f"Fehler beim Senden der Abmeldebestätigung: {e}")
            try:
                await interaction.followup.send(message, ephemeral=True)
            except Exception:
                pass
        
        # Sende DM an Teamleiter bei Admin-Änderungen
        if is_admin:
            dm_message = f"❌ Dein Team **{team_name}** {total_size_message} wurde von einem Administrator abgemeldet."
            if reason:
                dm_message += f"\nGrund: {reason}"
            
            dm_message += f"\n\nFalls du Fragen hast, wende dich bitte an einen Administrator."
            await send_team_dm_notification(team_name, dm_message)
        
        # Channel aktualisieren
        if channel_id:
            channel = bot.get_channel(interaction.channel_id)
            if channel:
                await send_event_details(channel)
        
        return True
    
    # Validiere neue Teamgröße (für Werte > 0)
    if new_size < 0:
        await interaction.response.send_message(
            "Die Teamgröße kann nicht negativ sein.",
            ephemeral=True
        )
        return False
    
    if new_size > max_team_size:
        await interaction.response.send_message(
            f"Die maximale Teamgröße beträgt {max_team_size}.",
            ephemeral=True
        )
        return False
    
    # Behandle die verschiedenen Fälle
    if team_registered:
        current_size = event["teams"][team_name]
        size_difference = new_size - current_size
        
        if size_difference == 0:
            # Keine Änderung
            await interaction.response.send_message(
                f"Die Teamgröße von {team_name} bleibt unverändert bei {current_size}.",
                ephemeral=True
            )
            return True
        
        elif size_difference > 0:
            # Teamgröße erhöhen
            available_slots = event["max_slots"] - event["slots_used"]
            
            if size_difference <= available_slots:
                # Genug Plätze verfügbar
                event["slots_used"] += size_difference
                event["teams"][team_name] = new_size
                
                # Log für Teamgröße-Erhöhung
                admin_or_user = "Admin" if is_admin else "Benutzer"
                admin_name = getattr(interaction.user, "name", "Unbekannt")
                log_message = f"📈 Teamgröße erhöht: {admin_or_user} {admin_name} hat die Größe von Team '{team_name}' von {current_size} auf {new_size} erhöht"
                if reason:
                    log_message += f" (Grund: {reason})"
                await send_to_log_channel(log_message, guild=interaction.guild)
                
                await interaction.response.send_message(
                    f"Die Teamgröße von {team_name} wurde von {current_size} auf {new_size} erhöht.",
                    ephemeral=True
                )
                
                # Log für Admins
                if is_admin and reason:
                    logger.info(f"Admin {interaction.user.name} hat die Größe von Team {team_name} auf {new_size} gesetzt. Grund: {reason}")
                
                # Sende DM an Teamleiter bei Admin-Änderungen
                if is_admin:
                    dm_message = f"📈 Die Größe deines Teams **{team_name}** wurde von einem Administrator von {current_size} auf {new_size} erhöht."
                    if reason:
                        dm_message += f"\nGrund: {reason}"
                    
                    dm_message += f"\n\nFalls du Fragen hast, wende dich bitte an einen Administrator."
                    await send_team_dm_notification(team_name, dm_message)
            else:
                # Nicht genug Plätze - Teile das Team auf
                filled_slots = available_slots
                waitlist_slots = size_difference - available_slots
                
                # Erhöhe die registrierte Teamgröße um die verfügbaren Slots
                event["slots_used"] += filled_slots
                event["teams"][team_name] = current_size + filled_slots
                
                # Füge die restlichen Spieler zur Warteliste hinzu
                # Prüfe, ob das Team bereits auf der Warteliste steht
                if team_on_waitlist:
                    # Erhöhe die Größe des Teams auf der Warteliste
                    event["waitlist"][waitlist_index] = (team_name, waitlist_size + waitlist_slots)
                    waitlist_message = f"Die bestehenden {waitlist_size} Plätze auf der Warteliste wurden um {waitlist_slots} auf {waitlist_size + waitlist_slots} erhöht."
                else:
                    # Füge das Team zur Warteliste hinzu
                    event["waitlist"].append((team_name, waitlist_slots))
                    waitlist_message = f"{waitlist_slots} Spieler wurden auf die Warteliste gesetzt (Position {len(event['waitlist'])})."
                
                await interaction.response.send_message(
                    f"Die Teamgröße von {team_name} wurde teilweise erhöht. "
                    f"{filled_slots} zusätzliche Spieler wurden angemeldet. "
                    f"{waitlist_message}",
                    ephemeral=True
                )
                
                # Benachrichtigung im Channel
                if channel_id:
                    channel = bot.get_channel(interaction.channel_id)
                    if channel:
                        await channel.send(
                            f"📢 Team {team_name} wurde teilweise erweitert. "
                            f"{filled_slots} Spieler wurden angemeldet und {waitlist_slots} auf die Warteliste gesetzt."
                        )
        
        else:  # size_difference < 0
            # Teamgröße verringern
            event["slots_used"] += size_difference  # Wird negativ sein
            event["teams"][team_name] = new_size
            
            # Log für Teamgröße-Verringerung
            admin_or_user = "Admin" if is_admin else "Benutzer"
            admin_name = getattr(interaction.user, "name", "Unbekannt")
            log_message = f"📉 Teamgröße verringert: {admin_or_user} {admin_name} hat die Größe von Team '{team_name}' von {current_size} auf {new_size} verringert"
            if reason:
                log_message += f" (Grund: {reason})"
            await send_to_log_channel(log_message, guild=interaction.guild)
            
            await interaction.response.send_message(
                f"Die Teamgröße von {team_name} wurde von {current_size} auf {new_size} verringert.",
                ephemeral=True
            )
            
            # Log für Admins
            if is_admin and reason:
                logger.info(f"Admin {interaction.user.name} hat die Größe von Team {team_name} auf {new_size} verringert. Grund: {reason}")
            
            # Sende DM an Teamleiter bei Admin-Änderungen
            if is_admin:
                dm_message = f"📉 Die Größe deines Teams **{team_name}** wurde von einem Administrator von {current_size} auf {new_size} verringert."
                if reason:
                    dm_message += f"\nGrund: {reason}"
                
                dm_message += f"\n\nFalls du Fragen hast, wende dich bitte an einen Administrator."
                await send_team_dm_notification(team_name, dm_message)
            
            # Freie Slots für Teams auf der Warteliste nutzen
            free_slots = -size_difference
            await process_waitlist_after_change(interaction, free_slots)
    
    elif team_on_waitlist:
        # Team ist auf der Warteliste
        size_difference = new_size - waitlist_size
        
        if size_difference == 0:
            # Keine Änderung
            await interaction.response.send_message(
                f"Die Teamgröße von {team_name} auf der Warteliste bleibt unverändert bei {waitlist_size}.",
                ephemeral=True
            )
            return True
        
        # Aktualisiere die Teamgröße auf der Warteliste
        event["waitlist"][waitlist_index] = (team_name, new_size)
        
        # Log für Warteliste-Teamgröße-Änderung
        admin_or_user = "Admin" if is_admin else "Benutzer"
        admin_name = getattr(interaction.user, "name", "Unbekannt")
        if size_difference > 0:
            message = f"Die Teamgröße von {team_name} auf der Warteliste wurde von {waitlist_size} auf {new_size} erhöht."
            log_message = f"📈 Warteliste-Team erhöht: {admin_or_user} {admin_name} hat die Größe von Team '{team_name}' auf der Warteliste von {waitlist_size} auf {new_size} erhöht"
        else:
            message = f"Die Teamgröße von {team_name} auf der Warteliste wurde von {waitlist_size} auf {new_size} verringert."
            log_message = f"📉 Warteliste-Team verringert: {admin_or_user} {admin_name} hat die Größe von Team '{team_name}' auf der Warteliste von {waitlist_size} auf {new_size} verringert"
        
        if reason:
            log_message += f" (Grund: {reason})"
        await send_to_log_channel(log_message, guild=interaction.guild)
        
        await interaction.response.send_message(
            message,
            ephemeral=True
        )
        
        # Log für Admins
        if is_admin and reason:
            logger.info(f"Admin {interaction.user.name} hat die Größe von Team {team_name} auf der Warteliste auf {new_size} gesetzt. Grund: {reason}")
        
        # Sende DM an Teamleiter bei Admin-Änderungen
        if is_admin:
            if size_difference > 0:
                dm_message = f"📈 Die Größe deines Teams **{team_name}** auf der Warteliste wurde von einem Administrator von {waitlist_size} auf {new_size} erhöht."
            else:
                dm_message = f"📉 Die Größe deines Teams **{team_name}** auf der Warteliste wurde von einem Administrator von {waitlist_size} auf {new_size} verringert."
            
            if reason:
                dm_message += f"\nGrund: {reason}"
            
            dm_message += f"\n\nFalls du Fragen hast, wende dich bitte an einen Administrator."
            await send_team_dm_notification(team_name, dm_message)
    
    else:
        # Team existiert nicht
        await interaction.response.send_message(
            f"Team {team_name} ist weder angemeldet noch auf der Warteliste.",
            ephemeral=True
        )
        return False
    
    # Speichere die Änderungen
    save_data(event_data, channel_id, user_team_assignments)
    
    # Aktualisiere die Event-Anzeige im Channel
    if channel_id:
        channel = bot.get_channel(interaction.channel_id)
        if channel:
            await send_event_details(channel)
    
    return True

async def process_waitlist_after_change(interaction, free_slots):
    """
    Verarbeitet die Warteliste, nachdem Slots frei geworden sind.
    
    Parameters:
    - interaction: Discord-Interaktion
    - free_slots: Anzahl der frei gewordenen Slots
    """
    event = get_event()
    if not event or free_slots <= 0 or not event["waitlist"]:
        return
    
    update_needed = False
    processed_teams = []
    
    while free_slots > 0 and event["waitlist"]:
        team_name, size = event["waitlist"][0]
        
        if size <= free_slots:
            # Das komplette Team kann nachrücken
            event["waitlist"].pop(0)
            event["slots_used"] += size
            event["teams"][team_name] = event["teams"].get(team_name, 0) + size
            free_slots -= size
            update_needed = True
            processed_teams.append((team_name, size))
        elif free_slots > 0:
            # Nur ein Teil des Teams kann nachrücken
            event["waitlist"][0] = (team_name, size - free_slots)
            event["slots_used"] += free_slots
            event["teams"][team_name] = event["teams"].get(team_name, 0) + free_slots
            processed_teams.append((team_name, free_slots))
            free_slots = 0
            update_needed = True
    
    if update_needed:
        save_data(event_data, channel_id, user_team_assignments)
        
        # Log für verarbeitete Warteliste
        if interaction and interaction.guild:
            initiator_name = getattr(interaction.user, "name", "System")
            log_message = f"⏫ Warteliste verarbeitet: {len(processed_teams)} Teams aufgerückt (initiiert von {initiator_name})"
            await send_to_log_channel(log_message, guild=interaction.guild)
        
        # Benachrichtigungen für aufgerückte Teams
        for team_name, moved_size in processed_teams:
            # Channel-Benachrichtigung
            if channel_id:
                channel = bot.get_channel(interaction.channel_id)
                if channel:
                    if moved_size == event["teams"][team_name]:
                        await channel.send(f"📢 Team {team_name} wurde komplett von der Warteliste in die Anmeldung aufgenommen!")
                    else:
                        await channel.send(f"📢 {moved_size} Spieler von Team {team_name} wurden von der Warteliste in die Anmeldung aufgenommen!")
            
            # Log für jedes aufgerückte Team
            if interaction and interaction.guild:
                team_log = f"📋 Team '{team_name}': {moved_size} Mitglieder von der Warteliste aufgerückt"
                await send_to_log_channel(team_log, level="INFO", guild=interaction.guild)
            
            # DM an Team-Repräsentanten
            requester = team_requester.get(team_name)
            if requester:
                try:
                    if moved_size == event["teams"][team_name]:
                        await requester.send(f"Gute Neuigkeiten! Dein Team {team_name} wurde komplett von der Warteliste in die Anmeldung für das Event '{event['name']}' aufgenommen.")
                    else:
                        await requester.send(f"Gute Neuigkeiten! {moved_size} Spieler deines Teams {team_name} wurden von der Warteliste in die Anmeldung für das Event '{event['name']}' aufgenommen.")
                except discord.errors.Forbidden:
                    logger.warning(f"Could not send DM to {requester}")
                    # Log für fehlgeschlagene DM
                    if interaction and interaction.guild:
                        await send_to_log_channel(
                            f"⚠️ Konnte keine DM an {requester.name} (Team {team_name}) senden", 
                            level="WARNING", 
                            guild=interaction.guild
                        )

async def admin_add_team(interaction, team_name, size, discord_user_id=None, discord_username=None, force_waitlist=False):
    """
    Funktion für Admins, um ein Team hinzuzufügen
    
    Parameters:
    - interaction: Discord-Interaktion
    - team_name: Name des Teams
    - size: Größe des Teams
    - discord_user_id: Optional - Discord-ID des Nutzers, der dem Team zugewiesen wird
    - discord_username: Optional - Username des Nutzers
    - force_waitlist: Ob das Team direkt auf die Warteliste gesetzt werden soll
    
    Returns:
    - True bei Erfolg, False bei Fehler
    """
    # Log-Eintrag für Admin-Aktion
    admin_name = getattr(interaction.user, "name", "Unbekannter Admin")
    await send_to_log_channel(
        f"👤 Admin-Aktion: {admin_name} versucht, Team '{team_name}' mit {size} Mitgliedern hinzuzufügen" + 
        (f" (direkt auf Warteliste)" if force_waitlist else ""),
        guild=interaction.guild
    )
    event = get_event()
    if not event:
        await interaction.response.send_message(
            "Es gibt derzeit kein aktives Event.",
            ephemeral=True
        )
        return False
    
    # Prüfe, ob das Team bereits existiert
    if team_name in event["teams"]:
        await interaction.response.send_message(
            f"Team {team_name} ist bereits angemeldet. Verwende die Team-Bearbeitung, um die Größe zu ändern.",
            ephemeral=True
        )
        return False
    
    # Prüfe, ob Team bereits auf der Warteliste steht
    for wl_team, _ in event["waitlist"]:
        if wl_team == team_name:
            await interaction.response.send_message(
                f"Team {team_name} steht bereits auf der Warteliste. Verwende die Team-Bearbeitung, um die Größe zu ändern.",
                ephemeral=True
            )
            return False
    
    max_team_size = event["max_team_size"]
    
    # Validiere Team-Größe
    if size <= 0 or size > max_team_size:
        await interaction.response.send_message(
            f"Die Teamgröße muss zwischen 1 und {max_team_size} liegen.",
            ephemeral=True
        )
        return False
    
    # Bestimme, ob auf Warteliste oder direktes Hinzufügen
    if force_waitlist:
        # Direkt auf Warteliste setzen
        event["waitlist"].append((team_name, size))
        
        # Setze Benutzer-Team-Zuweisung, wenn angegeben
        if discord_user_id:
            user_team_assignments[discord_user_id] = team_name
            team_requester[team_name] = await bot.fetch_user(int(discord_user_id))
        
        await interaction.response.send_message(
            f"Team {team_name} wurde mit {size} Personen auf die Warteliste gesetzt (Position {len(event['waitlist'])}).",
            ephemeral=True
        )
        
        # Log-Eintrag
        logger.info(f"Admin {interaction.user.name} hat Team {team_name} mit {size} Personen zur Warteliste hinzugefügt.")
        # Log zum Kanal senden
        await send_to_log_channel(
            f"📝 Admin {interaction.user.name} hat Team '{team_name}' mit {size} Personen zur Warteliste hinzugefügt.",
            guild=interaction.guild
        )
    else:
        # Prüfe, ob genügend Slots verfügbar sind
        available_slots = event["max_slots"] - event["slots_used"]
        
        if size <= available_slots:
            # Genügend Plätze verfügbar, direkt anmelden
            event["slots_used"] += size
            event["teams"][team_name] = size
            
            # Setze Benutzer-Team-Zuweisung, wenn angegeben
            if discord_user_id:
                user_team_assignments[discord_user_id] = team_name
            
            await interaction.response.send_message(
                f"Team {team_name} wurde mit {size} Personen angemeldet.",
                ephemeral=True
            )
            
            # Log-Eintrag
            logger.info(f"Admin {interaction.user.name} hat Team {team_name} mit {size} Personen angemeldet.")
            # Log zum Kanal senden
            await send_to_log_channel(
                f"✅ Admin {interaction.user.name} hat Team '{team_name}' mit {size} Personen angemeldet.",
                guild=interaction.guild
            )
        else:
            # Nicht genügend Plätze verfügbar
            if available_slots > 0:
                # Teilweise anmelden und Rest auf Warteliste
                waitlist_size = size - available_slots
                
                # Aktualisiere die angemeldete Teamgröße
                event["slots_used"] += available_slots
                event["teams"][team_name] = available_slots
                
                # Füge Rest zur Warteliste hinzu
                event["waitlist"].append((team_name, waitlist_size))
                
                # Setze Benutzer-Team-Zuweisung, wenn angegeben
                if discord_user_id:
                    user_team_assignments[discord_user_id] = team_name
                    team_requester[team_name] = await bot.fetch_user(int(discord_user_id))
                
                await interaction.response.send_message(
                    f"Team {team_name} wurde teilweise angemeldet. "
                    f"{available_slots} Spieler sind angemeldet und "
                    f"{waitlist_size} Spieler wurden auf die Warteliste gesetzt (Position {len(event['waitlist'])}).",
                    ephemeral=True
                )
                
                # Log-Eintrag
                logger.info(f"Admin {interaction.user.name} hat Team {team_name} teilweise angemeldet: {available_slots} angemeldet, {waitlist_size} auf Warteliste.")
                # Log zum Kanal senden
                await send_to_log_channel(
                    f"⚠️ Admin {interaction.user.name} hat Team '{team_name}' teilweise angemeldet: {available_slots} Mitglieder registriert, {waitlist_size} auf Warteliste.",
                    guild=interaction.guild
                )
            else:
                # Komplett auf Warteliste setzen
                event["waitlist"].append((team_name, size))
                
                # Setze Benutzer-Team-Zuweisung, wenn angegeben
                if discord_user_id:
                    user_team_assignments[discord_user_id] = team_name
                    team_requester[team_name] = await bot.fetch_user(int(discord_user_id))
                
                await interaction.response.send_message(
                    f"Team {team_name} wurde mit {size} Personen auf die Warteliste gesetzt (Position {len(event['waitlist'])}).",
                    ephemeral=True
                )
                
                # Log-Eintrag
                logger.info(f"Admin {interaction.user.name} hat Team {team_name} mit {size} Personen zur Warteliste hinzugefügt (keine Slots verfügbar).")
                # Log zum Kanal senden
                await send_to_log_channel(
                    f"📝 Admin {interaction.user.name} hat Team '{team_name}' mit {size} Personen zur Warteliste hinzugefügt (keine Slots verfügbar).",
                    guild=interaction.guild
                )
    
    # Speichere Änderungen
    save_data(event_data, channel_id, user_team_assignments)
    
    # Benachrichtigung für Discord-Benutzer, wenn angegeben
    if discord_user_id and discord_username:
        try:
            user = await bot.fetch_user(int(discord_user_id))
            if user:
                # Erstelle eine Benachrichtigung
                message = f"Hallo {discord_username}! Ein Admin hat dich dem Team **{team_name}** für das Event '{event['name']}' zugewiesen."
                
                if team_name in event["teams"]:
                    message += f" Das Team ist erfolgreich angemeldet mit {event['teams'][team_name]} Spielern."
                else:
                    # Suche in der Warteliste
                    for wl_team, wl_size in event["waitlist"]:
                        if wl_team == team_name:
                            message += f" Das Team steht auf der Warteliste (Position {event['waitlist'].index((wl_team, wl_size))+1}) mit {wl_size} Spielern."
                            break
                
                await user.send(message)
        except Exception as e:
            logger.warning(f"Konnte Benutzer {discord_user_id} nicht benachrichtigen: {e}")
    
    # Update channel with latest event details
    if channel_id:
        channel = bot.get_channel(interaction.channel_id)
        if channel:
            await send_event_details(channel)
    
    return True

async def send_event_details(channel, event=None):
    """Send event details to a channel with interactive buttons"""
    if event is None:
        event = get_event()
    
    try:
        embed = format_event_details(event)
        
        # Get the user's roles for button states
        has_admin = False
        has_clan_rep = False
        has_team = False
        team_name = None
        
        # Check if the message is for a specific user
        if hasattr(channel, 'author'):
            user = channel.author
            user_id = str(user.id)
            has_admin = has_role(user, ORGANIZER_ROLE)
            has_clan_rep = has_role(user, CLAN_REP_ROLE)
            team_name = user_team_assignments.get(user_id)
            has_team = team_name is not None
        
        # Add interactive buttons
        view = EventActionView(event, has_admin, has_clan_rep, has_team, team_name)
        
        if isinstance(embed, discord.Embed):
            await channel.send(embed=embed, view=view)
        else:
            await channel.send(embed, view=view)
    except Exception as e:
        logger.error(f"Error sending event details: {e}")
        # Fallback to plain text if embed fails
        await channel.send(format_event_list(event))

@bot.event
async def on_ready():
    """Handle bot ready event"""
    logger.info(f"Bot eingeloggt als {bot.user}")
    global channel_id
    
    # Initialisiere Log-Kanal
    from config import LOG_CHANNEL_NAME, LOG_CHANNEL_ID
    
    # Suche nach dem Log-Kanal in allen Guilds
    for guild in bot.guilds:
        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        
        # Wenn kein Log-Kanal gefunden wurde, versuche, einen zu erstellen (falls Berechtigungen vorhanden)
        if not log_channel:
            try:
                # Überprüfe, ob der Bot die erforderlichen Berechtigungen hat
                guild_me = guild.get_member(bot.user.id)
                if guild_me and guild_me.guild_permissions.manage_channels:
                    logger.info(f"Erstelle Log-Kanal '{LOG_CHANNEL_NAME}' in Guild '{guild.name}'")
                    # Erstelle einen neuen Kanal mit eingeschränkten Berechtigungen
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        guild_me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    }
                    # Finde die Orga-Rolle und gib ihr Leserechte
                    from config import ORGANIZER_ROLE
                    orga_role = discord.utils.get(guild.roles, name=ORGANIZER_ROLE)
                    if orga_role:
                        overwrites[orga_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)
                    
                    # Erstelle den Kanal
                    log_channel = await guild.create_text_channel(
                        LOG_CHANNEL_NAME,
                        overwrites=overwrites,
                        topic="Log-Kanal für den Event-Bot. Hier werden wichtige Ereignisse protokolliert."
                    )
                    logger.info(f"Log-Kanal '{LOG_CHANNEL_NAME}' erstellt in Guild '{guild.name}'")
                else:
                    logger.warning(f"Keine Berechtigung zum Erstellen eines Log-Kanals in Guild '{guild.name}'")
            except Exception as e:
                logger.error(f"Fehler beim Erstellen des Log-Kanals in Guild '{guild.name}': {e}")
        
        if log_channel:
            # Wenn gefunden oder erstellt, ID in der Konfiguration speichern
            import config
            config.LOG_CHANNEL_ID = log_channel.id
            logger.info(f"Log-Kanal initialisiert: {log_channel.name} (ID: {log_channel.id})")
            await send_to_log_channel(f"Event-Bot gestartet!", guild=guild)
            
            # Initialisiere globale Log-Kanal-Variable für andere Module
            from utils import discord_log_channel
            import utils
            utils.discord_log_channel = log_channel
            
            break
    
    # Initialisiere Hauptkanal
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            logger.info(f"Channel gefunden: {channel.name}")
            await channel.send("Event-Bot ist online und bereit!")
            await send_to_log_channel(f"Hauptkanal initialisiert: {channel.name} ({channel.id})")
        else:
            logger.warning("Gespeicherter Channel konnte nicht gefunden werden.")
            await send_to_log_channel("Gespeicherter Hauptkanal konnte nicht gefunden werden.", level="WARNING")
    else:
        logger.warning("Kein Channel gesetzt. Bitte nutze den Slash-Befehl /set_channel, um einen Channel zu definieren.")
        await send_to_log_channel("Kein Hauptkanal gesetzt. Bitte /set_channel verwenden.", level="WARNING")

    # Starte die Hintergrund-Tasks
    bot.loop.create_task(check_waitlist_and_expiry())
    bot.loop.create_task(process_log_queue())

async def process_log_queue():
    """Background task to process and send log messages to Discord channel"""
    await bot.wait_until_ready()
    
    # Warte, bis der Bot vollständig bereit ist
    await asyncio.sleep(5)
    
    while not bot.is_closed():
        try:
            # Wenn kein Discord-Kanal verfügbar ist, überspringe
            from utils import discord_log_channel
            if not discord_log_channel:
                await asyncio.sleep(10)
                continue
            
            # Hole Logs aus dem Handler (max. 5 auf einmal)
            logs = discord_handler.get_logs(5)
            
            if not logs:
                # Keine neuen Logs, kurze Pause
                await asyncio.sleep(1)
                continue
            
            # Kombiniere die Logs für eine Nachricht
            combined_message = ""
            
            for level, message in logs:
                # Formatiere die Nachricht je nach Log-Level
                if level == "INFO":
                    formatted_line = f"ℹ️ {message}\n"
                elif level == "WARNING":
                    formatted_line = f"⚠️ {message}\n"
                elif level == "ERROR":
                    formatted_line = f"❌ {message}\n"
                elif level == "CRITICAL":
                    formatted_line = f"🚨 {message}\n"
                else:
                    formatted_line = f"  {message}\n"
                
                combined_message += formatted_line
            
            # Sende die kombinierten Nachrichten
            if combined_message:
                try:
                    # Kürze die Nachricht, wenn sie zu lang ist
                    if len(combined_message) > 1900:
                        combined_message = combined_message[:1900] + "...\n(Nachricht gekürzt)"
                    
                    await discord_log_channel.send(f"```\n{combined_message}\n```")
                except Exception as e:
                    logger.error(f"Fehler beim Senden von Log-Nachrichten an Discord: {e}")
            
            # Kurze Pause, um Discord-Rate-Limits zu respektieren
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Fehler in process_log_queue: {e}")
            await asyncio.sleep(10)  # Längere Pause bei Fehlern

async def check_waitlist_and_expiry():
    """Background task to check waitlist and event expiry"""
    await bot.wait_until_ready()
    
    while not bot.is_closed():
        try:
            await asyncio.sleep(WAITLIST_CHECK_INTERVAL)
            event = get_event()

            if not event:
                continue

            # Check for event expiry
            if datetime.now() > event["expiry_date"]:
                logger.info("Event expired, removing it")
                
                event_name = event.get("name", "Unbekanntes Event")
                
                event_data.clear()
                save_data(event_data, channel_id, user_team_assignments)
                
                # Systemlognachricht zum Event-Ablauf
                for guild in bot.guilds:
                    await send_to_log_channel(
                        f"⏰ Event '{event_name}' ist automatisch abgelaufen und wurde aus dem System entfernt.",
                        level="INFO",
                        guild=guild
                    )
                
                if channel_id:
                    channel = bot.get_channel(channel_id)
                    if channel:
                        await channel.send("Das Event ist abgelaufen und wurde gelöscht.")
                continue

            # Check for free slots and process waitlist
            if event["slots_used"] < event["max_slots"] and event["waitlist"]:
                available_slots = event["max_slots"] - event["slots_used"]
                update_needed = False
                
                while available_slots > 0 and event["waitlist"]:
                    team_name, size = event["waitlist"][0]
                    
                    if size <= available_slots:
                        # Remove from waitlist and add to registered teams
                        event["waitlist"].pop(0)
                        event["slots_used"] += size
                        event["teams"][team_name] = event["teams"].get(team_name, 0) + size
                        available_slots -= size
                        update_needed = True
                        
                        # Notify team representative
                        if channel_id:
                            channel = bot.get_channel(channel_id)
                            if channel:
                                await channel.send(f"Team {team_name} wurde von der Warteliste in die Anmeldung aufgenommen!")
                        
                        requester = team_requester.get(team_name)
                        if requester:
                            try:
                                await requester.send(f"Gute Neuigkeiten! Dein Team {team_name} wurde von der Warteliste in die Anmeldung für das Event '{event['name']}' aufgenommen.")
                            except discord.errors.Forbidden:
                                logger.warning(f"Could not send DM to {requester}")
                    else:
                        break

                if update_needed:
                    save_data(event_data, channel_id, user_team_assignments)
                    
                    # Log für automatische Wartelisten-Verarbeitung
                    for guild in bot.guilds:
                        await send_to_log_channel(
                            f"⏫ Automatische Wartelisten-Verarbeitung: Teams wurden automatisch von der Warteliste aufgenommen",
                            level="INFO",
                            guild=guild
                        )
                    
                    if channel_id:
                        channel = bot.get_channel(channel_id)
                        if channel:
                            await send_event_details(channel)
        
        except Exception as e:
            logger.error(f"Error in waitlist check: {e}")

# Channel commands
@bot.tree.command(name="set_channel", description="Setzt den aktuellen Channel für Event-Updates")
async def set_channel(interaction: discord.Interaction):
    """Set the current channel for event updates"""
    # Überprüfe Berechtigungen
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("Du benötigst 'Kanäle verwalten'-Berechtigungen, um diesen Befehl zu nutzen.", ephemeral=True)
        return
        
    global channel_id
    channel_id = interaction.channel_id
    save_data(event_data, channel_id, user_team_assignments)
    
    # Log für Channel-Setzung
    await send_to_log_channel(
        f"📌 Event-Channel: {interaction.user.name} hat Channel '{interaction.channel.name}' (ID: {channel_id}) als Event-Channel festgelegt",
        guild=interaction.guild
    )
    
    await interaction.response.send_message(f"Dieser Channel ({interaction.channel.name}) wurde erfolgreich für Event-Interaktionen gesetzt.")
    logger.info(f"Channel gesetzt: {interaction.channel.name} (ID: {channel_id})")

# Event commands
@bot.tree.command(name="event", description="Erstellt ein neues Event (nur für Orga-Team)")
@app_commands.describe(
    name="Name des Events",
    date="Datum im Format TT.MM.JJJJ",
    time="Uhrzeit des Events",
    description="Beschreibung des Events"
)
async def create_event(interaction: discord.Interaction, name: str, date: str, time: str, description: str):
    """Create a new event"""
    # Überprüfe Rolle
    if not has_role(interaction.user, ORGANIZER_ROLE):
        await interaction.response.send_message(
            f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können Events erstellen.",
            ephemeral=True
        )
        return

    if get_event():
        await interaction.response.send_message("Es existiert bereits ein aktives Event. Bitte lösche es zuerst mit /delete_event.")
        return
    
    # Validate date format
    event_date = parse_date(date)
    if not event_date:
        await interaction.response.send_message("Ungültiges Datumsformat. Bitte verwende das Format TT.MM.JJJJ.")
        return
    
    # Create event
    event_data["event"] = {
        "name": name,
        "date": date,
        "time": time,
        "description": description,
        "teams": {},
        "waitlist": [],
        "max_slots": DEFAULT_MAX_SLOTS,
        "slots_used": 0,
        "max_team_size": DEFAULT_MAX_TEAM_SIZE,
        "expiry_date": event_date + timedelta(days=1)
    }

    save_data(event_data, channel_id, user_team_assignments)
    await interaction.response.send_message("Event erfolgreich erstellt!")
    
    # Log zum Erstellen des Events
    await send_to_log_channel(
        f"🆕 Event erstellt: '{name}' am {date} um {time} durch {interaction.user.name}",
        guild=interaction.guild
    )
    
    # Get channel after creating the event
    channel = bot.get_channel(interaction.channel_id)
    if channel:
        # Check roles for this specific user
        user_id = str(interaction.user.id)
        has_admin = has_role(interaction.user, ORGANIZER_ROLE)
        has_clan_rep = has_role(interaction.user, CLAN_REP_ROLE)
        team_name = user_team_assignments.get(user_id)
        has_team = team_name is not None
        
        # Create embed
        embed = format_event_details(get_event())
        view = EventActionView(get_event(), has_admin, has_clan_rep, has_team, team_name)
        
        await channel.send(embed=embed, view=view)

@bot.tree.command(name="delete_event", description="Löscht das aktuelle Event (nur für Orga-Team)")
async def delete_event(interaction: discord.Interaction):
    """Delete the current event"""
    # Überprüfe Rolle
    if not has_role(interaction.user, ORGANIZER_ROLE):
        await interaction.response.send_message(
            f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können Events löschen.", 
            ephemeral=True
        )
        return

    event = get_event()
    if not event:
        await interaction.response.send_message("Es gibt kein aktives Event zum Löschen.")
        return
    
    # Speichere den Event-Namen vor dem Löschen für das Log
    event_name = event.get("name", "Unbekanntes Event")
    
    # Event und zugehörige Daten löschen
    event_data.clear()
    team_requester.clear()  # Clear the team requester dictionary
    user_team_assignments.clear()  # Clear the team assignments when deleting an event
    save_data(event_data, channel_id, user_team_assignments)
    
    # Sende Benachrichtigung an den Log-Kanal
    await send_to_log_channel(
        f"🗑️ Event '{event_name}' wurde von {interaction.user.name} gelöscht.",
        guild=interaction.guild
    )
    
    await interaction.response.send_message("Event erfolgreich gelöscht.")

@bot.tree.command(name="show_event", description="Zeigt das aktuelle Event an")
async def show_event(interaction: discord.Interaction):
    """Show the current event"""
    event = get_event()
    if not event:
        await interaction.response.send_message("Es gibt derzeit kein aktives Event.")
        return
    # dd
    # Es gibt ein Event, zeige die Details mit Buttons
    await interaction.response.send_message("Hier sind die Event-Details:")
    
    # Get channel after sending initial response
    channel = bot.get_channel(interaction.channel_id)
    if channel:
        # Check roles for this specific user
        user_id = str(interaction.user.id)
        has_admin = has_role(interaction.user, ORGANIZER_ROLE)
        has_clan_rep = has_role(interaction.user, CLAN_REP_ROLE)
        team_name = user_team_assignments.get(user_id)
        has_team = team_name is not None
        
        # Create embed
        embed = format_event_details(event)
        view = EventActionView(event, has_admin, has_clan_rep, has_team, team_name)
        
        await channel.send(embed=embed, view=view)

# Registration commands
@bot.tree.command(name="reg", description="Meldet dein Team an oder ändert die Teamgröße (nur für Clan-Rep)")
@app_commands.describe(
    team_name="Name des Teams", 
    size="Anzahl der Teilnehmer (0 zum Entfernen des Teams)"
)
async def register_team(interaction: discord.Interaction, team_name: str, size: int):
    """Register a team or update team size. Size 0 unregisters the team."""
    # Überprüfe Rolle
    if not has_role(interaction.user, CLAN_REP_ROLE):
        await interaction.response.send_message(
            f"Nur Mitglieder mit der Rolle '{CLAN_REP_ROLE}' können Teams anmelden.",
            ephemeral=True
        )
        return

    event = get_event()
    if not event:
        await interaction.response.send_message("Es gibt derzeit kein aktives Event.", ephemeral=True)
        return

    team_name = team_name.strip().lower()
    max_team_size = event.get("max_team_size", 0)
    user_id = str(interaction.user.id)

    # Check if user is already assigned to another team
    if user_id in user_team_assignments and user_team_assignments[user_id] != team_name:
        assigned_team = user_team_assignments[user_id]
        await interaction.response.send_message(
            f"Du bist bereits dem Team '{assigned_team}' zugewiesen. Du kannst nur für ein Team anmelden.",
            ephemeral=True
        )
        return

    # Validate team size
    if size < 0 or size > max_team_size:
        await interaction.response.send_message(
            f"Die Teamgröße muss zwischen 0 und {max_team_size} liegen.",
            ephemeral=True
        )
        return

    # Remove team if size is 0
    if size == 0:
        # Prüfe, ob das Team angemeldet ist oder auf der Warteliste steht
        team_registered = team_name in event.get("teams", {})
        team_on_waitlist = False
        waitlist_index = -1
        
        for i, (wl_team, _) in enumerate(event.get("waitlist", [])):
            if wl_team == team_name:
                team_on_waitlist = True
                waitlist_index = i
                break
                
        if team_registered or team_on_waitlist:
            # Bestätigungsdialog anzeigen
            embed = discord.Embed(
                title="⚠️ Team wirklich abmelden?",
                description=f"Bist du sicher, dass du dein Team **{team_name}** abmelden möchtest?\n\n"
                           f"Diese Aktion kann nicht rückgängig gemacht werden!",
                color=discord.Color.red()
            )
            
            # Erstelle die Bestätigungsansicht
            view = TeamUnregisterConfirmationView(team_name, is_admin=False)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            # Log für Abmeldebestätigungsdialog
            status = "registriert" if team_registered else "auf der Warteliste"
            await send_to_log_channel(
                f"🔄 Abmeldungsprozess gestartet: {interaction.user.name} ({interaction.user.id}) will Team '{team_name}' abmelden (Status: {status})",
                level="INFO",
                guild=interaction.guild
            )
        else:
            await interaction.response.send_message(
                f"Team {team_name} ist weder angemeldet noch auf der Warteliste.",
                ephemeral=True
            )
    else:
        current_size = event["teams"].get(team_name, 0)
        size_difference = size - current_size
        
        # Check if adding or updating
        if size_difference > 0:
            # Check if enough slots are available
            if event["slots_used"] + size_difference > event["max_slots"]:
                available_slots = event["max_slots"] - event["slots_used"]
                if available_slots > 0:
                    # Teilweise anmelden und Rest auf Warteliste
                    waitlist_size = size_difference - available_slots
                    
                    # Aktualisiere die angemeldete Teamgröße
                    event["slots_used"] += available_slots
                    event["teams"][team_name] = current_size + available_slots
                    
                    # Füge Rest zur Warteliste hinzu
                    event["waitlist"].append((team_name, waitlist_size))
                    
                    # Nutzer diesem Team zuweisen
                    user_team_assignments[user_id] = team_name
                    
                    # Speichere für Benachrichtigungen
                    team_requester[team_name] = interaction.user
                    
                    await interaction.response.send_message(
                        f"Team {team_name} wurde teilweise angemeldet. "
                        f"{current_size + available_slots} Spieler sind angemeldet und "
                        f"{waitlist_size} Spieler wurden auf die Warteliste gesetzt (Position {len(event['waitlist'])})."
                    )
                else:
                    # Komplett auf Warteliste setzen
                    event["waitlist"].append((team_name, size))
                    
                    # Nutzer diesem Team zuweisen
                    user_team_assignments[user_id] = team_name
                    
                    # Speichere für Benachrichtigungen
                    team_requester[team_name] = interaction.user
                    
                    await interaction.response.send_message(
                        f"Team {team_name} wurde mit {size} Personen auf die Warteliste gesetzt (Position {len(event['waitlist'])})."
                    )
            else:
                # Genügend Plätze vorhanden, normal anmelden
                event["slots_used"] += size_difference
                event["teams"][team_name] = size
                
                # Assign user to this team
                user_team_assignments[user_id] = team_name
                
                # Log für Team-Anmeldung
                await send_to_log_channel(
                    f"👥 Team angemeldet: {interaction.user.name} hat Team '{team_name}' mit {size} Mitgliedern angemeldet",
                    guild=interaction.guild
                )
                
                await interaction.response.send_message(f"Team {team_name} wurde mit {size} Personen angemeldet.")
        elif size_difference < 0:
            # Reduce team size
            event["slots_used"] += size_difference  # Will be negative
            event["teams"][team_name] = size
            await interaction.response.send_message(f"Teamgröße für {team_name} wurde auf {size} aktualisiert.")
            
            # Freie Plätze für Warteliste nutzen
            free_slots = -size_difference
            await process_waitlist_after_change(interaction, free_slots)
        else:
            # Size unchanged
            await interaction.response.send_message(f"Team {team_name} ist bereits mit {size} Personen angemeldet.")
    
    # Save data after any changes
    save_data(event_data, channel_id, user_team_assignments)
    
    # Update channel with latest event details
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            await send_event_details(channel)

# Der /wl-Befehl wurde entfernt, da die Warteliste jetzt automatisch vom Bot verwaltet wird

@bot.tree.command(name="open_reg", description="Erhöht die maximale Teamgröße (nur für Orga-Team)")
async def open_registration(interaction: discord.Interaction):
    """Increase the maximum team size (admin only)"""
    # Überprüfe Rolle
    if not has_role(interaction.user, ORGANIZER_ROLE):
        await interaction.response.send_message(
            f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können die Registrierung öffnen.",
            ephemeral=True
        )
        return

    event = get_event()
    if not event:
        await interaction.response.send_message("Es gibt derzeit kein aktives Event.")
        return
    
    if event["max_team_size"] >= EXPANDED_MAX_TEAM_SIZE:
        await interaction.response.send_message(
            f"Die maximale Teamgröße ist bereits auf das Maximum von {EXPANDED_MAX_TEAM_SIZE} gesetzt."
        )
        return
    
    # Set the expanded team size
    event["max_team_size"] = EXPANDED_MAX_TEAM_SIZE
    save_data(event_data, channel_id, user_team_assignments)
    
    # Log für die Erhöhung der maximalen Teamgröße
    await send_to_log_channel(
        f"⬆️ Teamgröße erhöht: Admin {interaction.user.name} hat die maximale Teamgröße für Event '{event['name']}' auf {EXPANDED_MAX_TEAM_SIZE} erhöht",
        guild=interaction.guild
    )
    
    await interaction.response.send_message(
        f"Die maximale Teamgröße wurde auf {EXPANDED_MAX_TEAM_SIZE} erhöht."
    )
    
    # Announce in the event channel
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(
                f"📢 **Ankündigung**: Die maximale Teamgröße für das Event '{event['name']}' wurde auf {EXPANDED_MAX_TEAM_SIZE} erhöht!"
            )
            await send_event_details(channel)

@bot.tree.command(name="reset_team_assignment", description="Setzt die Team-Zuweisung eines Nutzers zurück (nur für Orga-Team)")
@app_commands.describe(
    user="Der Nutzer, dessen Team-Zuweisung zurückgesetzt werden soll"
)
async def reset_team_assignment(interaction: discord.Interaction, user: discord.User):
    """Reset a user's team assignment (admin only)"""
    # Überprüfe Rolle
    if not has_role(interaction.user, ORGANIZER_ROLE):
        await interaction.response.send_message(
            f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können diese Aktion ausführen.",
            ephemeral=True
        )
        return

    user_id = str(user.id)
    
    if user_id not in user_team_assignments:
        await interaction.response.send_message(f"{user.display_name} ist keinem Team zugewiesen.")
        return
    
    team_name = user_team_assignments[user_id]
    del user_team_assignments[user_id]
    save_data(event_data, channel_id, user_team_assignments)
    
    # Log für Zurücksetzen der Team-Zuweisung
    await send_to_log_channel(
        f"🔄 Team-Zuweisung zurückgesetzt: Admin {interaction.user.name} hat die Zuweisung von {user.display_name} zum Team '{team_name}' entfernt",
        guild=interaction.guild
    )
    
    await interaction.response.send_message(
        f"Team-Zuweisung für {user.display_name} (Team {team_name}) wurde zurückgesetzt."
    )
    
    # Try to notify the user
    try:
        await user.send(
            f"Deine Team-Zuweisung (Team {team_name}) wurde von einem Administrator zurückgesetzt. "
            f"Du kannst dich nun einem anderen Team anschließen."
        )
    except discord.errors.Forbidden:
        # User has DMs disabled, continue silently
        pass

# Team List and CSV Export Commands
@bot.tree.command(name="team_list", description="Zeigt eine schön formatierte Liste aller angemeldeten Teams")
async def team_list(interaction: discord.Interaction):
    """Display a formatted list of all registered teams"""
    event = get_event()
    if not event:
        await interaction.response.send_message("Es gibt derzeit kein aktives Event.")
        return
    
    # Create formatted team list embed
    embed = discord.Embed(
        title=f"Teamliste für {event['name']}",
        description=f"Datum: {event['date']} | Uhrzeit: {event['time']}",
        color=discord.Color.blue()
    )
    
    # Add registered teams section
    if event["teams"]:
        registered_text = ""
        for idx, (team_name, size) in enumerate(sorted(event["teams"].items()), 1):
            registered_text += f"**{idx}.** {team_name.capitalize()} - {size} Mitglieder\n"
        
        embed.add_field(
            name=f"📋 Angemeldete Teams ({event['slots_used']}/{event['max_slots']} Slots)",
            value=registered_text,
            inline=False
        )
    else:
        embed.add_field(
            name=f"📋 Angemeldete Teams (0/{event['max_slots']} Slots)",
            value="Noch keine Teams angemeldet.",
            inline=False
        )
    
    # Add waitlist section
    if event["waitlist"]:
        waitlist_text = ""
        for idx, (team_name, size) in enumerate(event["waitlist"], 1):
            waitlist_text += f"**{idx}.** {team_name.capitalize()} - {size} Mitglieder\n"
        
        embed.add_field(
            name="⏳ Warteliste",
            value=waitlist_text,
            inline=False
        )
    else:
        embed.add_field(
            name="⏳ Warteliste",
            value="Keine Teams auf der Warteliste.",
            inline=False
        )
    
    # Add statistics
    available_slots = event["max_slots"] - event["slots_used"]
    embed.add_field(
        name="📊 Statistik",
        value=f"Anzahl Teams: **{len(event['teams'])}**\n"
              f"Verfügbare Slots: **{available_slots}**\n"
              f"Warteliste: **{len(event['waitlist'])}** Teams\n"
              f"Max. Teamgröße: **{event['max_team_size']}**",
        inline=False
    )
    
    embed.set_footer(text=f"Erstellt am {datetime.now().strftime('%d.%m.%Y um %H:%M')} Uhr")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="export_csv", description="Exportiert die Teamliste als CSV-Datei (nur für Orga-Team)")
async def export_csv(interaction: discord.Interaction):
    """Export team data as CSV file"""
    # Überprüfe Berechtigung
    if not has_role(interaction.user, ORGANIZER_ROLE):
        await interaction.response.send_message(
            f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können Team-Daten exportieren.",
            ephemeral=True
        )
        return
    
    event = get_event()
    if not event:
        await interaction.response.send_message("Es gibt derzeit kein aktives Event.")
        return
    
    # Create CSV in memory
    output = io.StringIO()
    csv_writer = csv.writer(output)
    
    # Write header
    csv_writer.writerow(["Team", "Größe", "Status"])
    
    # Write registered teams
    for team_name, size in event["teams"].items():
        csv_writer.writerow([team_name, size, "Angemeldet"])
    
    # Write waitlist teams
    for team_name, size in event["waitlist"]:
        csv_writer.writerow([team_name, size, "Warteliste"])
    
    # Reset stream position to start
    output.seek(0)
    
    # Create discord file object
    event_date = event["date"].replace(".", "-")
    filename = f"teams_{event_date}.csv"
    file = discord.File(fp=io.BytesIO(output.getvalue().encode('utf-8')), filename=filename)
    
    await interaction.response.send_message(f"Hier ist die exportierte Teamliste für {event['name']}:", file=file)

@bot.tree.command(name="help", description="Zeigt Hilfe zu den verfügbaren Befehlen")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    # Create help embed
    embed = discord.Embed(
        title="📚 Event-Bot Hilfe",
        description="Hier sind die verfügbaren Befehle:",
        color=discord.Color.blue()
    )
    
    # Get user roles
    is_admin = has_role(interaction.user, ORGANIZER_ROLE)
    is_clan_rep = has_role(interaction.user, CLAN_REP_ROLE)
    
    # Basic commands for everyone
    embed.add_field(
        name="🔍 Allgemeine Befehle",
        value=(
            "• `/help` - Zeigt diese Hilfe an\n"
            "• `/show_event` - Zeigt das aktuelle Event an\n"
        ),
        inline=False
    )
    
    # Commands for clan reps
    if is_clan_rep:
        embed.add_field(
            name="👥 Team-Verwaltung (für Clan-Rep)",
            value=(
                f"• `/reg [team_name] [size]` - Meldet dein Team an oder ändert die Teamgröße\n"
                f"Die Warteliste wird automatisch vom Bot verwaltet, wenn nicht genügend Slots verfügbar sind.\n"
            ),
            inline=False
        )
    
    # Commands for admins
    if is_admin:
        embed.add_field(
            name="⚙️ Admin-Befehle (nur für Orga-Team)",
            value=(
                "• `/set_channel` - Setzt den aktuellen Channel für Event-Updates\n"
                "• `/event [name] [date] [time] [description]` - Erstellt ein neues Event\n"
                "• `/delete_event` - Löscht das aktuelle Event\n"
                "• `/open_reg` - Erhöht die maximale Teamgröße\n"
                "• `/reset_team_assignment [user]` - Setzt die Team-Zuweisung eines Nutzers zurück\n"
                "• Admin-Menü: Teams verwalten, bearbeiten und hinzufügen\n"
            ),
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="wl", description="Setze dein Team auf die Warteliste")
async def waitlist_command(interaction: discord.Interaction, team_name: str, size: int):
    """Setzt ein Team auf die Warteliste"""
    # Hole das aktive Event
    event = get_event()
    if not event:
        await interaction.response.send_message(
            "Es gibt derzeit kein aktives Event.",
            ephemeral=True
        )
        return
    
    # Definiere user_id aus der Interaktion
    user_id = str(interaction.user.id)
    
    # Prüfe, ob der Nutzer die Clan-Rep Rolle hat
    if not has_role(interaction.user, CLAN_REP_ROLE) and not has_role(interaction.user, ORGANIZER_ROLE):
        await interaction.response.send_message(
            f"Du benötigst die '{CLAN_REP_ROLE}' Rolle, um ein Team auf die Warteliste zu setzen.",
            ephemeral=True
        )
        return
    
    # Prüfe, ob der Nutzer bereits einem anderen Team zugewiesen ist
    if user_id in user_team_assignments and user_team_assignments[user_id] != team_name:
        assigned_team = user_team_assignments[user_id]
        await interaction.response.send_message(
            f"Du bist bereits dem Team '{assigned_team}' zugewiesen. Du kannst nur für ein Team anmelden.",
            ephemeral=True
        )
        return
    
    # Validiere Team-Größe
    max_team_size = event["max_team_size"]
    if size <= 0 or size > max_team_size:
        await interaction.response.send_message(
            f"Die Teamgröße muss zwischen 1 und {max_team_size} liegen.",
            ephemeral=True
        )
        return
    
    # Prüfe, ob das Team schon angemeldet ist
    if team_name in event["teams"]:
        await interaction.response.send_message(
            f"Das Team '{team_name}' ist bereits angemeldet und nicht auf der Warteliste.",
            ephemeral=True
        )
        return
    
    # Prüfe, ob das Team bereits auf der Warteliste steht
    team_on_waitlist = False
    waitlist_index = -1
    waitlist_team_size = 0
    
    for i, (wl_team, wl_size) in enumerate(event["waitlist"]):
        if wl_team == team_name:
            team_on_waitlist = True
            waitlist_index = i
            waitlist_team_size = wl_size
            break
    
    if team_on_waitlist:
        # Team ist bereits auf der Warteliste - aktualisiere die Größe
        event["waitlist"][waitlist_index] = (team_name, size)
        await interaction.response.send_message(
            f"Team '{team_name}' wurde aktualisiert und behält Position {waitlist_index+1} auf der Warteliste mit {size} Spielern.",
            ephemeral=True
        )
        
        # Log eintragen
        await send_to_log_channel(
            f"⏳ Warteliste aktualisiert: {interaction.user.name} hat die Größe von Team '{team_name}' auf der Warteliste auf {size} aktualisiert",
            level="INFO",
            guild=interaction.guild
        )
    else:
        # Füge das Team zur Warteliste hinzu
        event["waitlist"].append((team_name, size))
        
        # Speichere Benutzer für Benachrichtigungen
        team_requester[team_name] = interaction.user
        
        # Nutzer diesem Team zuweisen
        user_team_assignments[user_id] = team_name
        
        await interaction.response.send_message(
            f"Team '{team_name}' wurde zur Warteliste hinzugefügt (Position {len(event['waitlist'])}) mit {size} Spielern.",
            ephemeral=True
        )
        
        # Log eintragen
        await send_to_log_channel(
            f"⏳ Warteliste: {interaction.user.name} hat Team '{team_name}' mit {size} Spielern zur Warteliste hinzugefügt",
            level="INFO",
            guild=interaction.guild
        )
    
    # Speichere Daten
    save_data(event_data, channel_id, user_team_assignments)
    
    # Channel aktualisieren
    if channel_id:
        channel = bot.get_channel(interaction.channel_id)
        if channel:
            await send_event_details(channel)

@bot.tree.command(name="unregister", description="Meldet dein Team vom Event ab")
async def unregister_command(interaction: discord.Interaction, team_name: str = None):
    """Melde dein Team vom Event ab"""
    # Hole das aktive Event
    event = get_event()
    if not event:
        await interaction.response.send_message(
            "Es gibt derzeit kein aktives Event.",
            ephemeral=True
        )
        return
    
    # Definiere user_id aus der Interaktion
    user_id = str(interaction.user.id)
    
    # Wenn kein Team-Name angegeben wurde, versuche das zugeordnete Team zu finden
    if not team_name:
        if user_id in user_team_assignments:
            team_name = user_team_assignments[user_id]
        else:
            await interaction.response.send_message(
                "Du bist keinem Team zugeordnet und hast keinen Team-Namen angegeben.",
                ephemeral=True
            )
            return
    
    # Prüfe Berechtigungen
    is_admin = has_role(interaction.user, ORGANIZER_ROLE)
    is_assigned_to_team = (user_id in user_team_assignments and user_team_assignments[user_id] == team_name)
    
    if not is_admin and not is_assigned_to_team:
        await interaction.response.send_message(
            f"Du kannst nur dein eigenes Team abmelden, oder benötigst die '{ORGANIZER_ROLE}' Rolle.",
            ephemeral=True
        )
        return
    
    # Bestätigungsansicht erstellen
    view = TeamUnregisterConfirmationView(team_name, is_admin)
    
    await interaction.response.send_message(
        f"Bist du sicher, dass du das Team '{team_name}' abmelden möchtest?",
        view=view,
        ephemeral=True
    )

@bot.tree.command(name="update", description="Aktualisiert die Details des aktuellen Events")
async def update_command(interaction: discord.Interaction):
    """Aktualisiert die Event-Details im Kanal"""
    # Nur das Orga-Team darf das ausführen
    if not has_role(interaction.user, ORGANIZER_ROLE):
        await interaction.response.send_message(
            f"Du benötigst die '{ORGANIZER_ROLE}' Rolle, um diese Aktion auszuführen.",
            ephemeral=True
        )
        return
    
    # Prüfe, ob ein aktives Event existiert
    event = get_event()
    if not event:
        await interaction.response.send_message(
            "Es gibt derzeit kein aktives Event.",
            ephemeral=True
        )
        return
    
    # Prüfe, ob ein Kanal gesetzt wurde
    if not channel_id:
        await interaction.response.send_message(
            "Es wurde noch kein Kanal gesetzt. Bitte verwende /set_channel, um einen Kanal festzulegen.",
            ephemeral=True
        )
        return
    
    channel = bot.get_channel(channel_id)
    if not channel:
        await interaction.response.send_message(
            "Der gespeicherte Kanal konnte nicht gefunden werden. Bitte setze den Kanal neu mit /set_channel.",
            ephemeral=True
        )
        return
    
    # Aktualisiere die Event-Details im Kanal
    await send_event_details(channel)
    
    await interaction.response.send_message(
        "Die Event-Details wurden im Kanal aktualisiert.",
        ephemeral=True
    )

@bot.tree.command(name="edit", description="Bearbeitet die Größe deines Teams")
async def edit_command(interaction: discord.Interaction):
    """Bearbeite die Größe deines Teams"""
    # Hole das aktive Event
    event = get_event()
    if not event:
        await interaction.response.send_message(
            "Es gibt derzeit kein aktives Event.",
            ephemeral=True
        )
        return
    
    # Definiere user_id aus der Interaktion
    user_id = str(interaction.user.id)
    
    # Prüfe, ob der Nutzer einem Team zugewiesen ist
    if user_id not in user_team_assignments:
        await interaction.response.send_message(
            "Du bist keinem Team zugewiesen und kannst daher keine Teamgröße bearbeiten.",
            ephemeral=True
        )
        return
    
    # Hole den Team-Namen
    team_name = user_team_assignments[user_id]
    
    # Prüfe, ob das Team angemeldet oder auf der Warteliste ist
    team_registered = team_name in event["teams"]
    team_on_waitlist = False
    team_size = 0
    
    if team_registered:
        team_size = event["teams"][team_name]
    else:
        # Prüfe, ob das Team auf der Warteliste steht
        for wl_team, wl_size in event["waitlist"]:
            if wl_team == team_name:
                team_on_waitlist = True
                team_size = wl_size
                break
    
    if not team_registered and not team_on_waitlist:
        await interaction.response.send_message(
            f"Team '{team_name}' ist weder angemeldet noch auf der Warteliste.",
            ephemeral=True
        )
        return
    
    # Erstelle ein Modal zum Bearbeiten der Teamgröße
    modal = TeamEditModal(team_name, team_size, event["max_team_size"])
    await interaction.response.send_modal(modal)

@bot.tree.command(name="close", description="Schließt die Anmeldungen für das aktuelle Event (nur für Orga-Team)")
async def close_command(interaction: discord.Interaction):
    """Schließt die Anmeldungen für das Event"""
    # Nur das Orga-Team darf das ausführen
    if not has_role(interaction.user, ORGANIZER_ROLE):
        await interaction.response.send_message(
            f"Du benötigst die '{ORGANIZER_ROLE}' Rolle, um diese Aktion auszuführen.",
            ephemeral=True
        )
        return
    
    # Prüfe, ob ein aktives Event existiert
    event = get_event()
    if not event:
        await interaction.response.send_message(
            "Es gibt derzeit kein aktives Event.",
            ephemeral=True
        )
        return
    
    # Setze die verfügbaren Slots auf die aktuell verwendeten Slots
    event["max_slots"] = event["slots_used"]
    
    # Speichere die Änderungen
    save_data(event_data, channel_id, user_team_assignments)
    
    await interaction.response.send_message(
        f"Die Anmeldungen für das Event '{event['name']}' wurden geschlossen. Neue Teams können nur noch auf die Warteliste.",
        ephemeral=True
    )
    
    # Log eintragen
    await send_to_log_channel(
        f"🔒 Event geschlossen: {interaction.user.name} hat die Anmeldungen für das Event '{event['name']}' geschlossen",
        level="INFO",
        guild=interaction.guild
    )
    
    # Aktualisiere die Event-Details im Kanal
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            await send_event_details(channel)

@bot.tree.command(name="find", description="Findet ein Team oder einen Spieler im Event")
async def find_command(interaction: discord.Interaction, search_term: str):
    """Findet ein Team oder einen Spieler im Event"""
    # Hole das aktive Event
    event = get_event()
    if not event:
        await interaction.response.send_message(
            "Es gibt derzeit kein aktives Event.",
            ephemeral=True
        )
        return
    
    search_term = search_term.lower()
    results = []
    
    # Suche in registrierten Teams
    for team_name, size in event["teams"].items():
        if search_term in team_name.lower():
            results.append(f"✅ **{team_name}**: {size} {'Person' if size == 1 else 'Personen'} (Angemeldet)")
    
    # Suche in Warteliste
    for i, (team_name, size) in enumerate(event["waitlist"]):
        if search_term in team_name.lower():
            results.append(f"⏳ **{team_name}**: {size} {'Person' if size == 1 else 'Personen'} (Warteliste Position {i+1})")
    
    # Suche nach zugewiesenen Benutzern (Discord-ID -> Team)
    user_results = []
    for user_id, team_name in user_team_assignments.items():
        # Versuche, den Benutzer zu finden
        try:
            user = await bot.fetch_user(int(user_id))
            if search_term in user.name.lower() or search_term in str(user.id):
                # Prüfe, ob das Team angemeldet oder auf der Warteliste ist
                if team_name in event["teams"]:
                    user_results.append(f"👤 **{user.name}** (ID: {user.id}) ist in Team **{team_name}** (Angemeldet)")
                else:
                    # Prüfe auf Warteliste
                    for i, (wl_team, _) in enumerate(event["waitlist"]):
                        if wl_team == team_name:
                            user_results.append(f"👤 **{user.name}** (ID: {user.id}) ist in Team **{team_name}** (Warteliste Position {i+1})")
                            break
        except:
            # Bei Fehler einfach überspringen
            pass
    
    # Kombiniere die Ergebnisse
    results.extend(user_results)
    
    if results:
        # Erstelle eine Nachricht mit allen Ergebnissen
        message = f"**🔍 Suchergebnisse für '{search_term}':**\n\n" + "\n".join(results)
        
        # Wenn die Nachricht zu lang ist, kürze sie
        if len(message) > 1900:
            message = message[:1900] + "...\n(Weitere Ergebnisse wurden abgeschnitten)"
        
        await interaction.response.send_message(message, ephemeral=True)
    else:
        await interaction.response.send_message(
            f"Keine Ergebnisse für '{search_term}' gefunden.",
            ephemeral=True
        )



@bot.tree.command(name="export_teams", description="Exportiert die Teamliste als CSV-Datei (nur für Orga-Team)")
async def export_teams(interaction: discord.Interaction):
    """Exportiert alle Teams als CSV-Datei"""
    # Überprüfe Berechtigung
    if not has_role(interaction.user, ORGANIZER_ROLE):
        await interaction.response.send_message(
            f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können diese Aktion ausführen.",
            ephemeral=True
        )
        return
    
    event = get_event()
    if not event:
        await interaction.response.send_message("Es gibt derzeit kein aktives Event.")
        return
        
    # Erstelle CSV-Inhalt im Speicher
    import io
    import csv
    from datetime import datetime
    
    csv_file = io.StringIO()
    csv_writer = csv.writer(csv_file)
    
    # Schreibe Header
    csv_writer.writerow(["Typ", "Teamname", "Größe", "Teamleiter-Discord-ID", "Registrierungsdatum"])
    
    # Schreibe angemeldete Teams
    for team_name, size in event["teams"].items():
        # Finde Team-Leiter (suche ersten Nutzer mit diesem Team)
        leader_id = "Unbekannt"
        for user_id, assigned_team in user_team_assignments.items():
            if assigned_team == team_name:
                leader_id = user_id
                break
        
        csv_writer.writerow(["Angemeldet", team_name, size, leader_id, ""])
    
    # Schreibe Warteliste
    for i, (team_name, size) in enumerate(event["waitlist"]):
        # Finde Team-Leiter (suche ersten Nutzer mit diesem Team)
        leader_id = "Unbekannt"
        for user_id, assigned_team in user_team_assignments.items():
            if assigned_team == team_name:
                leader_id = user_id
                break
        
        csv_writer.writerow(["Warteliste", team_name, size, leader_id, ""])
    
    # Zurück zum Anfang der Datei
    csv_file.seek(0)
    
    # Aktuelle Zeit für den Dateinamen
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"teamliste_{current_time}.csv"
    
    # Log für CSV-Export
    await send_to_log_channel(
        f"📊 CSV-Export: Admin {interaction.user.name} hat eine CSV-Datei der Teams für Event '{event['name']}' exportiert",
        guild=interaction.guild
    )
    
    # Sende Datei als Anhang
    await interaction.response.send_message(
        f"Hier ist die Teamliste für das Event '{event['name']}':",
        file=discord.File(fp=csv_file, filename=filename)
    )

# Start the bot
if __name__ == "__main__":
    logger.info("Starting bot...")
    bot.run(TOKEN)