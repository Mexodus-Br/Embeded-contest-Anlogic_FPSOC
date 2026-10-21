"""Create an OFFLINE-ONLY rootfs, deliberately without BOOT/bit/HPF/SD image."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import argparse

H=Path(__file__).resolve().parent
T=H.parent
S=H/'frozen/software'
OLD=Path.home()/'embedded-bsp-wifi-http-20261019-r3'
WIFI=Path.home()/'embedded-bsp-wifi-20261018'
BASE=Path.home()/'embedded-bsp'
p=argparse.ArgumentParser();p.add_argument('--tag',default='');a=p.parse_args()
assert not a.tag or a.tag.replace('-','').isalnum()
suffix=('-'+a.tag) if a.tag else ''
target=T/('rootfs-target'+suffix)
assert not target.exists(),'Refuse overwriting rootfs candidate'
assert (T/'build/build.ok').is_file(),'Require successful matched software build'
shutil.copytree(str(OLD/'output/rootfs-target'),str(target),symlinks=True)
release=(WIFI/'output/kernel/include/config/kernel.release').read_text().strip()
assert release=='6.1.111-rt42-bsp-wifi1'
files={
    'bsp/wifi/driver.sh':'usr/sbin/wifi-driver',
    'bsp/wifi/sta.sh':'usr/sbin/wifi-sta',
    'bsp/wifi/http/server.py':'usr/lib/wifi-http/server.py',
    'bsp/wifi/http/auth.py':'usr/sbin/wifi-http-auth',
    'bsp/wifi/http/export.py':'usr/sbin/wifi-http-export',
    'bsp/wifi/http/control.sh':'usr/sbin/wifi-http',
    'bsp/wifi/http/S46wifi-http':'etc/init.d/S46wifi-http'}
direct={}
for name,dest in files.items():direct[dest]=S/name
direct.update({'usr/bin/saf2-diag':T/'build/saf2-diag',
               'usr/bin/rs485-accept':T/'build/rs485-accept',
               'usr/sbin/integration-export':H/'export_snapshot.py'})
for name in ['bsp_gp','bsp_motion','bsp_rs485','bsp_saf2_diag']:
    direct['lib/modules/'+release+'/extra/'+name+'.ko']=T/'build/modules'/(name+'.ko')
direct['lib/modules/'+release+'/kernel/drivers/dma/anlogic/anlogic-dma-engine.ko']=T/'build/modules/anlogic-dma-engine.ko'
for dest,source in direct.items():
    path=target/dest;path.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(str(source),str(path));path.chmod(0o644 if dest.endswith('.ko') else 0o755)
for name in ['aic_load_fw','aic8800_fdrv']:
    source=T/'build/aic8800'/name/(name+'.ko')
    assert source.is_file(),'Rebuild Wi-Fi modules first'
    dest='opt/wifi-candidates/'+name+'.ko';direct[dest]=source
    shutil.copyfile(str(source),str(target/dest))
# Old scope/motion applications have not qualified SAF2 admission/recovery.
# Quarantine these entry points in this NEW candidate, leaving all old images intact.
excluded=[]
for name in ['delta-scope','motion-accept','motion-supply','motion-stream']:
    for folder in ['usr/bin','usr/sbin']:
        path=target/folder/name
        if path.exists():path.unlink();excluded.append(folder+'/'+name)
for name in ['etc/wifi-http/auth.json','etc/wifi-http/autostart',
             'etc/wifi/wpa_supplicant.conf','etc/wifi/autostart','etc/wifi/driver-approved',
             'srv/wifi-http/exports/network-snapshot.txt','srv/wifi-http/exports/integration-snapshot.json']:
    assert not (target/name).exists(),'Personal configuration or fake board evidence: '+name
for directory in ['root/.ssh','home/uisrc/.ssh']:
    assert not (target/directory).exists(),'Personal SSH directory in distribution'
for pattern in ['etc/ssh/ssh_host_*_key','etc/dropbear/dropbear_*_host_key','root/.*history']:
    assert not list(target.glob(pattern)),'Host keys or shell history in distribution'
index=target/'srv/wifi-http/public/index.html'
index.write_text('<!doctype html><meta charset="utf-8"><title>Offline integration candidate</title>'
    '<h1>Read-only diagnostics</h1><p>Kernel: '+release+'</p>'
    '<p>No-motor candidate. Production HOME and mechanical motion are not approved.</p>'
    '<p>No board snapshot collected. Use local integration-export explicitly.</p>'
    '<a href="/files/test.bin">Binary test</a> '
    '<a href="/files/network-snapshot.txt">Network snapshot</a> '
    '<a href="/files/integration-snapshot.json">SAF2 snapshot</a>')
for path in (target/'etc/init.d').iterdir():
    if path.is_file():
        text=path.read_text(errors='replace')
        assert not any(x in text for x in ['saf2-diag','rs485-accept','delta-scope','bsp_motion','bsp_rs485','bsp_saf2_diag']),path
subprocess.check_call(['depmod','-b',str(target),release])
host=WIFI/'output/buildroot/host'
image=T/('build/rootfs-offline'+suffix+'.ext4')
script=T/('build/fakeroot-integration'+suffix+'.sh')
script.write_text('''#!/bin/sh
set -eu
chown -h -R 0:0 '%s'
'%s/bin/makedevs' -d '%s/output/buildroot/build/buildroot-fs/full_devices_table.txt' '%s'
'%s/sbin/mkfs.ext4' -F -d '%s' -r 1 -N 0 -m 5 -L integration-off -O ^64bit -U 524316de-f9a9-4db6-9aac-cc9984110201 '%s' 256M
'''%(target,host,WIFI,target,host,target,image))
subprocess.check_call([str(host/'bin/fakeroot'),'--','sh',str(script)])
subprocess.check_call(['e2fsck','-fn',str(image)])
with tempfile.TemporaryDirectory() as directory:
    def dump(name):
        p=Path(directory)/'file'
        if p.exists():p.unlink()
        subprocess.check_call(['debugfs','-R','dump /'+name+' '+str(p),str(image)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        assert p.is_file(),name
        return p.read_bytes()
    for name,source in direct.items():assert dump(name)==source.read_bytes(),name
    assert dump('srv/wifi-http/exports/test.bin')==bytes(range(256))*1024
    fw=target/'vendor/etc/firmware'
    count=0
    for path in fw.iterdir():
        if path.is_symlink() and os.readlink(str(path)).startswith('aic8800D80/'):
            assert dump('vendor/etc/firmware/'+os.readlink(str(path)))==path.resolve().read_bytes()
            stat=subprocess.check_output(['debugfs','-R','stat /vendor/etc/firmware/'+path.name,str(image)],stderr=subprocess.STDOUT).decode()
            assert 'Type: symlink' in stat and os.readlink(str(path)) in stat
            count+=1
    assert count==11,count
    for name in ['etc/wifi-http/auth.json','etc/wifi-http/autostart','etc/wifi/wpa_supplicant.conf','etc/wifi/autostart','etc/wifi/driver-approved',
                 'srv/wifi-http/exports/network-snapshot.txt','srv/wifi-http/exports/integration-snapshot.json']:
        stat=subprocess.check_output(['debugfs','-R','stat /'+name,str(image)],stderr=subprocess.STDOUT).decode()
        assert 'File not found' in stat,name
    passwd=dump('etc/passwd');assert b'wifihttp:x:498:498:' in passwd
    assert b'wifihttp:!:' in dump('etc/shadow')
result={'status':'PASS_OFFLINE_ROOTFS_ONLY_NOT_BOOTABLE_CHAIN','kernel':release,
        'installed_files_compared_from_ext4':list(direct),'firmware_aliases':count,
        'excluded_unqualified_motion_programs':excluded,'credentials_present':False,
        'autostart_approval_present':False,'fake_board_snapshot_present':False,
        'boot_hpf_bit_fsbl_sd_generated':False,'partition_audit':'NOT_APPLICABLE_NO_SD_IMAGE',
        'e2fsck':'PASS','hashes_computed':False}
(T/('build/rootfs-audit'+suffix+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
