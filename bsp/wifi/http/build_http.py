"""Incremental rootfs-only build, preserving the prior candidate and boot inputs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

task=Path(sys.argv[1]).resolve()
previous=Path.home()/'embedded-bsp-wifi-20261018'
source=task/'bsp/wifi/http'
out=task/'output'
out.mkdir(exist_ok=True)
target=out/'rootfs-target'
if not target.exists(): shutil.copytree(str(previous/'output/buildroot/target'),str(target),symlinks=True)
for directory in ('boot','fsbl','debug'):
    (out/directory).mkdir(exist_ok=True)
for name in ('u-boot.bin','uImage.lz4','system.dtb'):
    shutil.copy2(str(previous/'output/boot'/name),str(out/'boot'/name))
shutil.copy2(str(previous/'output/fsbl/fsbl.elf'),str(out/'fsbl/fsbl.elf'))
shutil.copy2(str(previous/'system.hpf'),str(task/'system.hpf'))
for name in ('kernel.config','buildroot.config'):
    shutil.copy2(str(previous/'output/debug'/name),str(out/'debug'/name))
for link,original in [(out/'kernel',previous/'output/kernel'),(task/'vendor/tools',Path.home()/'embedded-bsp/vendor/tools')]:
    link.parent.mkdir(parents=True,exist_ok=True)
    if not link.exists(): link.symlink_to(original,target_is_directory=True)
files={'server.py':'usr/lib/wifi-http/server.py','auth.py':'usr/sbin/wifi-http-auth',
       'export.py':'usr/sbin/wifi-http-export','control.sh':'usr/sbin/wifi-http','S46wifi-http':'etc/init.d/S46wifi-http'}
for name,dest in files.items():
    path=target/dest; path.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(str(source/name),str(path)); path.chmod(0o755)
shutil.copy2(str(task/'bsp/wifi/driver.sh'),str(target/'usr/sbin/wifi-driver'))
(target/'usr/sbin/wifi-driver').chmod(0o755)
shutil.copy2(str(task/'bsp/wifi/sta.sh'),str(target/'usr/sbin/wifi-sta'))
(target/'usr/sbin/wifi-sta').chmod(0o755)
for name in ('fw_patch_table_8800d80_u02.bin','fw_patch_8800d80_u02.bin','fw_adid_8800d80_u02.bin','fmacfw_8800d80_u02.bin','fmacfw_8800d80_h_u02.bin','fmacfw_8800d80_u02_ipc.bin','calibmode_8800d80.bin','lmacfw_rf_8800d80_u02.bin','fw_ble_scan_ad_filter.bin','aic_userconfig_8800d80.txt','aic_powerlimit_8800d80.txt'):
    alias=target/'vendor/etc/firmware'/name
    if not alias.exists(): alias.symlink_to('aic8800D80/'+name)
for directory in ('srv/wifi-http/public','srv/wifi-http/exports','etc/wifi-http'):
    path=target/directory; path.mkdir(parents=True,exist_ok=True); path.chmod(0o755 if directory.startswith('srv') else 0o700)
for name in ('auth.json','autostart'):
    assert not (target/'etc/wifi-http'/name).exists(),'Credentials/approval must never enter an image'
(target/'srv/wifi-http/exports/test.bin').write_bytes(bytes(range(256))*1024)
kernel=(out/'kernel/include/config/kernel.release').read_text().strip()
(target/'srv/wifi-http/public/index.html').write_text('<!doctype html><meta charset="utf-8"><title>Wi-Fi diagnostics</title><h1>Wi-Fi read-only diagnostics</h1><p>Kernel: '+kernel+'</p><p>Snapshot not collected. Run local wifi-http-export after Wi-Fi connects.</p><a href="/files/test.bin">Binary test (262144 bytes)</a>')
assert not (target/'srv/wifi-http/exports/network-snapshot.txt').exists(),'No build-host snapshot in board image'
# Fixed non-login identity; independent of root and all motion services.
passwd=target/'etc/passwd'; group=target/'etc/group'; shadow=target/'etc/shadow'
assert not any(line.split(':')[2]=='498' and not line.startswith('wifihttp:') for line in passwd.read_text().splitlines()),'UID collision'
assert not any(line.split(':')[2]=='498' and not line.startswith('wifihttp:') for line in group.read_text().splitlines()),'GID collision'
for path,record in [(passwd,'wifihttp:x:498:498:WiFi read-only HTTP:/nonexistent:/bin/false\n'),(group,'wifihttp:x:498:\n'),(shadow,'wifihttp:!:10933:0:99999:7:::\n')]:
    if not any(line.startswith('wifihttp:') for line in path.read_text().splitlines()):
        with path.open('a') as stream: stream.write(record)
shadow.chmod(0o600)
host=previous/'output/buildroot/host'
image=out/'buildroot/images/rootfs.ext4'; image.parent.mkdir(parents=True,exist_ok=True)
fakeroot=task/'build/fakeroot-http.sh'
fakeroot.write_text('''#!/bin/sh
set -eu
chown -h -R 0:0 '%s'
'%s/bin/makedevs' -d '%s/output/buildroot/build/buildroot-fs/full_devices_table.txt' '%s'
find '%s' -print0 | xargs -0 -r touch -hd @1791676800
'%s/sbin/mkfs.ext4' -F -d '%s' -r 1 -N 0 -m 5 -L bsp-root -O ^64bit -U 6d398841-220c-4d38-aefa-20ab09f33832 '%s' 256M
''' % (target,host,previous,target,target,host,target,image))
subprocess.check_call([str(host/'bin/fakeroot'),'--','sh',str(fakeroot)])
subprocess.check_call(['e2fsck','-fn',str(image)])
subprocess.check_call(['python3',str(task/'bsp/wifi/package.py'),str(task)])
m=out/'release/manifest.json'; data=json.loads(m.read_text())
data.update(profile='wifi-http-readonly-20261019',http_port=8080,http_authentication='LOCAL_ONLY_NOT_PROVISIONED',http_autostart=False,
            hardware_acceptance='PENDING_THIS_IMAGE_LAN_AND_COLD_BOOT',
            wifi_driver_selection='D80_CANDIDATE_REQUIRES_LOCAL_DEVICE_QUALIFICATION')
m.write_text(json.dumps(data,indent=2)+'\n')
print('HTTP_ROOTFS_BUILT_NOT_BOARD_ACCEPTED')
