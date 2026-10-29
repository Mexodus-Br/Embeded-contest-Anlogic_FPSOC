"""Fetch this task's VM file image and verify ONLY the 11 final artifacts."""
from pathlib import Path
import hashlib
import json
import os
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'bsp/.host-python'))
import paramiko

remote = '/home/uisrc/embedded-full-function-20261028-r3'
release = HERE/'artifacts/release-r1'
audit = HERE/'artifacts/release-audits'
assert not release.exists() or not any(release.iterdir()), 'Preserve any prior download'
assert not audit.exists() or not any(audit.iterdir()), 'Preserve any prior audit'
release.mkdir(parents=True, exist_ok=True)
audit.mkdir(exist_ok=True)
names = ['sdcard.img', 'BOOT.bin', 'system.hpf', 'system.bit', 'fsbl.elf',
         'u-boot.bin', 'uImage.lz4', 'system.dtb', 'rootfs.ext4', 'boot.cmd', 'boot.scr']
client = paramiko.SSHClient()
client.load_system_host_keys()
# Obtained independently via local VMware Tools from the running project VM;
# vmrun getGuestIPAddress confirmed 192.168.43.136. Never learn it over SSH.
public_key = (HERE/'artifacts/vm-host-ed25519.pub').read_text().strip()
assert public_key.startswith('ssh-ed25519 ')
entry = paramiko.hostkeys.HostKeyEntry.from_line('192.168.43.136 '+public_key)
assert entry and entry.key
client.get_host_keys().add('192.168.43.136', entry.key.get_name(), entry.key)
client.set_missing_host_key_policy(paramiko.RejectPolicy())
try:
    client.connect('192.168.43.136', username='uisrc',
                   password=os.environ['WIFI_VM_PASSWORD'],
                   allow_agent=False, look_for_keys=False, timeout=15)
    with client.open_sftp() as sftp:
        for name in ['manifest.json', 'SHA256SUMS']:
            sftp.get(remote+'/output/release/'+name, str(release/name))
        manifest = json.loads((release/'manifest.json').read_text())
        assert list(manifest['files']) == names
        assert manifest['hardware_result']['setup_ns'] > 0
        assert manifest['hardware_result']['hold_ns'] >= 0
        assert not manifest['sd_written'] and not manifest['emmc_qspi_touched']
        for name in names:
            target = release/name
            sftp.get(remote+'/output/release/'+name, str(target))
            assert target.stat().st_size == manifest['files'][name]['bytes'], name
            digest = hashlib.sha256()
            with target.open('rb') as stream:
                for block in iter(lambda: stream.read(1 << 20), b''):
                    digest.update(block)
            assert digest.hexdigest() == manifest['files'][name]['sha256'], name
            print('VERIFIED', name, target.stat().st_size, flush=True)
        for name in ['build-vm.log', 'hardware-result.json', 'source-identity.json',
                     'boot_work/identity-audit.json', 'build/module-audit.json',
                     'build/abi-audit.json', 'build/system-enabled.dts',
                     'build/module-build.log', 'build/userspace-build.log']:
            target = audit/name
            target.parent.mkdir(parents=True, exist_ok=True)
            sftp.get(remote+'/'+name, str(target))
finally:
    client.close()
(audit/'local-verification.json').write_text(json.dumps({
    'final_files_verified': names, 'sha256_equal_to_vm_manifest': True,
    'logs_or_intermediate_files_hashed': False, 'card_or_flash_access': False,
}, indent=2)+'\n')
print('PASS all 11 final artifacts match VM SHA256; no card/flash access')
