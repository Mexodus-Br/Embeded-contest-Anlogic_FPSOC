"""Telemetry constants from pl_interface/schema.json, no separate ABI source."""
import argparse,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];SOURCE=R.parent/'pl_interface/schema.json'
def constants(p):
 c={k.upper():v for k,v in p.items() if type(v)==int}
 for group,pre in [('registers','REG_'),('row_offsets','ROW_'),('snapshot_header','SNAP_'),('errors','ERR_')]:c.update({pre+k:v for k,v in p[group].items()})
 for group,pre in [('flag_bits','FLAG_'),('status_bits','STATUS_'),('irq_bits','IRQ_')]:c.update({pre+k:1<<v for k,v in p[group].items()})
 for n,f in p['frame_fields'].items():
  for k,v in f.items():c['FRAME_'+n+'_'+k.upper()]=v
 for k,v in p['dma'].items():
  if type(v)==int:c['DMA_'+k.upper()]=v
 for k,v in p['dma']['parameters'].items():c['DMA_'+k]=v
 return c
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');a=ap.parse_args()
 p=json.loads(SOURCE.read_text(encoding='utf-8'))['rs485_telemetry'];c=constants(p);h=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
 v=['// Generated telemetry ABI, sole schema SHA256 '+h,'`ifndef RS485_TELEM_DEFS','`define RS485_TELEM_DEFS']+[f"`define RT_{n} 32'h{x:08x}" for n,x in c.items()]+['`endif','']
 C=['/* Generated telemetry ABI, sole schema SHA256 '+h+' */','#ifndef RS485_TELEM_DEFS_H','#define RS485_TELEM_DEFS_H','#include <stdint.h>']+[f'#define RT_{n} UINT32_C(0x{x:08x})' for n,x in c.items()]+['#endif','']
 t=['# Confirmed telemetry registers','','|Offset|Name|Access|','|---|---|---|']+[f'|0x{o:03x}|{n}|{p["register_access"][n]}|' for n,o in p['registers'].items()]
 for n,text in {'telem_defs.vh':'\n'.join(v),'telem_defs.h':'\n'.join(C),'telem_registers.md':'\n'.join(t)+'\n'}.items():
  path=R/'generated'/n
  if a.check:
   if path.read_bytes()!=text.encode():raise RuntimeError('stale '+n)
  else:path.write_bytes(text.encode())
 print('Telemetry definitions match' if a.check else 'Telemetry definitions generated')
if __name__=='__main__':main()
