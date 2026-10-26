"""Explicit IPv4 binding must preserve Host, Origin and authentication gates."""
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT/'build/partner/native'/('ps_server.exe' if os.name == 'nt' else 'ps_server')
with tempfile.TemporaryDirectory(dir=ROOT/'build/partner') as directory:
    d = Path(directory)
    token = 'a'*64
    (d/'token').write_text(token)
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    base = [str(EXE), '--backend', 'simulation', '--port', str(port),
            '--data', str(d/'data'), '--token-file', str(d/'token')]
    for invalid in ['0.0.0.0', '255.255.255.255', 'localhost', 'bad']:
        r = subprocess.run(base+['--bind', invalid], cwd=ROOT, capture_output=True, timeout=5)
        assert r.returncode != 0 and b'concrete local IPv4' in r.stderr, (invalid, r.stderr)
    p = subprocess.Popen(base+['--bind', '127.0.0.2'], cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        def request(method, path, host, origin=None, body=None):
            c = http.client.HTTPConnection('127.0.0.2', port, timeout=2)
            headers = {'Host': host, 'Content-Type': 'application/json'}
            if origin is not None:
                headers['Origin'] = origin
            c.request(method, path, json.dumps(body) if body is not None else None, headers)
            r = c.getresponse()
            result = r.status, json.loads(r.read())
            c.close()
            return result
        for _ in range(100):
            try:
                assert request('GET', '/api/health', f'127.0.0.2:{port}')[0] == 200
                break
            except OSError:
                assert p.poll() is None
                time.sleep(.03)
        else:
            raise AssertionError('server did not start')
        host = f'127.0.0.2:{port}'
        assert request('GET', '/api/v1/state', host)[0] == 401
        assert request('GET', '/api/health', 'attacker.invalid')[0] == 401
        assert request('GET', '/api/health', f'localhost:{port}')[0] == 401
        assert request('POST', '/api/v1/auth', host, 'http://attacker.invalid', {'token': token})[0] == 401
        assert request('POST', '/api/v1/auth', host, 'http://'+host, {'token': token})[0] == 200
        assert request('POST', '/api/v1/auth', host, 'http://'+host, {'token': 'bad'})[0] == 401
        print('PASS explicit IPv4 bind, wildcard refusal, Host/Origin/auth gates')
    finally:
        p.terminate()
        p.communicate(timeout=5)
