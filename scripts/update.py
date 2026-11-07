#!/usr/bin/env python3
"""Met à jour l'état signé de LION CONNECT (exécuté par la surveillance GitHub Actions).
Contrôles : version.json (fichiers statiques) + point d'accès PHP (réponse JSON attendue).
Deux échecs consécutifs = incident. L'état est signé en Ed25519 avec une clé dédiée (secret STATUS_SIGNING_KEY)."""
import base64, json, os, subprocess, sys, time, urllib.request, urllib.error

NOW = int(time.time())
UA = {'User-Agent': 'lion-connect-status-monitor'}

def check_static():
    try:
        with urllib.request.urlopen(urllib.request.Request('https://lion-connect.com/version.json', headers=UA), timeout=20) as r:
            return r.status == 200 and 'version' in json.loads(r.read().decode())
    except Exception:
        return False

def check_api():
    req = urllib.request.Request('https://lion-connect.com/api/share/limits', data=b'{}', method='POST',
                                 headers={**UA, 'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=20)
        return False
    except urllib.error.HTTPError as e:   # 401 JSON attendu sans authentification
        try: return e.code == 401 and json.loads(e.read().decode()).get('code') == 'auth_required'
        except Exception: return False
    except Exception:
        return False

def load(p, d):
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except Exception: return d

state = load('state.json', {'fails': 0, 'since': None, 'lastIncident': None})
msg = load('message.json', {'fr': '', 'en': ''})
prev = load('status.json', {})
prev_payload = json.loads(base64.b64decode(prev['payload'])) if prev.get('payload') else {}

ok = check_static() and check_api()
if ok:
    if state.get('since'): state['lastIncident'] = {'since': state['since'], 'end': NOW}
    state.update(fails=0, since=None)
else:
    state['fails'] = int(state.get('fails', 0)) + 1
    if state['fails'] >= 2 and not state.get('since'): state['since'] = NOW

incident = bool(state.get('since'))
payload = {
    'v': 1, 'incident': incident, 'since': state.get('since'), 'updatedAt': NOW,
    'until': NOW + 3600 if incident else None, 'lastIncident': state.get('lastIncident'),
    'message_fr': str(msg.get('fr', ''))[:500], 'message_en': str(msg.get('en', ''))[:500],
}
# Écriture seulement si l'état change, pendant un incident (renouvellement de « until »), ou une fois par jour.
same = {k: prev_payload.get(k) for k in ('incident', 'since', 'lastIncident', 'message_fr', 'message_en')} == \
       {k: payload[k] for k in ('incident', 'since', 'lastIncident', 'message_fr', 'message_en')}
stale = NOW - int(prev_payload.get('updatedAt') or 0) > 86000
with open('state.json', 'w', encoding='utf-8') as f: json.dump(state, f, indent=2)
if same and not incident and not stale:
    print('état inchangé'); sys.exit(0)

raw = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()
key = os.environ.get('STATUS_KEY_FILE', '')
with open('payload.bin', 'wb') as f: f.write(raw)
sig = subprocess.run(['openssl', 'pkeyutl', '-sign', '-inkey', key, '-rawin', '-in', 'payload.bin'], check=True, capture_output=True).stdout
os.remove('payload.bin')
with open('status.json', 'w', encoding='utf-8') as f:
    json.dump({'v': 1, 'payload': base64.b64encode(raw).decode(), 'sig': base64.b64encode(sig).decode()}, f, indent=2)
print('incident' if incident else 'normal', payload['updatedAt'])
