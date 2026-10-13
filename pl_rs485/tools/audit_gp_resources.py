"""Read-only audit of current numeric CPU ranges; not final BSP approval."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
    p=json.loads((R.parent/'pl_interface/schema.json').read_text(encoding='utf-8'))['rs485_gp_profiles']['gp_rs485_v1']
    source=R.parent/'bsp/artifacts/gp-release/debug/gp-board.expanded.dts'
    t=source.read_text(encoding='utf-8');ranges=[]
    for m in re.finditer(r'\breg\s*=\s*([^;]+);',t):
        v=[int(x,0) for x in re.findall(r'\b(?:0[xX][0-9a-fA-F]+|[0-9]+)\b',m[1])]
        if len(v)%4:continue
        for k in range(0,len(v),4):
            a=v[k]<<32|v[k+1];size=v[k+2]<<32|v[k+3]
            if a<0x60000000 or not size:continue
            ranges.append({'base':a,'size':size,'line':t[:m.start()].count('\n')+1})
    collisions=[x for x in ranges if max(x['base'],p['base'])<min(x['base']+x['size'],p['base']+p['size'])]
    irq_matches=[]
    for m in re.finditer(r'\binterrupts\s*=\s*([^;]+);',t):
        vals=[int(x,0) for x in re.findall(r'\b(?:0[xX][0-9a-fA-F]+|[0-9]+)\b',m[1])]
        if p['irq_spi'] in vals:irq_matches.append({'text':m[1],'line':t[:m.start()].count('\n')+1})
    result={'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'base':p['base'],'size':p['size'],'irq_line':p['irq_line'],'spi':p['irq_spi'],
      'numeric_cpu_ranges':ranges,'collisions':collisions,'interrupt_cell_matches':irq_matches,
      'limits':'Same numeric four-cell method as DMA audit; includes disabled resources; not complete child-bus translation or final HPF/DT/GIC mapping proof. Existing three-way router has no RS485 port. BSP final audit and router extension required.'}
    (R/'evidence/GP_RESOURCE_AUDIT.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    if collisions or irq_matches:raise RuntimeError('candidate conflict; inspect audit')
    print('PASS current numeric resource audit; final BSP mapping remains pending')
if __name__=='__main__':main()
