import pickle

# Load the data
with open('event_data.pkl', 'rb') as f:
    data = pickle.load(f)

print("Keys in data:", data.keys())
print("\nFull data structure:")
for key, value in data.items():
    print(f"- {key}: {type(value)}")
    if isinstance(value, dict):
        print(f"  - Dict keys: {value.keys()}")
    elif isinstance(value, list):
        print(f"  - List length: {len(value)}")
    else:
        print(f"  - Value: {value}")

print("\nEvent data:")
event_data = data.get('event_data', {})
if event_data:
    print(f"Event data type: {type(event_data)}")
    print(f"Event data: {event_data}")
    
    # Check if there's an event key inside event_data
    event = event_data.get('event', {})
    if event:
        print(f"\nEvent details:")
        print(f"- Name: {event.get('name', 'None')}")
        print(f"- Date: {event.get('date', 'None')}")
        print(f"- Teams: {len(event.get('teams', {}))}")
        print(f"- Waitlist: {len(event.get('waitlist', []))}")
        print(f"- Max team size: {event.get('max_team_size', 0)}")
        print(f"- Registrations open: {event.get('registrations_open', False)}")
else:
    print("No event data found")

print("\nChannel ID:", data.get('channel_id', 'None'))
print("\nUser team assignments:", len(data.get('user_team_assignments', {})))