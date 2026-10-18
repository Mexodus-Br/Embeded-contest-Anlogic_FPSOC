"""Prepare an isolated source-only ZIP from the user-owned vendor WIFI.zip."""
import argparse
from pathlib import Path
import zipfile

p = argparse.ArgumentParser()
p.add_argument('vendor_zip', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
with zipfile.ZipFile(str(a.vendor_zip)) as src, zipfile.ZipFile(str(a.output), 'w', zipfile.ZIP_DEFLATED) as dst:
    for name in src.namelist():
        parts = Path(name).parts
        if name.startswith('/') or '..' in parts or '\\' in name:
            continue
        if (name.startswith('aic8800/') and (name.endswith(('.c', '.h', '/Makefile', '/Kconfig')) or Path(name).name in ('LICENSE', 'COPYING'))) or (name.startswith('aic8800D80/') and not name.endswith('/')):
            dst.writestr(name, src.read(name))
print('Prepared source/firmware input; all old ko/o/cmd products excluded')
