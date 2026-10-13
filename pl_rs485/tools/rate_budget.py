"""Planning calculation from existing wire schema; not hardware rate evidence."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def calculate(profile, schema, design):
    base=schema['profile']; nodes=base['SLAVE_COUNT']; clock=base['CLK_HZ']
    bit_cycles=(clock+base['BAUD']//2)//base['BAUD']
    byte_us=10*bit_cycles*1000000/clock
    prepost_us=(base['PRE_CYCLES']+base['POST_CYCLES'])*1000000/clock
    response_us=design['budget_assumptions']['response_start_bound_us']
    wire=load=requests=0.0;rates=[]
    for q,p in zip(schema['queries'],profile['period_us']):
        hz=1000000/p if p else 0
        transmission_us=(3+q['data_bytes']+2)*byte_us
        cost_us=max(profile['min_start_gap_us'],transmission_us+prepost_us+response_us+profile['normal_guard_us'])
        requests+=nodes*hz;wire+=nodes*hz*transmission_us/1000000;load+=nodes*hz*cost_us/1000000
        rates.append({'query':f"{q['code']:02X}",'per_node_hz':hz,'normal_service_budget_us':round(cost_us,2)})
    return {'profile':profile['name'],'per_query':rates,'requests_per_second':requests,
            'wire_fraction':round(wire,6),'normal_service_fraction':round(load,6),
            'planning_limit':design['budget_assumptions']['nominal_load_limit'],
            'within_planning_limit':load<=design['budget_assumptions']['nominal_load_limit']}
def main():
    schema=json.loads((ROOT/'schema.json').read_text())
    design=json.loads((ROOT/'rate_design.json').read_text())
    results=[calculate(p,schema,design) for p in design['candidate_profiles']]
    fast=dict(design['candidate_profiles'][1]);fast.update(name='fast_rates_with_legacy_guard_NOT_ADMISSIBLE',normal_guard_us=10000,min_start_gap_us=10000)
    results.append(calculate(fast,schema,design))
    output={'source':'schema.json + rate_design.json','assumptions':design['budget_assumptions'],
            'scope':'normal traffic only; admission estimate, not scheduling or physical proof','results':results}
    (ROOT/'evidence/rate_budget.json').write_text(json.dumps(output,indent=2)+'\n')
    for r in results:
        print(f"{r['profile']}: {r['requests_per_second']:.0f} requests/s; wire={100*r['wire_fraction']:.2f}%; normal-service budget={100*r['normal_service_fraction']:.2f}%; admissible={r['within_planning_limit']}")
if __name__=='__main__':main()
