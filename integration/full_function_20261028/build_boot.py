"""New same-project HPF/FSBL/BOOT inputs; no block-device or flash access."""
from pathlib import Path
import json,os,re,shutil,subprocess,zipfile
T=Path(__file__).resolve().parent
R=T/'src';B=Path.home()/'embedded-bsp';W=Path.home()/'embedded-bsp-wifi-20261018'
OLD=Path.home()/'embedded-controlled-v1-20261021/boot_candidate_v1/output/release'
D=T/'boot_work';O=D/'output/release'
assert not D.exists(), 'Preserve previous FSBL build'
O.mkdir(parents=True);(D/'vendor').mkdir();(D/'sdk').mkdir()
shutil.copytree(B/'sdk/master_sdk',D/'sdk/master_sdk',symlinks=True)
(D/'vendor/tools').symlink_to(B/'vendor/tools')
shutil.copyfile(T/'system.hpf',D/'system.hpf')
patch=D/'bsp/gp/fsbl';patch.mkdir(parents=True)
shutil.copyfile(R/'bsp/gp/fsbl/0001-gp-common-reset.patch',patch/'0001-gp-common-reset.patch')
env=os.environ.copy();env.update(TASK=str(D),GP_RESET_BOOT='1',PLATFORM_NAME='project_full_function',FSBL_VARIANT='fsbl_full_function')
with (D/'fsbl.log').open('w') as log:
 subprocess.run(['bash',str(R/'integration/controlled_v1_20261021/boot_inputs/build_fsbl.sh')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
dis=(D/'output/fsbl/disassembly.txt').read_text()
assert re.search(r'\bbl\s+[0-9a-f]+ <AlTop_GPPortEnable>',dis)
assert re.search(r'\bbl\s+[0-9a-f]+ <AlTop_P2F_RstRelease>',dis)
gp=re.search(r'^[0-9a-f]+ <AlTop_GPPortEnable>:(.*?)(?=^[0-9a-f]+ <)',dis,re.M|re.S)[1]
assert '#0x33' in gp and 'str' in gp
with zipfile.ZipFile(T/'system.hpf') as z,zipfile.ZipFile(OLD/'system.hpf') as old:
 assert z.read('HPFs/soc_plat_dts.h')==old.read('HPFs/soc_plat_dts.h'),'PS DT configuration changed; regenerate PS DT before packaging'
 def macros(b):
  values=dict(re.findall(r'^#define\s+(\w+)\s+([^\n]*)',b.decode(),re.M))
  for k in ['HPF_EXPORT_TIME','BITSTREAM_GENERATE_TIME']:values.pop(k,None)
  return values
 assert macros(z.read('HPFs/soc_plat.h'))==macros(old.read('HPFs/soc_plat.h')),'PS/DDR/storage macros changed'
 assert z.read('HPFs/soc_plat.c').replace(b'\r\n',b'\n')==old.read('HPFs/soc_plat.c').replace(b'\r\n',b'\n'),'Executable PS init changed'
 (O/'system.bit').write_bytes(z.read('HPFs/system.bit'))
shutil.copyfile(T/'system.hpf',O/'system.hpf')
shutil.copyfile(D/'output/fsbl/fsbl.elf',O/'fsbl.elf')
for name in ['u-boot.bin','uImage.lz4','system.dtb','boot.cmd']:
 shutil.copyfile(OLD/name,O/name)
(O/'manifest.json').write_text(json.dumps({'root_partuuid':json.loads((OLD/'manifest.json').read_text())['root_partuuid']}))
(O/'boot.bif').write_text((OLD/'boot.bif').read_text())
with (D/'bootgen.log').open('w') as log:
 subprocess.run([str(B/'vendor/tools/bootgen/linux64/bin/albg'),'-w','-log','info','-image','boot.bif','-arch','dr1m90','-o','BOOT.bin'],cwd=O,stdout=log,stderr=subprocess.STDOUT,check=True)
(D/'identity-audit.json').write_text(json.dumps(dict(same_hpf_bit=True,new_fsbl=True,ps_header_and_executable_init_equal=True,dt_header_equal=True,gp_hp0_hp1_reset_mask='0x33',hardware_qualified=False),indent=2)+'\n')
print('NEW_HPF_FSBL_BOOT_CHAIN_OK')
