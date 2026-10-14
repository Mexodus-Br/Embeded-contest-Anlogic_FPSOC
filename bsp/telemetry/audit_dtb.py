"""Walk compiled DT address cells/ranges; audit six CPU windows and GIC SPIs.

Preview uses accepted scope storage/clock header until final HPF can be released.
"""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('dtb',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
def get(node,prop,kind='x'):
 r=subprocess.run(['fdtget','-t',kind,str(a.dtb),node,prop],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
 return None if r.returncode else r.stdout.strip()
def cells(node,prop):
 v=get(node,prop);return None if v is None else [int(x,16) for x in v.split()]
def integer(node,prop,default):
 v=cells(node,prop);return v[0] if v else default
def number(v):
 out=0
 for x in v:out=(out<<32)|x
 return out
resources=[];not_cpu=[];interrupts=[]
def children(n):
 r=subprocess.run(['fdtget','-l',str(a.dtb),n],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
 return r.stdout.split() if not r.returncode else []
def translate(base,size,chain):
 for node,parent in reversed(list(zip(chain[1:],chain[:-1]))):
  ranges=cells(node,'ranges')
  if ranges is None:return None
  if not ranges:continue
  ac=integer(node,'#address-cells',2);pc=integer(parent,'#address-cells',2);sc=integer(node,'#size-cells',1);stride=ac+pc+sc
  assert len(ranges)%stride==0,node
  found=False
  for i in range(0,len(ranges),stride):
   child=number(ranges[i:i+ac]);host=number(ranges[i+ac:i+ac+pc]);length=number(ranges[i+ac+pc:i+stride])
   if child<=base and base+size<=child+length:base=host+base-child;found=True;break
  if not found:return None
 return base
def walk(node,chain):
 for name in children(node):
  path=node.rstrip('/')+'/'+name;v=cells(path,'reg');ac=integer(node,'#address-cells',2);sc=integer(node,'#size-cells',1)
  if v is not None:
   if sc==0:not_cpu.append({'node':path,'reason':'size-cells=0, channel/device identifier, not memory window'})
   else:
    assert len(v)%(ac+sc)==0,path
    for i in range(0,len(v),ac+sc):
     b=number(v[i:i+ac]);sz=number(v[i+ac:i+ac+sc]);cpu=translate(b,sz,chain)
     if cpu is None:not_cpu.append({'node':path,'reason':'ancestor has no CPU ranges translation','local_base':b})
     else:resources.append({'node':path,'base':cpu,'size':sz,'status':get(path,'status','s') or 'okay'})
  assert cells(path,'interrupts-extended') is None,'Explicit extended IRQ parser required: '+path
  irq=cells(path,'interrupts');parent=cells(path,'interrupt-parent')
  if parent is None:
   for ancestor in reversed(chain):
    parent=cells(ancestor,'interrupt-parent')
    if parent is not None:break
  if irq is not None:interrupts.append({'node':path,'parent':parent,'cells':irq})
  walk(path,chain+[path])
walk('/',['/'])
expected={0x80400000:'/soc/gp-control@80400000',0x80500000:'/soc/dma@80500000',0x80600000:'/soc/motion-control@80600000',0x80700000:'/soc/rs485-control@80700000',0x80800000:'/soc/rs485-control@80700000',0x80900000:'/soc/dma@80900000'}
for address,node in expected.items():
 matches=[x for x in resources if x['base']==address and x['size']==4096 and x['node']==node];assert len(matches)==1,(address,node)
 for x in resources:
  if x['node']!=node and x['size']:assert x['base']+x['size']<=address or x['base']>=address+4096,x
gic=cells('/interrupt-controller@f9000000','phandle')
if not gic:
 for name in children('/'):
  path='/'+name
  if get(path,'compatible','s') and 'gic' in get(path,'compatible','s'):gic=cells(path,'phandle');break
assert gic,'actual GIC controller not located'
mapped={82:'/soc/gp-control@80400000',83:'/soc/dma@80500000/dma-channel@0',84:'/soc/dma@80500000/dma-channel@30',85:'/soc/motion-control@80600000',86:'/soc/rs485-control@80700000',87:'/soc/rs485-control@80700000',88:'/soc/dma@80900000/dma-channel@30'}
for spi,node in mapped.items():
 irq=cells(node,'interrupts');assert cells(node,'interrupt-parent')==gic,node
 assert any(irq[i:i+3]==[0,spi,4] for i in range(0,len(irq),3)),(spi,node)
 for x in interrupts:
  if x['node']!=node and x['parent']==gic:assert not any(x['cells'][i:i+3]==[0,spi,4] for i in range(0,len(x['cells']),3)),x
assert 'bsp,telemetry-exclusive-controller' in subprocess.check_output(['fdtget','-p',str(a.dtb),'/soc/dma@80900000'],universal_newlines=True).split()
assert children('/soc/dma@80900000')==['dma-channel@30']
assert cells('/soc/rs485-control@80700000','dmas')[-1]==1
result={'status':'PASS_COMPILED_PREVIEW_NOT_FINAL_HPF_OR_BOOT','resources':resources,'non_cpu_reg_entries':not_cpu,'gic_phandle':gic,'irq_spi':list(mapped),'all_windows_4KiB':True,'full_bus_ranges_walk':True,'new_controller':'S2MM-only; own device; no motion-controller flag','hp_internal_reset_release':'await qualified HPF/FSBL; not tested'}
a.out.write_text(json.dumps(result,indent=2)+'\n');print('PASS compiled preview six translated CPU windows and seven level-high GIC SPIs; NOT BOOT RELEASE')
