"""Freeze actual routed inputs and clean BSP sources; never package the worktree.

No hashes of logs, databases, evidence directories, or temporary files.
"""
import json
from pathlib import Path
import shutil
import subprocess
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUILD = ROOT / 'pl_safety/build/rtl_path38'
CANDIDATE = ROOT / 'pl_safety/optimization/reset_path_20261020/rtl37_candidate_r5'
BASE = '07745a8238608f548314fe90a505fcd2c4c575a4'


def main():
    destination = HERE / 'frozen'
    if destination.exists():
        raise SystemExit('Refuse existing frozen directory')
    summary = json.loads((BUILD / 'route_summary.json').read_text())
    assert summary['flow_completed'] and not summary['signoff_pass']
    assert summary['stages']['route'] == {'setup_ns': .032, 'hold_ns': .02}
    assert summary['threads'] == 16
    entries = []

    def copy(source, target, origin):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert source.read_bytes() == target.read_bytes()
        entries.append({'path': target.relative_to(HERE).as_posix(), 'source': origin,
                        'source_bytes': target.stat().st_size})

    # The historical manifest is only a path inventory. Never hash its contents.
    reference = ROOT / 'pl_safety/build/closure_cofactor_route5/inputs.json'
    names = set(json.loads(reference.read_text())['candidate_inputs_sha256'])
    names.update(p.relative_to(BUILD).as_posix() for p in (BUILD / 'gp').rglob('*') if p.is_file())
    names.update(['system.al', 'system/hdl/system_wrapper.v', 'run.tcl',
                  'place_budget.sdc', 'route_budget.sdc'])
    allowed = {'.v', '.vh', '.xml', '.tcl', '.sdc', '.adc', '.al'}
    for name in sorted(names):
        p = BUILD / name
        if p.suffix.lower() in allowed:
            assert p.is_file(), p
            copy(p, destination / 'pl' / name, p.relative_to(ROOT).as_posix())
    for p in CANDIDATE.glob('*.v'):
        assert p.read_bytes() == (destination / 'pl/gp' / p.name).read_bytes(), p

    # BSP and generators come from an explicit commit, never the dirty tree.
    roots = ['bsp/gp/', 'bsp/motion/', 'bsp/telemetry/', 'bsp/wifi/',
             'pl_interface/', 'pl_rs485/generated/', 'pl_rs485/software/', 'pl_rs485/tools/',
             'pl_safety/generated/', 'pl_safety/software/', 'pl_safety/config/']
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
    suffixes = {'.c', '.h', '.py', '.sh', '.dtsi', '.fragment', '.patch', '.json', '.vh'}
    for name in names:
        p = Path(name)
        explicit={'pl_rs485/rate_design.json','pl_rs485/schema.json','pl_safety/generate.py','pl_safety/generate_interlock.py','bsp/configs/kernel.dts'}
        if (name in explicit or any(name.startswith(r) for r in roots)) and (p.suffix in suffixes or ('/generated/' in name and p.suffix=='.md') or p.name == 'Makefile' or p.name.startswith(('S45', 'S46'))):
            # Evidence/old release manifests are references, not software inputs.
            if '/evidence/' in name or p.name in {'DELIVERY.json', 'hardware-review.json', 'integration.review.json'}:
                continue
            data = subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)
            target = destination / 'software' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            entries.append({'path': target.relative_to(HERE).as_posix(), 'source': BASE + ':' + name, 'source_bytes': len(data)})
    # Check direct generated identity against the actual routed copies.
    for name in ['interlock_defs.vh', 'safety_defs.vh', 'safety_parameters.vh']:
        assert (destination / 'software/pl_safety/generated' / name).read_bytes() == (destination / 'pl/gp' / name).read_bytes()
    (HERE / 'sources.json').write_text(json.dumps({'baseline_commit': BASE,
        'actual_pl': 'rtl_path38', 'candidate': 'rtl37_candidate_r5',
        'product_promoted': False, 'production_profile': False,
        'hashes_computed': False, 'manifest_semantics':'Origins and byte counts before explicit isolated adaptations; final modified identities are in delivery.json', 'files': entries}, indent=2) + '\n')
    print('Frozen', len(entries), 'explicit source/build inputs; no databases or logs copied')


if __name__ == '__main__':
    main()
