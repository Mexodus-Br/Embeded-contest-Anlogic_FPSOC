"""Read-only baseline/ABI/space checks; deliberately computes no file hashes.

Does not execute historic sealing/build helpers, consume a Questa license,
modify generated output or select any interlock production parameter.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
SAFETY = ROOT / 'pl_safety'
BASELINE = '249f3c3'
TIMING_SOURCE = 'eccab43'
EVIDENCE = SAFETY / 'evidence/closure_cofactor_route5'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def leaves_preserved(old, new, path=''):
    if isinstance(old, dict):
        assert isinstance(new, dict), path
        return sum(leaves_preserved(v, new[k], path + '/' + k)
                   for k, v in old.items())
    if isinstance(old, list):
        assert isinstance(new, list) and len(old) == len(new), path
        return sum(leaves_preserved(v, new[i], path + '/' + str(i))
                   for i, v in enumerate(old))
    assert type(old) is type(new) and old == new, (path, old, new)
    return 1


def occupied(profile):
    words = set(profile['registers'].values())
    assert len(words) == len(profile['registers'])
    words.update(range(profile['snapshot_base'],
                       profile['snapshot_base'] + 4 * profile['snapshot_words'], 4))
    assert all(x % 4 == 0 and 0 <= x < 4096 for x in words)
    return words


def ranges(words):
    result = []
    for x in sorted(words):
        if result and result[-1][1] + 4 == x:
            result[-1][1] = x
        else:
            result.append([x, x])
    return [[f'0x{a:03x}', f'0x{b + 3:03x}'] for a, b in result]


def numeric_definitions(schema):
    """Check generated numeric ABI even when an old schema banner is stale."""
    result = {}
    for script, profile, prefix in (
            ('generate_gp.py', schema['rs485_gp_profiles']['gp_rs485_v1'], 'RG_'),
            ('generate_telem.py', schema['rs485_telemetry'], 'RT_')):
        path = ROOT / 'pl_rs485/tools' / script
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected = {prefix + k: v for k, v in module.constants(profile).items()}
        stem = 'gp_defs' if prefix == 'RG_' else 'telem_defs'
        for suffix in ('vh', 'h'):
            text = (ROOT / 'pl_rs485/generated' / (stem + '.' + suffix)).read_text()
            pattern = (r"`define (\w+) 32'h([0-9a-f]+)" if suffix == 'vh' else
                       r'#define (\w+) UINT32_C\(0x([0-9a-f]+)\)')
            actual = {k: int(v, 16) for k, v in re.findall(pattern, text)}
            assert actual == expected, (stem, suffix, 'numeric ABI mismatch')
            result[stem + '.' + suffix] = len(expected)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        assert not args.output.exists(), 'Refuse to overwrite prior evidence'
        assert args.output.resolve().is_relative_to(SAFETY.resolve())
    schema = json.loads((ROOT / 'pl_interface/schema.json').read_text(encoding='utf-8'))
    old = json.loads(git('show', BASELINE + ':pl_interface/schema.json'))
    count = leaves_preserved(old, schema)
    safety = schema['safety_profiles']['gp_safety_home_v1']
    rs485 = schema['rs485_gp_profiles']['gp_rs485_v1']
    assert safety['base'] == 0x80a00000 and safety['caps'] == 0x3f
    assert rs485['base'] == 0x80700000
    assert safety['time_hz'] == 1000000 and safety['clock_hz'] == 100000000
    saf_words, rs_words = occupied(safety), occupied(rs485)
    assert not (saf_words & set(range(0x100, 0x200, 4)))
    assert not (saf_words & set(range(0x300, 0x1000, 4)))
    direct = ['pl_safety/rtl/safety_controller.v',
              'pl_safety/rtl/safety_motion_service.v',
              'pl_safety/rtl/safety_regs.v',
              'pl_motion/rtl/motion_service.v',
              'pl_motion/rtl/motion_stream_rx.v',
              'pl_motion/rtl/motion_executor.v',
              'pl_motion/rtl/continuous_motion.v',
              'pl_rs485/rtl/rs485_gp_bridge.v',
              'pl_rs485/rtl/rs485_gp_regs.v',
              'pl_rs485/rtl/rs485_multirate.v',
              'pl_rs485/rtl/rs485_transaction.v',
              'pl_rs485/rtl/rs485_light_parse.v']
    source_matches = {}
    for name in direct:
        actual = (ROOT / name).read_bytes().replace(b'\r\n', b'\n')
        reference = git('show', TIMING_SOURCE + ':' + name).replace(b'\r\n', b'\n')
        source_matches[name] = actual == reference
        assert source_matches[name], ('Source differs from timing baseline', name)
        # The text evidence folder intentionally keeps only constraints under
        # gp/. Source bytes remain in the complete routed project cache.
        staged = SAFETY / 'build/closure_cofactor_route5/gp' / Path(name).name
        staged_bytes = staged.read_bytes().replace(b'\r\n', b'\n')
        if name.startswith('pl_rs485/'):
            # Frozen actual project expands these generated includes inline.
            # Require exactly that textual expansion; no HDL logic rewriting.
            for header in ('parameters.vh', 'rate_parameters.vh',
                           'rs485_defs.vh', 'rate_defs.vh', 'gp_defs.vh'):
                actual = actual.replace(('`include "' + header + '"').encode(),
                                        (ROOT / 'pl_rs485/generated' / header)
                                        .read_bytes().replace(b'\r\n', b'\n'))
        assert staged_bytes == actual, staged
    comparison = json.loads((SAFETY / 'optimization/timing_20261017/comparison_closure_cofactor_route5.json').read_text())
    stages = {}
    for stage in ('gate', 'place', 'route'):
        report = (EVIDENCE / (stage + '.timing')).read_text()
        stages[stage] = {
            key: float(re.search(pattern, report)[1]) for key, pattern in
            [('setup_ns', r'SWNS:\s*([-\d.]+)ns'),
             ('hold_ns', r'HWNS:\s*([-\d.]+)ns')]}
        for key, value in stages[stage].items():
            assert value == comparison['timing_after'][stage][key]
    assert stages['route'] == {'setup_ns': 1.133, 'hold_ns': 0.020}
    area = (EVIDENCE / 'route.area').read_text()
    patterns = {'lut6': '#lut6', 'slice': '#slice', 'slice_reg': '  #slice reg',
                'pad_reg': '  #pad reg', 'eram': '#eram', 'dsp': '#dsp',
                'io': '#IO', 'gclk': '#gclk', 'sclk': '#sclk', 'lclk': '#lclk',
                'pll': '#pll', 'ioclk': '#ioclk', 'mlclk': '#mlclk'}
    for key, pattern in patterns.items():
        used = int(re.search('^' + re.escape(pattern) + r'\s+(\d+)', area, re.M)[1])
        assert used == comparison['resources_after'][key]['used'], key
    run = (EVIDENCE / 'run.log').read_text(errors='replace')
    tcl = (EVIDENCE / 'run.tcl').read_text()
    assert 'set_param flow thread 16' in tcl and 'get_num_thread' in tcl
    assert 'SAFETY_TD_THREADS 16' in run and 'Number of Thread = 16' in run
    assert comparison['target_pass'] and not comparison['signoff_pass']
    result = {
        'preparation_passed': True, 'head': git('rev-parse', 'HEAD').decode().strip(),
        'baseline': BASELINE, 'timing_source': TIMING_SOURCE,
        'old_schema_leaves_preserved': count,
        'generated_rs485_numeric_definitions': numeric_definitions(schema),
        'direct_source_byte_comparison_lf_normalized': source_matches,
        'safety_occupied_byte_ranges': ranges(saf_words),
        'rs485_occupied_byte_ranges': ranges(rs_words),
        'reference_full_top_resources': comparison['resources_after'],
        'reference_full_top_timing': stages, 'reference_threads_readback': 16,
        'tools_present': {n: shutil.which(n) for n in
                          ('python', 'iverilog', 'vvp', 'vlog', 'vsim', 'td_commands_prompt')},
        'tracked_worktree_status': git('status', '--porcelain', '--untracked-files=no').decode().splitlines(),
        'production_parameters_selected': False, 'new_rtl_verified': False,
        'new_full_top_timing_passed': False, 'release_signoff': False,
        'file_hashes_computed': False,
    }
    if args.output:
        with args.output.open('x', encoding='utf-8') as output:
            output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        if '--output' in sys.argv:
            target = Path(sys.argv[sys.argv.index('--output') + 1])
            if (not target.exists() and
                    target.resolve().is_relative_to(SAFETY.resolve())):
                with target.open('x', encoding='utf-8') as output:
                    output.write(json.dumps({'preparation_passed': False,
                                             'failure': traceback.format_exc(),
                                             'file_hashes_computed': False}, indent=2) + '\n')
        raise
