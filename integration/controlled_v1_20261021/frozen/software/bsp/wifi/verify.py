"""Offline gates for this candidate. Hashes are restricted to explicit final files."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

task = Path(sys.argv[1]).resolve()
out = task/'output'
release = out/'release'
scope = Path.home()/'embedded-bsp-scope'

def run(*args):
    return subprocess.check_output(list(map(str, args)), stderr=subprocess.PIPE, universal_newlines=True).strip()

def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()

manifest = json.loads((release/'manifest.json').read_text())
allowed = {'sdcard.img','BOOT.bin','system.hpf','system.bit','fsbl.elf','u-boot.bin','system.dtb','uImage.lz4','rootfs.ext4','boot.cmd','boot.scr','boot.bif'}
assert set(manifest['files']) == allowed
for name in sorted(allowed):
    assert sha(release/name) == manifest['files'][name]['sha256'], name
assert (release/'BOOT.bin').read_bytes() == (scope/'output/release/BOOT.bin').read_bytes(), 'scope boot chain changed'
assert (release/'system.hpf').read_bytes() == (scope/'system.hpf').read_bytes()
dtb = release/'system.dtb'
usb = '/soc/usb@F8180000'
assert run('fdtget',dtb,usb,'status') == 'okay'
assert run('fdtget',dtb,usb,'dr_mode') == 'host'
assert run('fdtget','-t','x',dtb,usb,'interrupts') == '0 38 4'
# Canonical DT comparison proves all other node properties are retained.
with tempfile.TemporaryDirectory(prefix='wifi-verify-') as directory:
    expected = Path(directory)/'expected.dtb'
    expected.write_bytes((scope/'output/boot/system.dtb').read_bytes())
    subprocess.check_call(['fdtput','-t','s',str(expected),usb,'status','okay'])
    assert run('dtc','-I','dtb','-O','dts',expected) == run('dtc','-I','dtb','-O','dts',dtb), 'unexpected non-USB DT change'
assert run('fdtget','-t','x',dtb,'/memory','reg') == '0 0 0 40000000'
kr = (out/'kernel/include/config/kernel.release').read_text().strip()
assert kr == '6.1.111-rt42-bsp-wifi1'
kconfig = (out/'debug/kernel.config').read_text()
for key in ('CONFIG_CFG80211','CONFIG_WLAN','CONFIG_RFKILL','CONFIG_USB_DWC2_HOST','CONFIG_MODVERSIONS'):
    assert key+'=y' in kconfig, key
target = out/'buildroot/target'
ko_names = ['extra/bsp_gp.ko','extra/bsp_motion.ko','kernel/drivers/dma/anlogic/anlogic-dma-engine.ko']
critical = ['lib/modules/'+kr+'/'+name for name in ko_names]
critical += ['opt/wifi-candidates/aic_load_fw.ko','opt/wifi-candidates/aic8800_fdrv.ko']
critical += ['usr/sbin/wifi-sta','usr/sbin/wifi-driver','usr/sbin/wifi-configure','usr/sbin/wifi-accept','usr/sbin/wifi-usb','usr/libexec/wifi-udhcpc','etc/init.d/S45wifi']
critical += ['usr/sbin/wpa_supplicant','usr/sbin/wpa_cli','usr/sbin/iw','bin/busybox','sbin/ip','usr/bin/python3.10']
modules = {}
symbols = {}
for source in (out/'kernel/Module.symvers',task/'build/modules/provider/Module.symvers',task/'build/aic8800/Module.symvers'):
    for line in source.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 2:
            symbols[fields[1]] = int(fields[0],16)
for name in critical[:5]:
    vermagic = run('modinfo','-F','vermagic',target/name)
    assert vermagic.startswith(kr+' ') and 'modversions aarch64' in vermagic
    imports = run('modprobe','--dump-modversions',target/name).splitlines()
    for line in imports:
        crc, symbol = line.split()
        assert symbols.get(symbol) == int(crc,16), 'symbol CRC mismatch: '+name+':'+symbol
    modules[name] = {'vermagic':vermagic, 'sha256':sha(target/name),
                     'depends':run('modinfo','-F','depends',target/name),'import_crc_count':len(imports)}
assert 'aic' not in (target/'lib/modules'/kr/'modules.dep').read_text().lower()
for name in ('wpa_supplicant.conf','autostart','driver-approved'):
    assert not (target/'etc/wifi'/name).exists(), 'local-only configuration leaked into image'
assert not (target/'etc/delta-scope/files.sha256').exists(), 'stale scope identity gate'
assert 'network={' not in (target/'etc/wpa_supplicant.conf').read_text()
assert (target/'usr/bin/lsusb').is_symlink()
assert 'BR2_ROOTFS_DEVICE_CREATION_DYNAMIC_DEVTMPFS=y' in (out/'debug/buildroot.config').read_text()
for init in (target/'etc/init.d').glob('S*'):
    text = init.read_text()
    assert not any(command in text for command in ('bsp_motion','motion-accept','delta-scope serve')), str(init)
busybox = next((out/'buildroot/build').glob('busybox-*/.config')).read_text()
assert 'CONFIG_UDHCPC=y' in busybox and 'CONFIG_LSUSB=y' in busybox
for name in ('regulatory.db','regulatory.db.p7s'):
    assert (target/'lib/firmware'/name).is_file(), name
with tempfile.TemporaryDirectory(prefix='wifi-rootfs-') as directory:
    for index, name in enumerate(critical):
        dest = Path(directory)/str(index)
        run('debugfs','-R','dump /'+name+' '+str(dest),release/'rootfs.ext4')
        assert dest.is_file(), 'not installed: '+name
        assert dest.read_bytes() == (target/name).read_bytes(), 'rootfs mismatch: '+name
    for name in ('wpa_supplicant.conf','autostart','driver-approved'):
        text = subprocess.check_output(['debugfs','-R','stat /etc/wifi/'+name,str(release/'rootfs.ext4')],stderr=subprocess.STDOUT,universal_newlines=True)
        assert 'File not found' in text, 'image has local-only configuration'
# Compare exact boot/root partition bytes without hashing intermediate files.
image = release/'sdcard.img'
assert image.stat().st_size == 536870912
with image.open('rb') as stream:
    mbr = stream.read(512)
    assert mbr[510:] == b'\x55\xaa'
    signature = struct.unpack_from('<I',mbr,440)[0]
    assert manifest['root_partuuid'] == '%08x-02' % signature
    for index, part in enumerate(('boot.vfat','rootfs.ext4')):
        sector, length = struct.unpack_from('<II',mbr,446+16*index+8)
        assert sector == (2048,133120)[index]
        assert length == (131072,524288)[index]
        stream.seek(sector*512)
        with (release/part).open('rb') as source:
            for block in iter(lambda: source.read(1024*1024), b''):
                assert stream.read(len(block)) == block, part
subprocess.check_call(['fsck.vfat','-n',str(release/'boot.vfat')])
subprocess.check_call(['e2fsck','-fn',str(release/'rootfs.ext4')])
result = {'status':'OFFLINE_VERIFIED_NOT_DEPLOYED_NOT_BOARD_ACCEPTED', 'kernelrelease':kr,
          'root_partuuid':manifest['root_partuuid'], 'image_sha256':manifest['files']['sdcard.img']['sha256'],
          'scope_boot_unchanged':True, 'dt_change':'USB0 status only', 'modules':modules,
          'credentials_in_image':False, 'autostart_enabled':False,
          'hardware_acceptance':{key:'NOT_EXECUTED_BOARD_AND_SD_UNAVAILABLE' for key in 'ABCDEF'}}
(out/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
