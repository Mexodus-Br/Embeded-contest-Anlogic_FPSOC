"""Read-only numeric register-range audit against actual BSP expanded DTS."""
import hashlib,json,re
from pathlib import Path
from prepare_ip import ROOT,profile,digest
source=ROOT.parent/'bsp/artifacts/gp-release/debug/gp-board.expanded.dts'
text=source.read_text(encoding='utf-8');ranges=[]
for m in re.finditer(r'\breg\s*=\s*([^;]+);',text):
 values=[int(x,0) for x in re.findall(r'\b(?:0[xX][0-9a-fA-F]+|[0-9]+)\b',m[1])]
 # Four-cell CPU physical resources; child-bus/Cpu-ID registers are excluded.
 if len(values)%4:continue
 for k in range(0,len(values),4):
  a=(values[k]<<32)|values[k+1];size=(values[k+2]<<32)|values[k+3]
  if a<0x60000000 or not size:continue
  ranges.append({'base':a,'size':size,'line':text[:m.start()].count('\n')+1})
p=profile()['address'];overlap=[r for r in ranges if max(r['base'],p['base'])<min(r['base']+r['size'],p['base']+p['size'])]
if overlap:raise RuntimeError('new DMA window conflicts with BSP '+str(overlap))
if not any(r['base']==0x80400000 and r['size']==4096 for r in ranges):raise RuntimeError('actual GP resource missing')
result={'status':'NO_DMA_REGISTER_WINDOW_COLLISION_IN_CURRENT_BSP','source':str(source),'sha256':digest(source),
        'new_dma_window':p,'audited_numeric_cpu_ranges':ranges,
        'limits':'Includes disabled numeric CPU register resources. Child bus addresses are not CPU physical addresses. PS HPF address XML is empty; BSP must audit final HPF, DDR decode and newly generated DTS before deployment.'}
(ROOT/'ADDRESS_MAP.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
