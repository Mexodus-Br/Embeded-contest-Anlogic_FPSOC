"""Extract source only, excluding the vendor's old objects/modules/generated files."""
import subprocess, sys, zipfile
from pathlib import Path
task = Path(sys.argv[1])
with zipfile.ZipFile(task/'input/vendor-input.zip') as z:
    for name in z.namelist():
        p = Path(name)
        if p.is_absolute() or '..' in p.parts:
            raise ValueError(name)
        if name.startswith('aic8800/') and (p.suffix in ('.c', '.h') or p.name in ('Makefile', 'Kconfig')):
            target = task/'build'/name
        elif name.startswith('aic8800D80/'):
            target = task/'output/overlay/vendor/etc/firmware'/name
        else:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(z.read(name))
# Command-line CONFIG_PLATFORM_* overrides the vendor's RK defaults and paths.
# Keep direct file firmware loading: supplied layout is /vendor/etc/firmware/aic8800D80.
subprocess.run(['patch', '-p1', '-i', str(task/'bsp/wifi/driver-privacy.patch')], cwd=task/'build', check=True)
