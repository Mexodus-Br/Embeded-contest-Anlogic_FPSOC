"""Existing parser baseline only; no hashes, production values or Questa use."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import traceback

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.tag):
        raise ValueError('Invalid evidence tag')
    evidence = ROOT / 'pl_safety/evidence' / ('interlock_inputs_' + args.tag)
    evidence.mkdir(exist_ok=False)
    result = {'passed': False, 'scope': 'existing parser eligibility inputs only',
              'new_interlock_verified': False, 'production_parameters_selected': False,
              'hashes_computed': False, 'commands': []}

    def run(name, command):
        completed = subprocess.run(command, cwd=ROOT, capture_output=True,
                                   text=True, errors='replace', timeout=60)
        (evidence / (name + '.log')).write_text(
            completed.stdout + completed.stderr, encoding='utf-8')
        result['commands'].append({'argv': list(map(str, command)),
                                   'exit_code': completed.returncode})
        if completed.returncode:
            raise RuntimeError(name + ' failed; retained log: ' + str(evidence))
        return completed.stdout

    try:
        iv, vvp = shutil.which('iverilog'), shutil.which('vvp')
        if not iv or not vvp:
            raise RuntimeError('Icarus and vvp are required')
        executable = evidence / 'parser.vvp'
        run('compile', [iv, '-g2005', '-I', str(ROOT / 'pl_rs485/generated'),
                        '-s', 'tb_interlock_feedback_inputs', '-o', str(executable),
                        str(ROOT / 'pl_rs485/rtl/rs485_light_parse.v'),
                        str(ROOT / 'pl_safety/tests/tb_interlock_feedback_inputs.v')])
        output = run('simulation', [vvp, str(executable)])
        match = re.search(r'PASS interlock_feedback_input_baseline checks=(\d+)', output)
        if not match:
            raise RuntimeError('Missing self-check completion marker')
        result.update(passed=True, checks=int(match[1]))
        print(output.strip())
    except Exception:
        result['failure'] = traceback.format_exc()
        raise
    finally:
        (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n',
                                               encoding='utf-8')


if __name__ == '__main__':
    main()
