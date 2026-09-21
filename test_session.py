import requests, json, sys

r = requests.get('http://localhost:8765/conversations', timeout=30)
sessions = r.json()['sessions']
print(f'Found {len(sessions)} sessions')

if sessions:
    sid = sessions[0]['session_id']
    print(f'Testing session: {sid}')
    r2 = requests.get(f'http://localhost:8765/conversations/{sid}', timeout=30)
    print(f'Status: {r2.status_code}')
    data = r2.json()
    msgs = data.get('messages', [])
    print(f'Messages: {len(msgs)}')
    for msg in msgs[:3]:
        role = msg.get('role', '?')
        content = msg.get('content', '')[:80]
        print(f'  [{role}] {content}')
