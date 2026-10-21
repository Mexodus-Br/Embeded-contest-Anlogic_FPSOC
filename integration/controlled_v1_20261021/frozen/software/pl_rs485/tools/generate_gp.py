"""Short local aliases and contract tables from the shared sole schema."""
import hashlib,json,argparse
from pathlib import Path
R=Path(__file__).resolve().parents[1]
SOURCE=R.parent/'pl_interface/schema.json'
def constants(p):
    c={k.upper():v for k,v in p.items() if type(v)==int}
    for group,pre in [('registers','REG_'),('snapshot_header','SNAP_'),('task_fields','TASK_'),('node_fields','NODE_'),('errors','ERR_')]:
        c.update({pre+k:v for k,v in p[group].items()})
    for group,pre in [('irq_bits','IRQ_'),('cfg_bits','CFG_'),('status_bits','STATUS_'),('feature_bits','FEATURE_')]:
        c.update({pre+k:1<<v for k,v in p[group].items()})
    for group,pre in [('capture_fields','CAP_'),('node_flag_fields','NODE_FLAG_')]:
        for k,(shift,w) in p[group].items():c[pre+k+'_SHIFT']=shift;c[pre+k+'_MASK']=((1<<w)-1)<<shift
    rate=json.loads((R/'rate_design.json').read_text())
    c.update({'CFG_ERR_'+k:v for k,v in rate['implementation']['cfg_error'].items()})
    return c
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');a=ap.parse_args()
    p=json.loads(SOURCE.read_text(encoding='utf-8'))['rs485_gp_profiles']['gp_rs485_v1'];c=constants(p)
    h=hashlib.sha256(SOURCE.read_bytes()).hexdigest();banner='Generated from pl_interface/schema.json SHA256 '+h
    v=['// '+banner,'`ifndef RS485_GP_DEFS','`define RS485_GP_DEFS']+[f"`define RG_{k} 32'h{n:08x}" for k,n in c.items()]+['`endif','']
    C=['/* '+banner+' */','#ifndef RS485_GP_DEFS_H','#define RS485_GP_DEFS_H','#include <stdint.h>']+[f'#define RG_{k} UINT32_C(0x{n:08x})' for k,n in c.items()]+['#endif','']
    table=['# Confirmed RS485 GP registers','','Generated from sole shared schema; '+h,'','|Offset|Register|Access|','|---|---|---|']+[f'|0x{o:03x}|{n}|{p["register_access"][n]}|' for n,o in p['registers'].items()]
    for n,t in {'gp_defs.vh':'\n'.join(v),'gp_defs.h':'\n'.join(C),'gp_registers.md':'\n'.join(table)+'\n'}.items():
        path=R/'generated'/n
        if a.check:
            if path.read_bytes()!=t.encode():raise RuntimeError('stale '+str(path))
        else:path.write_bytes(t.encode())
    print('GP definitions match' if a.check else 'GP definitions generated')
if __name__=='__main__':main()
