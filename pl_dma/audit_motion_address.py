"""Read-only audit of current recovery-image CPU resources for motion GP."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'bsp/artifacts/dma-recovery-release/debug/dma-board.expanded.dts'
p=json.loads((ROOT/'pl_interface/schema.json').read_text(encoding='utf-8'))['motion_integration_profiles']['gp_motion_v1']
text=source.read_text(encoding='utf-8');ranges=[]
for m in re.finditer(r'\breg\s*=\s*([^;]+);',text):
 values=[int(x,0) for x in re.findall(r'\b(?:0[xX][0-9a-fA-F]+|[0-9]+)\b',m[1])]
 if len(values)%4:continue
 for k in range(0,len(values),4):
  base=(values[k]<<32)|values[k+1];size=(values[k+2]<<32)|values[k+3]
  if base<0x60000000 or not size:continue
  ranges.append({'base':base,'size':size,'line':text[:m.start()].count('\n')+1})
overlap=[r for r in ranges if max(r['base'],p['base'])<min(r['base']+r['size'],p['base']+p['size'])]
if overlap:raise RuntimeError('motion window collision '+str(overlap))
result={'status':'NO_MOTION_COLLISION_IN_CURRENT_RECOVERY_DTS','source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'motion_base':p['base'],'motion_size':p['size'],'ranges':ranges,'limits':'Numeric CPU resources including disabled nodes; child bus addresses excluded. Final BSP HPF/DT/IRQ map must be re-audited; no BSP file was edited.'}
(ROOT/'pl_dma/MOTION_ADDRESS_MAP.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
