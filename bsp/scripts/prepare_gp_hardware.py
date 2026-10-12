"""Clone the accepted PS baseline into an isolated GP work project.

This prepares real PS IP generation; never patches only report fields.
"""
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'work/soc_prj'
destination = ROOT / 'work/gp_soc_prj'
if destination.exists():
    raise SystemExit('GP work project already exists; inspect rather than overwrite')
destination.mkdir(parents=True)
for name in ['system', 'uisrc']:
    shutil.copytree(source / name, destination / name)
project = (source / 'system.al').read_text(encoding='utf-8')
project = re.sub(r'(<Project[^>]* Path=")[^"]*', lambda m: m[1] + destination.as_posix(), project, count=1)
(destination / 'system.al').write_text(project, encoding='utf-8')
print('Prepared isolated PS generation input:', destination)
print('Original DDR configuration preserved; run ps_gp_regen.tcl next')
