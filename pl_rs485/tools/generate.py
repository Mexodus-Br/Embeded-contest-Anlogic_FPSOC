"""Generate Verilog/C definitions and protocol table from the sole JSON source."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=json.loads((ROOT/'schema.json').read_text())
assert sum(f['width'] for f in s['record']) == s['record_bits']
assert s['profile']['SLAVE_ADDRS']==int('E2E1E0',16)
defs={'VERSION':1,'RECORD_BITS':s['record_bits']}
defs.update(s['profile'])
defs.update({'STATUS_'+k:v for k,v in s['status'].items()})
for f in s['record']:
    defs[f['name']+'_LSB']=f['lsb'];defs[f['name']+'_WIDTH']=f['width']
v=['// GENERATED from schema.json; edit the schema and rerun tools/generate.py.']
c=['/* GENERATED from schema.json. */','#pragma once','#include <stdint.h>']
for k,n in defs.items():
    v.append(f'`define RS_{k} {n}')
    c.append(f'#define RS_{k} {n}u')
v+=['function [7:0] query_code;', 'input [2:0] index;', 'begin case(index)']
l=['function [3:0] query_length;', 'input [2:0] index;', 'begin case(index)']
table=['<!-- GENERATED -->','|index|query|code|request/response bytes|data|source|mode|','|---|---|---|---|---|---|---|']
for i,q in enumerate(s['queries']):
    v.append(f"3'd{i}: query_code=8'h{q['code']:02x};")
    l.append(f"3'd{i}: query_length=4'd{q['data_bytes']};")
    c += [f"#define RS_QUERY_{q['name']} {q['code']}u",f"#define RS_LENGTH_{q['name']} {q['data_bytes']}u"]
    table.append(f"|{i}|{q['name']}|{q['code']:02X}|3/{q['data_bytes']+2}|{q['fields']}|{q['source']}|{q['mode']}|")
v+=['default: query_code=0;','endcase end endfunction']
l+=['default: query_length=0;','endcase end endfunction']
(ROOT/'generated/rs485_defs.vh').write_text('\n'.join(v+l)+'\n')
(ROOT/'generated/rs485_defs.h').write_text('\n'.join(c)+'\n')
(ROOT/'generated/queries.md').write_text('\n'.join(table)+'\n')
params=[]
for k,n in s['profile'].items():
    if k=='QUERY_MASK':continue
    kind='[79:0]' if k=='SLAVE_ADDRS' else 'integer'
    params.append(f'parameter {kind} {k}={n}')
(ROOT/'generated/parameters.vh').write_text('// GENERATED from schema.json\n'+',\n'.join(params)+'\n')
