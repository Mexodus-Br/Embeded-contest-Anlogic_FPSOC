"""Snapshot only committed source and reviewed task edits; no dirty product RTL."""
from pathlib import Path
import argparse
import io
import json
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE/'artifacts'
OUT.mkdir(exist_ok=True)
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--tag', default='final')
args = p.parse_args()
assert args.tag.replace('-', '').isalnum()
archive = OUT/('source-'+args.tag+'.tar.gz')
assert not archive.exists(), 'Preserve previous attempt; use a new task directory'
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
paths = ['ps_app/src', 'ps_app/third_party', 'ps_app/scenarios', 'ps_app/web',
         'ps_app/tools', 'ps_app/ps_partner_v1_1_20261022_005289b',
         'bsp/safety_execution', 'bsp/motion/motion_uapi.h', 'bsp/motion/generated',
         'integration/controlled_v1_20261021/safety']
names = subprocess.check_output(['git', 'ls-files', *paths], cwd=ROOT).decode().splitlines()
subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', *paths], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
with tarfile.open(archive, 'w:gz') as tar:
    for name in names:
        data = subprocess.check_output(['git', 'show', revision+':'+name], cwd=ROOT)
        info = tarfile.TarInfo('src/'+name)
        info.size = len(data)
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(data))
    identity = json.dumps({'base_commit': revision, 'task': 'full_system_20261026',
                          'source_override': [],
                          'product_dirty_rtl_included': False}, indent=2).encode()
    info = tarfile.TarInfo('source-identity.json'); info.size = len(identity)
    tar.addfile(info, io.BytesIO(identity))
    for name in ['build_vm.py', 'ps-local.py', 'S47ps-hmi']:
        tar.add(HERE/name, arcname=name)
print(archive)
