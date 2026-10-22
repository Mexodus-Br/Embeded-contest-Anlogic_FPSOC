"""Windows handoff relocation check; uses a disposable runtime copy only."""
import http.cookiejar
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/partner'
KIT = 'ps_partner_v1_1_20261022_005289b'


def check():
    if os.name != 'nt':
        raise RuntimeError('This launcher check requires Windows PowerShell.')
    manifest=json.loads((ROOT/KIT/'ps_partner_v1/PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        relative=Path(item['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert (ROOT/KIT/'ps_partner_v1'/relative).stat().st_size==item['bytes']
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='relocated bundle ', dir=OUT) as directory:
        bundle = Path(directory).resolve()
        assert bundle.is_relative_to(OUT.resolve())
        for relative in ['web/ps', 'scenarios', KIT]:
            shutil.copytree(ROOT / relative, bundle / relative)
        for relative in ['build/partner/native/ps_server.exe', 'tools/launch_ps.ps1',
                         'tools/stop_ps.ps1']:
            target = bundle / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        # The caller deliberately has a different cwd from the runtime copy.
        caller = bundle / 'unrelated caller'
        caller.mkdir()

        def shell(script, *arguments, success=True):
            # Windows background processes can inherit capture pipes and keep
            # communicate() waiting for EOF after PowerShell has already exited.
            # Real files let us wait on the launcher process itself instead.
            out_path = caller / 'launcher-output.txt'
            err_path = caller / 'launcher-error.txt'
            with out_path.open('wb') as output, err_path.open('wb') as error:
                result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy',
                                         'Bypass', '-File', str(bundle / 'tools' / script), *arguments],
                                        cwd=caller, stdout=output, stderr=error, timeout=25)
            stdout, stderr = out_path.read_bytes(), err_path.read_bytes()
            if success:
                assert result.returncode == 0, (stdout, stderr)
            else:
                assert result.returncode != 0
            return stdout.decode('ascii', errors='replace').strip()

        blocker = socket.socket()
        try:
            try:
                blocker.bind(('127.0.0.1', 18083))
                blocker.listen()
            except OSError:
                # An already running application provides the occupied-port case.
                blocker.close()
            try:
                shell('launch_ps.ps1', '-NoBrowser', '-Port', '18083', success=False)
                base = shell('launch_ps.ps1', '-NoBrowser', '-SimulationInjection')
                assert base.startswith('http://127.0.0.1:') and not base.endswith(':18083'), base
                state_file = bundle / '.cache/launcher.json'
                launched = json.loads(state_file.read_text(encoding='utf-8-sig'))
                assert shell('launch_ps.ps1', '-NoBrowser', '-SimulationInjection') == base
                assert json.loads(state_file.read_text(encoding='utf-8-sig')) == launched
                with urllib.request.urlopen(base + '/api/health', timeout=3) as response:
                    assert json.load(response)['simulation'] is True
                for route, name in [('/', 'index.html'), ('/app.js', 'app.js'), ('/style.css', 'style.css')]:
                    with urllib.request.urlopen(base + route, timeout=3) as response:
                        assert response.read() == (bundle / 'web/ps' / name).read_bytes()
                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                csrf = ''

                def api(path, body=None):
                    request = urllib.request.Request(base + '/api/v1' + path,
                        data=json.dumps(body).encode() if body is not None else None,
                        headers={'Content-Type': 'application/json', 'Origin': base, 'X-CSRF-Token': csrf})
                    with opener.open(request, timeout=5) as response:
                        return json.load(response)

                token = (bundle / '.cache/ps-token').read_text().strip()
                csrf = api('/auth', {'token': token})['csrf']
                state = api('/state')
                assert state['phase'] == 'idle' and not state['position']['valid']
                api('/control', {'action': 'acquire'})
                api('/simulation/inject', {'kind': 'reference_position'})
                state = api('/state')
                preview = api('/preview', {'schema_version': 1,
                    'parameter_version': state['parameter_version'],
                    'start_position_id': state['position']['position_id'],
                    'task': {'schema_version': 1, 'id': 'relocation_check',
                             'points': [{'xyz_mm': [5, 0, -140]}],
                             'repeat': {'mode': 'finite', 'count': '1'}}})
                assert preview['executable'] is True
                assert preview['target']['steps'] == ['-1089', '-966', '-1213', '0']
                replay = api('/simulation/telemetry', {})
                assert replay['frames'] == 17
                assert api('/state')['phase'] == 'idle'
                assert (bundle / 'runs/ps').is_dir()
            finally:
                shell('stop_ps.ps1')
            try:
                with urllib.request.urlopen(base + '/api/health', timeout=.5):
                    raise AssertionError('Relocated service still running after stop.')
            except (OSError, urllib.error.URLError):
                pass
        finally:
            blocker.close()
        report = {'passed': True, 'scope': 'windows_host_runtime_relocation',
                  'reference_manifest_inventory_verified': True,
                  'launch_from_unrelated_cwd': True, 'occupied_port_rejected': True,
                  'default_port_fallback': True, 'same_folder_instance_reused': True,
                  'static_assets_byte_equal': True, 'initial_position_unknown': True,
                  'preview_golden_target_verified': True, 'frozen_telemetry_frames': 17,
                  'runtime_data_within_relocated_folder': True, 'stop_service_verified': True,
                  'commands_executed': False, 'hardware_access': False}
    report['temporary_copy_removed'] = not bundle.exists()
    assert report['temporary_copy_removed']
    (OUT / 'package_runtime_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('PACKAGE_RUNTIME_PASS')


if __name__ == '__main__':
    check()
