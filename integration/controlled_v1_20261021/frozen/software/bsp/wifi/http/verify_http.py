"""Offline final-image checks. Never hash diagnostics, logs or temporary dumps."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

task=Path(sys.argv[1]); out=task/'output'; release=out/'release'
previous=Path.home()/'embedded-bsp-wifi-20261018'
manifest=json.loads((release/'manifest.json').read_text())
for name in ('BOOT.bin','system.hpf','system.bit','fsbl.elf','u-boot.bin','system.dtb','uImage.lz4'):
    assert (release/name).read_bytes()==(previous/'output/release'/name).read_bytes(),name
files={'server.py':'usr/lib/wifi-http/server.py','auth.py':'usr/sbin/wifi-http-auth','export.py':'usr/sbin/wifi-http-export','control.sh':'usr/sbin/wifi-http','S46wifi-http':'etc/init.d/S46wifi-http'}
with tempfile.TemporaryDirectory() as directory:
    def dump(name):
        dest=Path(directory)/'file'
        if dest.exists(): dest.unlink()
        subprocess.check_call(['debugfs','-R','dump /'+name+' '+str(dest),str(release/'rootfs.ext4')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        assert dest.is_file(),name
        return dest.read_bytes()
    for name,dest in files.items(): assert dump(dest)==(task/'bsp/wifi/http'/name).read_bytes(),dest
    assert dump('usr/sbin/wifi-driver')==(task/'bsp/wifi/driver.sh').read_bytes()
    assert dump('usr/sbin/wifi-sta')==(task/'bsp/wifi/sta.sh').read_bytes()
    for firmware in (previous/'output/buildroot/target/vendor/etc/firmware/aic8800D80').iterdir():
        if not firmware.is_file(): continue
        name=firmware.name
        assert dump('vendor/etc/firmware/aic8800D80/'+name)==firmware.read_bytes(),name
        value=subprocess.check_output(['debugfs','-R','stat /vendor/etc/firmware/'+name,str(release/'rootfs.ext4')],stderr=subprocess.STDOUT,universal_newlines=True)
        assert 'Type: symlink' in value and 'aic8800D80/'+name in value,name
    assert dump('srv/wifi-http/exports/test.bin')==bytes(range(256))*1024
    assert b'Wi-Fi read-only diagnostics' in dump('srv/wifi-http/public/index.html')
    assert b'wifihttp:x:498:498:' in dump('etc/passwd')
    assert b'wifihttp:!:' in dump('etc/shadow')
    for name in ('auth.json','autostart'):
        value=subprocess.check_output(['debugfs','-R','stat /etc/wifi-http/'+name,str(release/'rootfs.ext4')],stderr=subprocess.STDOUT,universal_newlines=True)
        assert 'File not found' in value,name
    value=subprocess.check_output(['debugfs','-R','stat /srv/wifi-http/exports/network-snapshot.txt',str(release/'rootfs.ext4')],stderr=subprocess.STDOUT,universal_newlines=True)
    assert 'File not found' in value,'No VM snapshot may be passed off as board diagnostics'
    for path in ('usr/sbin/wifi-configure','usr/libexec/wifi-udhcpc',
                 'opt/wifi-candidates/aic_load_fw.ko','opt/wifi-candidates/aic8800_fdrv.ko',
                 'lib/modules/6.1.111-rt42-bsp-wifi1/extra/bsp_gp.ko','lib/modules/6.1.111-rt42-bsp-wifi1/extra/bsp_motion.ko',
                 'lib/modules/6.1.111-rt42-bsp-wifi1/kernel/drivers/dma/anlogic/anlogic-dma-engine.ko'):
        assert dump(path)==(previous/'output/buildroot/target'/path).read_bytes(),path
with (release/'sdcard.img').open('rb') as stream:
    mbr=stream.read(512); assert mbr[510:]==b'\x55\xaa'
    assert manifest['root_partuuid']=='%08x-02'%struct.unpack_from('<I',mbr,440)[0]
    for index,name in enumerate(('boot.vfat','rootfs.ext4')):
        start,count=struct.unpack_from('<II',mbr,454+index*16)
        assert (start,count)==((2048,131072),(133120,524288))[index]
        stream.seek(start*512)
        with (release/name).open('rb') as source:
            for block in iter(lambda:source.read(1024*1024),b''): assert stream.read(len(block))==block
subprocess.check_call(['fsck.vfat','-n',str(release/'boot.vfat')])
subprocess.check_call(['e2fsck','-fn',str(release/'rootfs.ext4')])
result=dict(status='OFFLINE_VERIFIED_NOT_LAN_ACCEPTED',profile=manifest['profile'],root_partuuid=manifest['root_partuuid'],image_sha256=manifest['files']['sdcard.img']['sha256'],kernel_modules_boot_unchanged=True,http_rootfs_files_verified=True,credentials_in_image=False,build_host_diagnostic_snapshot_in_image=False)
(out/'http-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
