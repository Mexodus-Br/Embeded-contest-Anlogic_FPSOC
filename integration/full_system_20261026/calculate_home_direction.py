"""Calculate +Z HOME direction using the unchanged original firmware sources.

Host calculation only: the Arduino shim has no hardware IO. Does not rebuild
PL/images, alter production parameters, hash evidence, or authorize movement.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIRMWARE = ROOT.parent/'docs/Arduino_firmware'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tag', default='original-plus-z')
args = parser.parse_args()
assert args.tag.replace('-', '').isalnum()
out = HERE/'artifacts'/('home-direction-'+args.tag)
out.mkdir(parents=True, exist_ok=False)
compiler = shutil.which('g++')
assert compiler, 'C++ compiler required'
command = [compiler, '-std=c++17', '-O0', '-Wall', '-Wextra', '-Wpedantic',
           '-fno-fast-math', '-ffp-contract=off',
           '-I'+str(ROOT/'golden_model/tests'), '-I'+str(FIRMWARE),
           str(ROOT/'golden_model/tests/oracle.cpp'),
           str(FIRMWARE/'robotGeometry.cpp'), str(FIRMWARE/'RampsStepper.cpp'),
           '-o', str(out/'original-firmware-oracle.exe')]
build = subprocess.run(command, capture_output=True, text=True)
(out/'compile.log').write_text(build.stdout+build.stderr, encoding='utf-8')
build.check_returncode()

config = (FIRMWARE/'config.h').read_text(encoding='utf-8-sig')
inverse = []
for axis in 'XYZ':
    values = re.findall(r'^#define\s+INVERSE_'+axis+r'_STEPPER\s+(true|false)\b', config, re.M)
    assert len(values) == 1
    inverse.append(values[0] == 'true')
stepper = (FIRMWARE/'RampsStepper.cpp').read_text(encoding='utf-8-sig')
assert 'digitalWrite(dirPin, !inverse)' in stepper
assert 'digitalWrite(dirPin, inverse)' in stepper

examples = [(0, 0, -141), (0, 0, -140), (0, 0, -139)]
lanes = [(0, 0), (30, 20), (-30, -20), (80, 0), (0, 80)]
points = examples+[(x, y, z) for x, y in lanes for z in range(-300, -99)]
result = subprocess.run([str(out/'original-firmware-oracle.exe')],
    input=''.join('xyz %s %s %s\n' % p for p in points),
    capture_output=True, text=True, check=True)
rows = [json.loads(line) for line in result.stdout.splitlines()]
assert len(rows) == len(points)
example_rows = [dict(xyz_mm=p, **r) for p, r in zip(examples, rows[:3])]
assert [r['absolute_steps'] for r in rows[:3]] == [[-1059]*3, [-1090]*3, [-1123]*3]
delta = [b-a for a, b in zip(rows[1]['absolute_steps'], rows[2]['absolute_steps'])]
assert all(d < 0 for d in delta)
home_levels = [int(inv if d > 0 else not inv) for inv, d in zip(inverse, delta)]
pull_levels = [1-level for level in home_levels]
mask = lambda levels: sum(level << i for i, level in enumerate(levels))
assert mask(home_levels) == 0 and mask(pull_levels) == 7

scans = []
for lane, xy in enumerate(lanes):
    values = rows[3+lane*201:3+(lane+1)*201]
    valid = invalid = 0
    exceptions = []
    for i, (a, b) in enumerate(zip(values, values[1:])):
        if any(v is None for v in a['angles_rad']+b['angles_rad']):
            invalid += 1
            continue
        valid += 1
        changes = [bv-av for av, bv in zip(a['angles_rad'], b['angles_rad'])]
        if any(change >= 0 for change in changes):
            exceptions.append(dict(z_mm=-300+i, angle_changes=changes))
    assert not exceptions, (xy, exceptions)
    scans.append(dict(xy_mm=xy, z_range_mm=[-300, -100], increment_mm=1,
                      finite_pairs=valid, invalid_pairs_excluded=invalid,
                      nondecreasing_angle_pairs=exceptions))

production = json.loads((ROOT/'pl_safety/config/production.json').read_text())
report = dict(numeric_profile='host_float32_double64', avr_execution_verified=False,
    sources=[str(FIRMWARE/n) for n in ['robotGeometry.cpp', 'RampsStepper.cpp', 'config.h']],
    unchanged_original_sources_compiled=True, hardware_io=False, hashes_computed=False,
    axis_order=['X_high/A0', 'Y_low/A1', 'Z_rot/A2'], inverse=inverse,
    user_home_cartesian_direction='+Z vertically upward', examples=example_rows,
    upward_delta_steps=delta, home_dir_levels=home_levels, HOME_DIRECTION=mask(home_levels),
    pull_dir_levels=pull_levels, PULL_DIRECTION=mask(pull_levels),
    production_direction_already_matches=production['HOME_DIRECTION'] == mask(home_levels),
    production_approved_unchanged=production['approved'], scans=scans,
    scope='Original firmware model and existing logical axis mapping; sampled numerical domain only',
    still_unset=['reference position / encoder reference', 'pull distance', 'phase speeds and travel/time bounds'],
    image_rebuilt=False, motion_authorized=False, compiler_command=command)
(out/'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['examples', 'upward_delta_steps', 'home_dir_levels',
    'HOME_DIRECTION', 'pull_dir_levels', 'PULL_DIRECTION', 'production_direction_already_matches', 'scans']},
    ensure_ascii=False, indent=2))
print('Result:', out/'result.json')
