"""Final source identity by exact staged byte comparisons; no file hashes."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    for key in ['build', 'real', 'tag']:
        p.add_argument('--' + key, required=True)
    p.add_argument('--legacy-build')
    p.add_argument('--legacy-results')
    a = p.parse_args()
    assert all(re.fullmatch('[A-Za-z0-9_-]+', x) for x in [a.build, a.real, a.tag])
    assert bool(a.legacy_build) == bool(a.legacy_results)
    if a.legacy_build:
        assert all(re.fullmatch('[A-Za-z0-9_-]+', x) for x in [a.legacy_build, a.legacy_results])
    build = ROOT / 'pl_safety/build' / a.build
    real = ROOT / 'pl_safety/build' / a.real
    result = {'passed': False, 'hashes_computed': False, 'build': a.build,
              'real': a.real, 'real_sources': [], 'td_authorized_sources': []}
    out = ROOT / 'pl_safety/evidence' / a.tag
    out.mkdir(exist_ok=False)
    try:
        inventory = json.loads((real / 'compiled_sources.json').read_text())
        for entry in inventory['direct_byte_verified_source_copies']:
            source, staged = Path(entry['source']), Path(entry['compiled_copy'])
            assert source.resolve().is_relative_to(ROOT) and staged.resolve().is_relative_to(real)
            assert source.read_bytes() == staged.read_bytes(), source
            result['real_sources'].append(source.relative_to(ROOT).as_posix())
        for folder in ['pl_motion/rtl', 'pl_rs485/rtl', 'pl_safety/rtl', 'pl_safety/generated']:
            for source in (ROOT / folder).glob('*.v*'):
                assert source.read_bytes() == (build / 'gp' / source.name).read_bytes(), source
                result['td_authorized_sources'].append(source.relative_to(ROOT).as_posix())
        for folder in ['pl_rs485/generated', 'pl_interface/generated']:
            for source in (ROOT / folder).glob('*.vh'):
                assert source.read_bytes() == (build / 'gp' / source.name).read_bytes(), source
                result['td_authorized_sources'].append(source.relative_to(ROOT).as_posix())
        baseline = ROOT / 'pl_safety/build/closure_cofactor_route5'
        for name in ['gp/gp.sdc', 'gp/gp.adc', 'gp/ps-generated-properties.tcl',
                     'gp/axi_dma.v', 'gp/axi_protocol_converter_merge.v',
                     'gp/axi_dma_func_pkg.vh', 'gp/axi_dma_param_pkg.vh']:
            assert (build / name).read_bytes() == (baseline / name).read_bytes(), name
        for name in ['axi_dma.v', 'axi_protocol_converter_merge.v',
                     'axi_dma_func_pkg.vh', 'axi_dma_param_pkg.vh']:
            assert (build / 'gp' / name).read_bytes() == (real / 'ip' / name).read_bytes(), name
        assert json.loads((ROOT / 'pl_safety/evidence' / a.real / 'result.json').read_text())['passed']
        if a.legacy_build:
            previous = ROOT / 'pl_safety/build' / a.legacy_build
            regression = json.loads((ROOT / 'pl_safety/evidence' / a.legacy_results / 'result.json').read_text())
            assert regression['passed'] and len(regression['cases']) == 33
            paths = []
            # These are exactly the original regression DUT source folders.
            # Changed SAF2 monitor RTL is covered by the separately rerun suite
            # and real-IP scenarios, not by reusing an old safety result.
            for folder in ['pl_motion/rtl', 'pl_rs485/rtl', 'pl_rs485/generated', 'pl_interface/generated']:
                for source in (ROOT / folder).glob('*.v*'):
                    assert source.read_bytes() == (previous / 'gp' / source.name).read_bytes(), source
                    assert source.read_bytes() == (build / 'gp' / source.name).read_bytes(), source
                    paths.append(source.relative_to(ROOT).as_posix())
            result['unchanged_original_regression_dut'] = {
                'build': a.legacy_build, 'passed_results': a.legacy_results,
                'cases': 33, 'direct_byte_verified_paths': paths}
        result['passed'] = True
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS exact current RTL/header byte identity with real compiled copies and TD project; vendor/constraints unchanged')


if __name__ == '__main__':
    main()
