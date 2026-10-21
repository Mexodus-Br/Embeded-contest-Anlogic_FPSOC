"""Authorized VM source staging; password is prompted and retained only in memory."""
from pathlib import Path
import sys,getpass,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'bsp/.host-python'))
import paramiko
p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','update','modules','status','package','download']);a=p.parse_args()
c=paramiko.SSHClient();c.load_system_host_keys();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.43.135',username='uisrc',password=getpass.getpass('VM password: '),allow_agent=False,look_for_keys=False,timeout=15)
remote='/home/uisrc/embedded-bsp-motor3125';W=R/'bsp/work/motor3125_soc_prj'
def run(cmd):
    _,o,e=c.exec_command(cmd)
    print(o.read().decode(errors='replace'));print(e.read().decode(errors='replace'))
    assert o.channel.recv_exit_status()==0
try:
 if a.action in ['stage','update']:
    if a.action=='stage':run('test ! -e '+remote+' && mkdir '+remote)
    s=c.open_sftp();s.put(str(W/'vm-input.tar'),remote+'/vm-input.tar');s.close()
    run('cd '+remote+' && tar xf vm-input.tar && mkdir -p logs')
    if a.action=='stage':run('cd '+remote+' && ln -s ../embedded-bsp-scope/vendor vendor && ln -s ../embedded-bsp-scope/sdk sdk')
    from datetime import datetime
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    run('cd '+remote+' && if test -f logs/arm-launch.log; then cp logs/arm-launch.log logs/arm-launch.'+stamp+'.log; cp logs/arm-build.log logs/arm-build.'+stamp+'.log; cp logs/unit-host.log logs/unit-host.'+stamp+'.log 2>/dev/null || true; fi; nohup bash -c "TASK='+remote+' bash bsp/scope/build_arm.sh; echo BUILD_EXIT=\$?" > logs/arm-launch.log 2>&1 < /dev/null &')
 elif a.action=='status':
    run('cd '+remote+' && tail -12 logs/arm-launch.log; test ! -f logs/modules-preflight.log || tail -6 logs/modules-preflight.log; test ! -f logs/package-launch.log || tail -12 logs/package-launch.log')
 elif a.action=='modules':
    run('cd '+remote+' && test ! -f logs/modules-preflight.log && nohup bash -c "TASK='+remote+' bash bsp/scripts/build_motion_software.sh; echo MODULES_EXIT=\$?" > logs/modules-preflight.log 2>&1 < /dev/null &')
 elif a.action=='package':
    s=c.open_sftp()
    for local,name in [(W/'system.hpf','system.hpf'),(R/'bsp/motor_test/integration.review.json','bsp/scope/integration.review.json'),(R/'bsp/motor_test/package.sh','bsp/motor_test/package.sh'),(R/'bsp/motor_test/README.md','bsp/motor_test/README.md')]:s.put(str(local),remote+'/'+name)
    import subprocess
    with s.file(remote+'/bsp/scripts/make_sd_image.py','wb') as f:
        f.write(subprocess.check_output(['git','show','0a4ca51:bsp/scripts/make_sd_image.py'],cwd=R))
    s.close()
    run('cd '+remote+' && bash -n bsp/motor_test/package.sh && test ! -f logs/package-launch.log')
    run('cd '+remote+' && nohup bash -c "TASK='+remote+' bash bsp/motor_test/package.sh; echo PACKAGE_EXIT=\$?" > logs/package-launch.log 2>&1 < /dev/null &')
 elif a.action=='download':
    run('cd '+remote+' && grep -q MOTOR3125_PACKAGE_COMPLETE logs/package-launch.log && grep -q PACKAGE_EXIT=0 logs/package-launch.log')
    dest=R/'bsp/artifacts/motor3125';dest.mkdir(exist_ok=True)
    s=c.open_sftp()
    for name in ['sdcard.img','manifest.json','SHA256SUMS','BOOT.bin','system.dtb','fsbl.elf']:
        s.get(remote+'/output/release/'+name,str(dest/name))
    for name in ['arm-build.log','unit-host.log','package-launch.log','modules-build.log','fsbl-build.log','boot-stage.log','rootfs-stage.log','image.log','image-verify.log']:
        s.get(remote+'/logs/'+name,str(dest/name))
    for item in s.listdir(remote+'/logs'):
        if item.endswith('.log') and not (dest/item).exists():s.get(remote+'/logs/'+item,str(dest/item))
    s.get(remote+'/output/debug/motion-image-verification.json',str(dest/'image-verification.json'))
    s.close();print(dest)
finally:c.close()
