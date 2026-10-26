"""The installed local adapter reuses one authenticated service and session."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT/'build/partner/native'/('ps_server.exe' if os.name == 'nt' else 'ps_server')
CLIENT = ROOT.parent/'integration/full_system_20261026/ps-local.py'
with tempfile.TemporaryDirectory(dir=ROOT/'build/partner') as directory:
    d = Path(directory)
    (d/'token').write_text('b'*64)
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    (d/'url').write_text(url)
    env = os.environ.copy()
    env.update(PS_HMI_RUN_DIR=str(d), PS_HMI_CONFIG_DIR=str(d))
    p = subprocess.Popen([str(EXE), '--backend', 'simulation', '--port', str(port),
                          '--token-file', str(d/'token'), '--data', str(d/'data')],
                         cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(url+'/api/health', timeout=.2):
                    break
            except OSError:
                assert p.poll() is None
                time.sleep(.03)
        else:
            raise AssertionError('server did not start')
        def call(*args, body=None):
            r = subprocess.run([sys.executable, str(CLIENT), *args], env=env, cwd=ROOT,
                               input=None if body is None else json.dumps(body),
                               capture_output=True, text=True, timeout=8)
            assert r.returncode == 0, r.stderr
            return json.loads(r.stdout)
        state = call('state')
        assert not state['position']['valid']
        boot = state['boot_id']
        assert call('request', body={'method': 'POST', 'path': '/mode', 'body': {'mode': 'manual'}})['mode'] == 'manual'
        assert call('request', body={'method': 'POST', 'path': '/mode', 'body': {'mode': 'task'}})['mode'] == 'task'
        assert call('state')['boot_id'] == boot
        assert call('stop')['status'] == 'received'
        for _ in range(30):
            if call('state')['phase'] == 'idle':
                break
            time.sleep(.03)
        else:
            raise AssertionError('STOP not completed')
        assert not call('release')['you_control']
        assert not call('state')['control_owned']
        assert (d/'local-cookies').is_file()
        print('PASS local adapter: same boot, persistent authenticated control, STOP and release')
    finally:
        p.terminate()
        p.communicate(timeout=5)
