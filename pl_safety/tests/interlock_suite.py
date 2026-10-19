"""Serial unit, legacy, 14 x 24 stop-phase sweep and exact collisions; no hashes."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tag', required=True)
    a = p.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+', a.tag)
    out = ROOT / 'pl_safety/evidence' / ('interlock_suite_' + a.tag)
    out.mkdir(exist_ok=False)
    result = {'passed': False, 'cases': [], 'hashes_computed': False}
    start = time.monotonic()
    try:
        cases = [('monitor', 0, 0), ('regs', 0, 0), ('rs485', 0, 0), ('owner', 0, 0)]
        cases += [('legacy', m, 0) for m in range(32)]
        cases += [('motion', m, o) for m in range(14) for o in range(24)]
        cases += [('motion', m, 0) for m in range(14, 17)]
        for bench, mode, offset in cases:
            tag = f'{a.tag}_{bench}_{mode}_{offset}'
            argv = [sys.executable, str(ROOT / 'pl_safety/tests/interlocks.py'),
                    '--bench', bench, '--mode', str(mode), '--offset', str(offset), '--tag', tag]
            process = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, timeout=90)
            result['cases'].append({'bench': bench, 'mode': mode, 'offset': offset,
                                    'exit_code': process.returncode, 'evidence': 'interlock_' + tag})
            assert process.returncode == 0, process.stdout
            if len(result['cases']) % 24 == 0:
                print('PASS cases', len(result['cases']), flush=True)
        result['passed'] = True
    except Exception:
        result['failure'] = traceback.format_exc()
        raise
    finally:
        result['elapsed_seconds'] = time.monotonic() - start
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print('RESULT', result['passed'], len(result['cases']), flush=True)


if __name__ == '__main__':
    main()
