"""Inventory/permissions/startup audit of the actual final EXT4, never mounted."""
from pathlib import Path
import json
import re
import subprocess
import tempfile

H=Path(__file__).resolve().parent
T=H.parent
image=T/'build/rootfs-offline-complete.ext4'
release='6.1.111-rt42-bsp-wifi1'


def query(command):
    return subprocess.check_output(['debugfs','-R',command,str(image)],stderr=subprocess.STDOUT).decode()


with tempfile.TemporaryDirectory() as directory:
    def dump(name):
        p=Path(directory)/'dump'
        if p.exists():p.unlink()
        query('dump /'+name+' '+str(p))
        assert p.is_file(),name
        return p.read_bytes()
    modules=set(re.findall(r'\s(\S+\.ko)\s*$',query('ls -l /lib/modules/'+release+'/extra'),re.M))
    assert modules=={'bsp_gp.ko','bsp_motion.ko','bsp_rs485.ko','bsp_saf2_diag.ko'},modules
    excluded=['usr/bin/delta-scope','usr/bin/motion-accept','usr/bin/dma-accept',
              'lib/modules/'+release+'/extra/bsp_dma_loop.ko',
              'etc/wifi/wpa_supplicant.conf','etc/wifi/autostart','etc/wifi/driver-approved',
              'etc/wifi-http/auth.json','etc/wifi-http/autostart',
              'srv/wifi-http/exports/network-snapshot.txt','srv/wifi-http/exports/integration-snapshot.json']
    for name in excluded:assert 'File not found' in query('stat /'+name),name
    startup=re.findall(r'\s((?:S\d\S+|rcS|rcK|automount\.sh))\s*$',query('ls -l /etc/init.d'),re.M)
    forbidden=[b'saf2-diag',b'rs485-accept',b'delta-scope',b'bsp_motion',b'bsp_rs485',b'bsp_saf2_diag']
    for name in ['etc/inittab']+['etc/init.d/'+x for x in startup]:
        content=dump(name)
        assert not any(token in content for token in forbidden),name
    modes={'srv/wifi-http/exports':'0755','srv/wifi-http/public':'0755','etc/wifi-http':'0700'}
    for name,mode in modes.items():
        text=query('stat /'+name)
        assert re.search(r'User:\s+0\s+Group:\s+0',text),name
        assert re.search(r'Mode:\s+'+mode,text),name
    firmware=T/'output/overlay/vendor/etc/firmware/aic8800D80'
    fw=[]
    for source in firmware.iterdir():
        if source.is_file():
            assert dump('vendor/etc/firmware/aic8800D80/'+source.name)==source.read_bytes(),source.name
            fw.append(source.name)
    result={'status':'PASS_ACTUAL_EXT4_INVENTORY','out_of_tree_extra_modules':sorted(modules),
            'excluded_legacy_entries_and_credentials':excluded,'startup_files_checked':startup+['inittab'],
            'no_automatic_control_entry':True,'http_directories_root_owned_and_modes':modes,
            'firmware_bytes_match_fresh_vendor_source_extraction':sorted(fw),'hashes_computed':False}
    (T/'build/final-rootfs-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS actual EXT4 legacy-entry exclusion, startup, permissions and fresh-source firmware inventory')
