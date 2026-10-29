"""Immutable scoped checkpoint for reset/control-path work; no hashes."""
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FILES = ['pl_motion/rtl/motion_planner.v', 'pl_motion/rtl/motion_stream_rx.v',
         'pl_motion/rtl/motion_service.v', 'pl_safety/rtl/safety_regs.v',
         'pl_safety/rtl/safety_interlock_regs.v']

if __name__ == '__main__':
    dest = HERE / 'before'
    dest.mkdir(exist_ok=False)
    for name in FILES:
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    result = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'status': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
              'saved_sources': FILES, 'hashes_computed': False,
              'previous_route16': 'No final place/route/summary at checkpoint; retained without changes.',
              'comparison_route13': {'setup_ns': -2.173, 'hold_ns': .020,
                                     'slice': 37984, 'slice_ff': 37863}}
    (HERE / 'BASELINE.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS scoped baseline', result['head'])
