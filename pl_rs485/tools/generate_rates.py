"""Generate multi-rate constants from rate_design.json and wire schema.json."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
d=json.loads((R/'rate_design.json').read_text());s=json.loads((R/'schema.json').read_text())
p=next(p for p in d['candidate_profiles'] if p['name']==d['implementation']['default_profile'])
packed=sum(n<<(32*i) for i,n in enumerate(p['period_us']))
values={'DEFAULT_PERIODS':packed,'MIN_PERIOD_US':d['implementation']['min_period_us'],
 'MAX_PERIOD_US':d['implementation']['max_period_us'],'LOAD_LIMIT_PPM':d['implementation']['load_limit_ppm'],
 'RESPONSE_BUDGET_US':d['budget_assumptions']['response_start_bound_us'],
 'FAILURE_THRESHOLD':d['confirmed']['node_failure_threshold'],'BACKOFF_US':d['confirmed']['node_backoff_us']}
v=['// GENERATED from rate_design.json and schema.json.']
params=['parameter integer NORMAL_CYCLES=QUIET_CYCLES','parameter integer ERROR_CYCLES=QUIET_CYCLES']
for k,n in values.items():
 params.append(f"parameter {'[159:0]' if k=='DEFAULT_PERIODS' else 'integer'} {k}="+(f"160'h{n:040x}" if k=='DEFAULT_PERIODS' else str(n)))
v+= [f'`define MR_CFG_{k} {n}' for k,n in d['implementation']['cfg_error'].items()]
v+=['function [31:0] query_wire_us;','input [2:0] q;','begin case(q)']
for i,q in enumerate(s['queries']):
 v.append(f"3'd{i}: query_wire_us=(64'd{5+q['data_bytes']}*10*BIT_CYCLES*1000000+CLK_HZ-1)/CLK_HZ;")
v+=['default: query_wire_us=0;','endcase end endfunction']
(R/'generated/rate_parameters.vh').write_text('// GENERATED\n'+',\n'.join(params)+'\n')
(R/'generated/rate_defs.vh').write_text('\n'.join(v)+'\n')
c=['/* GENERATED */','#pragma once']+[f'#define MR_CFG_{k} {n}u' for k,n in d['implementation']['cfg_error'].items()]
c += [f'#define MR_{k} {n}u' for k,n in values.items() if k!='DEFAULT_PERIODS']
c += [f'#define MR_DEFAULT_PERIOD_{i}_US {n}u' for i,n in enumerate(p['period_us'])]
(R/'generated/rate_defs.h').write_text('\n'.join(c)+'\n')
