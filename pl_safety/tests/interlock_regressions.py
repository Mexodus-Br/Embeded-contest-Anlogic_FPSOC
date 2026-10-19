"""Run original RTL assertions in new evidence folders, without hashing logs.

No historical result files are overwritten and no source assertions are changed.
This runner uses Icarus only; protected-IP runs remain separate and serial.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import traceback

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tag', required=True)
    a = p.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+', a.tag)
    out = ROOT / 'pl_safety/evidence' / ('interlock_regressions_' + a.tag)
    out.mkdir(exist_ok=False)
    result = {'passed': False, 'hashes_computed': False, 'cases': []}
    source = list((ROOT / 'pl_motion/rtl').glob('*.v')) + list((ROOT / 'pl_rs485/rtl').glob('*.v'))
    cases = []
    for profile in [dict(H=3,L=2,S=4,Q=7,E=5,OFF=3,P=8,POL=1),
                    dict(H=1,L=1,S=0,Q=0,E=0,OFF=0,P=2,POL=0),
                    dict(H=5,L=3,S=8,Q=20,E=9,OFF=6,P=10,POL=1)]:
        cases.append(('pl_motion', 'tb_axis_motion', profile))
    for scale, pol in [(1,15), (2,10)]:
        for group in range(6):
            cases.append(('pl_motion','tb_four_axis_motion',dict(SCALE=scale,POL=pol,TEST_GROUP=group)))
    cases += [('pl_motion', n, {}) for n in ['tb_contract', 'tb_motion_fifo', 'tb_motion_planner',
              'tb_motion_executor', 'tb_continuous_motion', 'tb_motion_stream_rx', 'tb_motion_service']]
    cases += [('pl_rs485', n, {}) for n in ['tb_divider', 'tb_fifo', 'tb_rs485', 'tb_profile',
              'tb_multirate', 'tb_multirate_profile', 'tb_gp_regs', 'tb_gp_stress', 'tb_gp_e2e',
              'tb_light_parse', 'tb_telemetry']]
    try:
        for index, (folder, top, params) in enumerate(cases):
            dest = out / f'{index:02}_{top}'
            dest.mkdir()
            includes = [ROOT / x for x in ['pl_interface','pl_rs485/generated','pl_rs485/tests']]
            commands = [
                [shutil.which('iverilog'), '-g2005', '-s', top, '-o', str(dest / 'test.vvp'),
                 *sum((['-I', str(x)] for x in includes), []),
                 *[f'-P{top}.{key}={value}' for key,value in params.items()],
                 *map(str, source), str(ROOT / folder / 'tests' / (top + '.v'))],
                [shutil.which('vvp'), str(dest / 'test.vvp'), '+seed=20261014']]
            record = {'top': top, 'parameters': params, 'passed': False, 'commands': []}
            result['cases'].append(record)
            for name, command in zip(['compile', 'simulation'], commands):
                with (dest / (name + '.log')).open('w', encoding='utf-8') as log:
                    proc = subprocess.run(command, cwd=dest, stdout=log, stderr=subprocess.STDOUT, timeout=240)
                record['commands'].append({'argv':command, 'exit_code':proc.returncode})
                assert proc.returncode == 0, (top, name, dest)
            output = (dest / 'simulation.log').read_text(encoding='utf-8')
            assert 'PASS' in output, top
            record['passed'] = True
            print('PASS', index, top, params, flush=True)
        result['passed'] = True
    except Exception:
        result['failure'] = traceback.format_exc()
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
