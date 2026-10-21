"""Stage scope boot/PS unchanged; enable only USB0 in its compiled DTS input."""
import hashlib, re, shutil, subprocess, sys
from pathlib import Path
task, scope, base = map(Path, sys.argv[1:])
wifi = task/'bsp/wifi'
out = task/'output'
assert hashlib.sha256((scope/'system.hpf').read_bytes()).hexdigest() == '609639dec28432912e7bcbddee90328edbeaca1a1ee46193d657e8cffa79103b'
shutil.copy2(scope/'system.hpf', task/'system.hpf')
dts = (scope/'output/debug/motion-board.expanded.dts').read_text()
# Replace the final overriding declaration, leaving all GP/HP0/GPIO resources intact.
matches = list(re.finditer(r'&usb_otg0\s*\{[^}]*\};', dts))
assert matches
m = matches[-1]
assert 'status = "disabled"' in m.group()
dts = dts[:m.start()] + m.group().replace('status = "disabled"', 'status = "okay"') + dts[m.end():]
(out/'debug').mkdir(exist_ok=True)
(out/'boot').mkdir(exist_ok=True)
(out/'debug/wifi-board.expanded.dts').write_text(dts)
subprocess.run([str(out/'kernel/scripts/dtc/dtc'), '-I', 'dts', '-O', 'dtb', '-o', str(out/'boot/system.dtb'), str(out/'debug/wifi-board.expanded.dts')], check=True)
overlay = out/'overlay'
# Preserve scope utilities/configuration, but never copy old kernel modules or boot services.
for name in ('delta-scope', 'delta-model', 'firmware-oracle', 'scope-unit', 'gp-accept', 'bsp-readonly-check'):
    source = scope/'output/rootfs-target/usr/bin'/name
    target = overlay/'usr/bin'/name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
source_config = scope/'output/rootfs-target/etc/delta-scope'
for source in source_config.rglob('*'):
    if source.is_file():
        target = overlay/'etc/delta-scope'/source.relative_to(source_config)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
# The previous module identity list is invalid after kernel/config change.
old_identity = overlay/'etc/delta-scope/files.sha256'
if old_identity.exists():
    old_identity.unlink()
for src, dest in [('usb_inventory.py','usr/sbin/wifi-usb'), ('driver.sh','usr/sbin/wifi-driver'), ('sta.sh','usr/sbin/wifi-sta'), ('configure.py','usr/sbin/wifi-configure'), ('udhcpc.sh','usr/libexec/wifi-udhcpc'), ('S45wifi','etc/init.d/S45wifi'), ('accept.sh','usr/sbin/wifi-accept')]:
    p = overlay/dest
    p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wifi/src, p)
    p.chmod(0o755)
# No credentials, no enable marker, no automatic driver loading in distributable image.
(overlay/'etc/wifi').mkdir(mode=0o700, exist_ok=True)
(overlay/'etc/wifi').chmod(0o700)
(overlay/'etc/wpa_supplicant.conf').write_text('# Use wifi-configure and wifi-sta; no default network.\n')
config = (base/'output/buildroot/.config').read_text()
for key, value in {
    'BR2_ROOTFS_OVERLAY': f'"{overlay}"', 'BR2_DL_DIR': f'"{base}/downloads"',
    'BR2_TOOLCHAIN_EXTERNAL_PATH': f'"{base}/vendor/tools/aarch64-linux"',
    'BR2_TARGET_GENERIC_HOSTNAME':'"delta-wifi"',
    'BR2_TARGET_GENERIC_ISSUE':'"Delta Wi-Fi candidate - not board accepted"',
    'BR2_PACKAGE_WPA_SUPPLICANT':'y', 'BR2_PACKAGE_WPA_SUPPLICANT_NL80211':'y',
    'BR2_PACKAGE_WPA_SUPPLICANT_CLI':'y', 'BR2_PACKAGE_WPA_SUPPLICANT_PASSPHRASE':'y',
    'BR2_PACKAGE_IW':'y', 'BR2_PACKAGE_IPROUTE2':'y',
    'BR2_PACKAGE_WIRELESS_REGDB':'y',
    'BR2_PACKAGE_PYTHON3':'y',
    'BR2_PACKAGE_BUSYBOX_CONFIG_FRAGMENT_FILES':f'"{wifi}/busybox.fragment"',
}.items():
    config = re.sub(r'^(?:'+key+r'=.*|# '+key+r' is not set)\n', '', config, flags=re.M)
    config += f'{key}={value}\n'
(task/'build/buildroot.config').write_text(config)
