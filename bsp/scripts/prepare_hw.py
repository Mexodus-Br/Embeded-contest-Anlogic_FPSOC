"""Copy the vendor's PS-only PL design and set the real IP configuration.

Run alps/TD afterwards: this file alone does NOT regenerate initialization.
"""
from pathlib import Path
import argparse
import shutil
import re

p = argparse.ArgumentParser()
p.add_argument('--demo', type=Path, default=Path(r'D:\Works\Embedded_contest\docs\Analogic\01_start\02_start_Linux\04_secondary_developmemt\demo'))
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
dst = root / 'work' / 'soc_prj'
if dst.exists():
    raise SystemExit('Work project exists; inspect it before recreating.')
shutil.copytree(a.demo / 'soc_prj' / 'system', dst / 'system')
shutil.copytree(a.demo / 'soc_prj' / 'uisrc', dst / 'uisrc')
shutil.copy2(a.demo / 'soc_prj' / 'system.al', dst / 'system.al')
changes = 0
for path in (dst / 'system').rglob('*.xml'):
    # Preserve vendor namespace spellings: the HPF parser is prefix-sensitive.
    s = path.read_text(encoding='utf-8')
    s, count = re.subn(r'(referenceId="DDRC_IO_VOL">)[^<]+', r'\g<1>1.35', s)
    if count:
        changes += count
        path.write_text(s, encoding='utf-8')
if changes == 0:
    raise SystemExit('DDR parameter was not found')
print('Copied PS-only project:', dst)
print('DDRC_IO_VOL changed in', changes, 'IP configuration entries; regeneration required')
