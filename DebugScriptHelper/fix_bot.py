#!/usr/bin/env python

with open('bot.py', 'r') as f:
    content = f.read()

# Ersetzen der get_event() Funktion
new_content = content.replace(
    'def get_event():\n    """Get the current event data"""\n    return event_data.get("event")',
    'def get_event():\n    """Get the current event data"""\n    return event_data  # event_data ist bereits das Event-Dictionary'
)

if new_content != content:
    with open('bot.py', 'w') as f:
        f.write(new_content)
    print("Die get_event()-Funktion wurde erfolgreich aktualisiert.")
else:
    print("Der Text wurde nicht gefunden. Keine Änderungen vorgenommen.")