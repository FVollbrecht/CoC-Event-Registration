#!/usr/bin/env python

def fix_export_commands():
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Suche nach der export_teams-Funktion und entferne sie
    import re
    
    # Suche nach dem Anfangsmuster der export_teams-Funktion
    pattern = r'@bot\.tree\.command\(name="export_teams".*?\)[\s\S]*?async def export_teams\(interaction: discord\.Interaction\):[\s\S]*?await interaction\.response\.send_message\(.*?file=file\)'
    
    # Suche und entferne die zweite Exportfunktion
    new_content = re.sub(pattern, '', content)
    
    # Aktualisiere die Berechtigungsprüfung in der verbleibenden export_csv Funktion
    replacement = """    # Überprüfe Berechtigung
    if not has_role(interaction.user, ORGANIZER_ROLE):
        await interaction.response.send_message(
            f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können Team-Daten exportieren.",
            ephemeral=True
        )
        return"""
    
    current_permission_check = """    # Überprüfe Rolle
    if not any(role.name == ORGANIZER_ROLE for role in interaction.user.roles):
        await interaction.response.send_message(
            f"Nur Mitglieder mit der Rolle '{ORGANIZER_ROLE}' können Team-Daten exportieren.",
            ephemeral=True
        )
        return"""
    
    new_content = new_content.replace(current_permission_check, replacement)
    
    # Schreibe die Änderungen zurück in die Datei
    if new_content != content:
        with open('bot.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

if __name__ == "__main__":
    result = fix_export_commands()
    if result:
        print("Die export_teams-Funktion wurde erfolgreich entfernt und die Berechtigungsprüfung in export_csv wurde aktualisiert.")
    else:
        print("Es wurden keine Änderungen vorgenommen. Die Funktionen wurden nicht gefunden oder sind bereits optimiert.")