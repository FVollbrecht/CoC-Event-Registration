#!/usr/bin/env python

"""
Dieses Skript entfernt die doppelte 'init' Funktion, da sie nur ein Alias für 'set_channel' ist.
Stattdessen erweitert es die Beschreibung für 'set_channel', um klarzustellen, dass dieser Befehl
auch für die Initialisierung des Bots verwendet werden soll.
"""

def fix_init_command():
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Suche nach der init_command-Funktion und entferne sie
    import re
    
    # Suche nach dem Anfangsmuster der init_command-Funktion
    pattern = r'@bot\.tree\.command\(name="init".*?\)[\s\S]*?async def init_command\(interaction: discord\.Interaction\):[\s\S]*?await set_channel\(interaction\)'
    
    # Entferne die init_command-Funktion
    new_content = re.sub(pattern, '', content)
    
    # Aktualisiere die Beschreibung der set_channel-Funktion
    set_channel_pattern = r'@bot\.tree\.command\(name="set_channel", description="Setzt den aktuellen Kanal für Event-Updates"\)'
    set_channel_replacement = '@bot.tree.command(name="set_channel", description="Setzt den aktuellen Kanal für Event-Updates und initialisiert den Bot")'
    
    new_content = new_content.replace(set_channel_pattern, set_channel_replacement)
    
    # Schreibe die Änderungen zurück in die Datei
    if new_content != content:
        with open('bot.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

if __name__ == "__main__":
    result = fix_init_command()
    if result:
        print("Die init_command-Funktion wurde erfolgreich entfernt und die set_channel-Beschreibung wurde aktualisiert.")
    else:
        print("Es wurden keine Änderungen vorgenommen. Die Funktionen wurden nicht gefunden oder sind bereits optimiert.")