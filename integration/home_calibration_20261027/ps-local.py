#!/usr/bin/python3
"""Root-local client of the ONE running hardware Service. Never opens a device."""
import http.cookiejar
import json
import secrets
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

os.umask(0o077)
run_dir = Path(os.environ.get('PS_HMI_RUN_DIR', '/run/ps-hmi'))
config_dir = Path(os.environ.get('PS_HMI_CONFIG_DIR', '/etc/ps-hmi'))
base = (run_dir/'url').read_text().strip()
token = (config_dir/'token').read_text().strip()
cookies = http.cookiejar.LWPCookieJar(str(run_dir/'local-cookies'))
try:
    cookies.load(ignore_discard=True)
except FileNotFoundError:
    pass
client = urllib.request.build_opener(urllib.request.ProxyHandler({}),
    urllib.request.HTTPCookieProcessor(cookies))
def call(path, method='GET', body=None, csrf=None):
    headers = {'Origin': base, 'Content-Type': 'application/json'}
    if csrf:
        headers['X-CSRF-Token'] = csrf
    data = None if body is None else json.dumps(body).encode()
    with client.open(urllib.request.Request(base+'/api/v1'+path, data, headers, method=method), timeout=5) as r:
        return json.load(r)
try:
    auth = call('/auth')
except urllib.error.HTTPError:
    auth = call('/auth', 'POST', {'token': token})
    cookies.save(ignore_discard=True)
arg = sys.argv[1] if len(sys.argv) > 1 else 'state'
if arg in ('state', 'telemetry'):
    result = call('/'+arg)
elif arg == 'stop':
    result = call('/stop', 'POST', {}, auth['csrf'])
elif arg == 'release':
    result = call('/control', 'POST', {'action': 'release'}, auth['csrf'])
elif arg == 'action' and len(sys.argv) == 3:
    call('/control', 'POST', {'action': 'acquire'}, auth['csrf'])
    body = {'action': sys.argv[2], 'boot_id': auth['boot_id']}
    if body['action'] == 'home':
        state = call('/state')
        body.update(owner_id=state['backend']['owner_id'], cancel_epoch=state['backend']['cancel_epoch'],
                    request_id=secrets.token_hex(16), deadline_monotonic_us=str(int(state['monotonic_us'])+2000000))
    result = call('/hardware/action', 'POST', body, auth['csrf'])
elif arg == 'request':
    request = json.load(sys.stdin)
    # All state-changing commands still pass the same Service admission gates.
    call('/control', 'POST', {'action': 'acquire'}, auth['csrf'])
    result = call(request['path'], request['method'], request.get('body'), auth['csrf'])
else:
    raise SystemExit('Usage: ps-local state|telemetry|stop|release|action NAME|request < request.json')
print(json.dumps(result, ensure_ascii=False, indent=2))
