"""Verify reviewed DMA image identity, actual DT resources and installed files."""
import hashlib,json,subprocess,sys,zipfile,tempfile
from pathlib import Path
task=Path(sys.argv[1]);out=task/'output';release=out/'release';dtb=release/'system.dtb'
def fdt(path,prop):return subprocess.check_output(['fdtget','-t','x',str(dtb),path,prop],universal_newlines=True).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((release/'manifest.json').read_text())
for name,record in m['files'].items():assert sha(release/name)==record['sha256'],name
assert fdt('/soc/gp-control@80400000','reg')=='0 80400000 0 1000'
assert fdt('/soc/gp-control@80400000','interrupts')=='0 52 4'
assert fdt('/soc/dma@80500000','reg')=='0 80500000 0 1000'
assert fdt('/soc/dma@80500000/dma-channel@0','interrupts')=='0 53 4'
assert fdt('/soc/dma@80500000/dma-channel@30','interrupts')=='0 54 4'
assert fdt('/soc/dma@80500000','anlogic,addrwidth')=='20'
assert fdt('/soc/dma@80500000','anlogic,sg-length-width')=='10'
for p in ['/soc/gp-control@80400000','/soc/dma@80500000','/dma-loopback-test']:
 assert subprocess.check_output(['fdtget',str(dtb),p,'status'],universal_newlines=True).strip()=='okay'
props=subprocess.check_output(['fdtget','-p',str(dtb),'/soc/dma@80500000'],universal_newlines=True).split()
assert 'anlogic,include-sg' not in props and 'bsp,loopback-pair' in props
resources=[]
for node in subprocess.check_output(['fdtget','-l',str(dtb),'/soc'],universal_newlines=True).split():
 try:reg=[int(v,16) for v in fdt('/soc/'+node,'reg').split()]
 except subprocess.CalledProcessError:continue
 if len(reg)%4:continue
 for i in range(0,len(reg),4):
  base=(reg[i]<<32)|reg[i+1];size=(reg[i+2]<<32)|reg[i+3]
  resources.append({'node':node,'base':base,'size':size})
  if node!='dma@80500000' and size:assert base+size<=0x80500000 or base>=0x80501000,node
kr='6.1.111-rt42-bsp-sd1'
files=['usr/bin/dma-accept','usr/bin/gp-accept','usr/bin/bsp-readonly-check',
       'lib/modules/'+kr+'/extra/bsp_dma_loop.ko','lib/modules/'+kr+'/extra/bsp_gp.ko',
       'lib/modules/'+kr+'/kernel/drivers/dma/anlogic/anlogic-dma-engine.ko','lib/modules/'+kr+'/modules.dep']
installed={}
with tempfile.TemporaryDirectory(prefix='bsp-dma-verify-') as tmp:
 for i,name in enumerate(files):
  dest=Path(tmp)/str(i)
  subprocess.run(['debugfs','-R','dump /'+name+' '+str(dest),str(release/'rootfs.ext4')],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  assert dest.is_file(),name
  installed[name]=sha(dest)
  assert installed[name]==sha(out/'rootfs-target'/name),name
with zipfile.ZipFile(release/'system.hpf') as z:assert z.read('HPFs/system.bit')==(release/'system.bit').read_bytes()
subprocess.run(['fsck.vfat','-n',str(release/'boot.vfat')],check=True)
subprocess.run(['e2fsck','-fn',str(release/'rootfs.ext4')],check=True)
result={'status':'IMAGE_VERIFIED_NOT_DEPLOYED_OR_BOARD_TESTED','sd_image_sha256':m['files']['sdcard.img']['sha256'],'root_partuuid':m['root_partuuid'],'cpu_soc_numeric_resources':resources,'installed_file_sha256':installed,'dt_spi':[82,83,84],'dt_simple':True,'dma_mask_bits':32,'btt_width':16,'kernel_config_sha256':sha(out/'debug/kernel.config'),'kernel_symvers_sha256':sha(out/'debug/Module.symvers'),'provider_symvers_sha256':sha(out/'debug/dma-provider.Module.symvers')}
(out/'debug/dma-image-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
