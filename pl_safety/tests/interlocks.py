"""SAF2 self-check runner. Immutable tags, no file hashes, serial simulators."""
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
    p.add_argument('--bench', choices=['monitor', 'regs', 'legacy', 'motion', 'rs485', 'owner'], default='monitor')
    p.add_argument('--mode', type=int, default=0)
    p.add_argument('--offset', type=int, default=0)
    a = p.parse_args()
    assert re.fullmatch('[A-Za-z0-9_-]+', a.tag)
    out = ROOT / 'pl_safety/evidence' / ('interlock_' + a.tag)
    out.mkdir(exist_ok=False)
    result = {'passed': False, 'bench': a.bench, 'hashes_computed': False, 'commands': []}
    try:
        sources = ['pl_rs485/rtl/rs485_light_parse.v', 'pl_safety/rtl/safety_interlock.v',
                   'pl_safety/tests/tb_interlock.v']
        top = 'tb_interlock'
        if a.bench == 'owner':
            sources = ['pl_safety/rtl/safety_controller.v', 'pl_safety/tests/tb_interlock_owner_projection.v']
            top = 'tb_interlock_owner_projection'
        if a.bench == 'regs':
            sources = ['pl_safety/rtl/safety_regs.v', 'pl_safety/rtl/safety_interlock_regs.v',
                       'pl_safety/tests/tb_interlock_regs.v']
            top = 'tb_interlock_regs'
        if a.bench == 'rs485':
            from interlock_rs485_fixture import render
            (out / 'tb_interlock_rs485.v').write_text(render(), encoding='utf-8')
            sources = ['pl_rs485/rtl/rs485_gp_regs.v', 'pl_rs485/rtl/record_fifo.v',
                       str(out / 'tb_interlock_rs485.v')]
            top = 'tb_interlock_rs485'
        if a.bench in ('legacy', 'motion'):
            sources = ['pl_safety/rtl/' + n for n in ['safety_controller.v', 'safety_inputs.v',
                       'safety_regs.v', 'safety_motion_service.v', 'safety_interlock.v', 'safety_interlock_regs.v']]
            sources += ['pl_motion/rtl/' + n for n in ['motion_service.v', 'continuous_motion.v',
                        'motion_executor.v', 'motion_planner.v', 'motion_fifo.v', 'motion_stream_rx.v']]
            sources += ['pl_rs485/rtl/rs485_light_parse.v']
            if a.bench == 'legacy':
                sources += ['pl_safety/tests/tb_safety.v']
                top = 'tb_safety'
            else:
                from interlock_motion_fixture import render
                (out / 'tb_interlock_motion.v').write_text(render(), encoding='utf-8')
                sources += [str(out / 'tb_interlock_motion.v')]
                top = 'tb_interlock_motion'
        commands = [
            [shutil.which('iverilog'), '-g2005', '-I', str(ROOT / 'pl_safety/generated'),
             '-I', str(ROOT / 'pl_rs485/generated'), '-I', str(ROOT / 'pl_rs485/tests'), '-I', str(ROOT / 'pl_interface'),
             '-s', top, *([f'-P{top}.MODE={a.mode}', f'-P{top}.OFFSET={a.offset}']
                         if a.bench in ('legacy', 'motion') else []), '-o', str(out / 'test.vvp'),
             *[str(ROOT / x) for x in sources]],
            [shutil.which('vvp'), str(out / 'test.vvp')]]
        for name, command in zip(['compile', 'simulation'], commands):
            with (out / (name + '.log')).open('w', encoding='utf-8') as log:
                proc = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=60)
            result['commands'].append({'argv': command, 'exit_code': proc.returncode})
            assert proc.returncode == 0, name
        output = (out / 'simulation.log').read_text(encoding='utf-8')
        marker = {'monitor': 'PASS interlock_monitor', 'regs': 'PASS interlock_regs',
                  'legacy': 'PASS safety', 'motion': 'PASS interlock_motion', 'rs485': 'PASS interlock_rs485_guard',
                  'owner': 'PASS interlock_owner_projection'}[a.bench]
        assert marker in output
        result['passed'] = True
        print(output.strip())
    except Exception:
        result['failure'] = traceback.format_exc()
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
