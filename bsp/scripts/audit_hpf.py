"""Inspect generated HPF and executable initialization, refusing display-only edits."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

p = argparse.ArgumentParser()
p.add_argument('hpf', type=Path)
p.add_argument('--extract', type=Path)
a = p.parse_args()
with zipfile.ZipFile(a.hpf) as z:
    print('\n'.join(z.namelist()))
    for n in z.namelist():
        if n.endswith(('soc_plat.h', 'soc_plat.c', 'ddr_init.c', 'ddr.js')):
            data = z.read(n).decode('utf-8', errors='replace')
            print('\nFILE:', n)
            print('\n'.join(x for x in data.splitlines() if any(t in x for t in ['DDRC_', 'IO_VOLT', 'IO_VOL', 'io_vol', '1.35', 'VREF', 'vref', 'ddr_init', 'fd_ddr'])))
    if a.extract:
        a.extract.mkdir(parents=True, exist_ok=True)
        for n in z.namelist():
            target = (a.extract / n).resolve()
            if not target.is_relative_to(a.extract.resolve()):
                raise SystemExit('Unsafe ZIP member')
        z.extractall(a.extract)
print('HPF SHA256', hashlib.sha256(a.hpf.read_bytes()).hexdigest())
