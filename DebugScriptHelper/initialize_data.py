#!/usr/bin/env python3

import pickle
import os

# Default empty event data structure
default_data = {
    'event_data': {
        'event': {
            'name': None,
            'date': None,
            'time': None,
            'description': None,
            'max_slots': 96,
            'max_team_size': 9,
            'slots_used': 0,
            'teams': {},
            'waitlist': []
        }
    },
    'channel_id': None,
    'user_team_assignments': {}
}

# Save to pickle file
SAVE_FILE = "event_data.pkl"

def initialize_data():
    """Initialize event data pickle file with default structure"""
    try:
        # Check if file already exists
        if os.path.exists(SAVE_FILE):
            print(f"WARNING: {SAVE_FILE} already exists. This will overwrite the existing file.")
            choice = input("Do you want to continue? (y/n): ")
            if choice.lower() != 'y':
                print("Initialization cancelled.")
                return False
            
            # Make a backup just in case
            backup_file = f"{SAVE_FILE}.bak.before_init"
            try:
                with open(SAVE_FILE, 'rb') as f_old, open(backup_file, 'wb') as f_backup:
                    f_backup.write(f_old.read())
                print(f"Created backup of existing data file to {backup_file}")
            except Exception as backup_err:
                print(f"Failed to create backup before initialization: {backup_err}")
        
        # Create the pickle file with default structure
        with open(SAVE_FILE, 'wb') as f:
            pickle.dump(default_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        print(f"Successfully initialized {SAVE_FILE} with default empty structure.")
        return True
    
    except Exception as e:
        print(f"Error initializing data: {e}")
        return False

if __name__ == "__main__":
    initialize_data()