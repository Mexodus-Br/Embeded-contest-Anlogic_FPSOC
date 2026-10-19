"""Parse top-level pack counters once; never add a parent to its children."""
from pathlib import Path
import json,re,csv

ROOT=Path(__file__).resolve().parent
CAPACITY=dict(lut6_equivalent_gate=52480,slice_gate=52480,registers=104960,eram=280,dsp=240)
BASE=dict(lut6_equivalent_gate=29873,slice_gate=37984,registers=37863,eram=58,dsp=6)

def counter(text, name):
    m=re.search(r'^\s*#'+re.escape(name)+r'\*?\s+(\d+)',text,re.M)
    if not m:raise ValueError(name)
    return int(m[1])

def parse(name, folder):
    text=(folder/'gate_full.area').read_text()
    slices=counter(text,'slice');reg_only=counter(text,'reg only')
    out=dict(configuration=name,phase='gate pack + legalize; not placed/routed',
             slice_gate=slices,register_only_slices=reg_only,
             lut6_equivalent_gate=slices-reg_only,
             lut6_equivalent_definition='derived: packed slices minus register-only slices; gate capacity proxy, not post-place LUT6 utilization',
             registers=counter(text,'slice reg'),pad_registers=counter(text,'pad reg'),
             eram=counter(text,'eram'),dsp=counter(text,'dsp'),virtual_io=counter(text,'virtual IO'),
             physical_io=counter(text,'IO'),clock_resources={k:counter(text,k) for k in ['pll','gclk','lclk','sclk','mlclk','ioclk']},
             clock_resources_boundary='zero external clock fabric in this virtual-IO fixture, not an integrated clock budget',
             source_area=str((folder/'gate_full.area').relative_to(ROOT)).replace('\\','/'),
             external_interconnect_resources='not measured',model_qualified=False)
    core_line=next(line for line in text.splitlines() if line.startswith('|  video_npu_top_'))
    cells=[cell.strip() for cell in core_line.strip('|').split('|')]
    core_lut=sum(int(cells[i]) for i in [2,3,7,8])
    out['ip_body_lut6_equivalent_gate']=core_lut
    out['virtual_boundary_lut6_equivalent_gate']=out['lut6_equivalent_gate']-core_lut
    out['ip_body_other_resources']={k:out[k] for k in ['registers','eram','dsp']}
    out['ip_body_slice']='not separately reported by hierarchy; full fixture slice count above'
    out['virtual_boundary_note']='top minus direct IP instance; these counters are not native PS/HP interconnect cost'
    assert out['virtual_io']==433 and out['registers']>1000 and out['eram']>0
    out['arithmetic_budget']={key:dict(existing=BASE[key],ip=out[key],sum=BASE[key]+out[key],
        capacity=CAPACITY[key],remaining=CAPACITY[key]-BASE[key]-out[key]) for key in CAPACITY}
    out['budget_limit']='gate IP + routed candidate13, with external interconnect omitted; arithmetic budget only'
    return out

if __name__=='__main__':
    full='ip_full_native' if (ROOT/'ip_full_native/gate_full.area').exists() else 'native_full'
    variants={'full_reference':full,'whole_no_video':'ip_whole_no_video',
              'tiny_no_video':'ip_tiny_no_video','mbface_no_video':'ip_mbface_no_video','v3_no_video':'ip_v3_no_video'}
    results=[parse(k,ROOT/f) for k,f in variants.items() if (ROOT/f/'gate_full.area').exists()]
    payload=dict(capacity=CAPACITY,baseline=BASE,baseline_phase='candidate13 route',
                 baseline_setup_ns=-2.173,baseline_hold_ns=.020,configurations=results)
    placed=ROOT/'physical_tiny_100m'
    if (placed/'place.area').exists() and 'NPU_PLACE_DONE' in (placed/'place.log').read_text(errors='replace'):
        text=(placed/'place.area').read_text()
        timing=(placed/'place.timing').read_text()
        active=re.findall(r'^\s*clk\d+:\s+([\d.]+)\s+\d+\s+(npu_\w+)',timing,re.M)
        assert sorted(active)==[('100.000','npu_config'),('100.000','npu_data')],active
        physical=dict(configuration='tiny_no_video',phase='independent virtual-IO place at 100MHz; not routed',
            lut6_equivalent=counter(text,'lut6'),slice=counter(text,'slice'),registers=counter(text,'slice reg'),
            eram=counter(text,'eram'),dsp=counter(text,'dsp'),
            clock_resources={k:counter(text,k) for k in ['pll','gclk','lclk','sclk','mlclk','ioclk']},
            setup_ns=float(re.search(r'SWNS:\s*([-\d.]+)ns',timing)[1]),
            hold_ns=float(re.search(r'HWNS:\s*([-\d.]+)ns',timing)[1]),
            source_area='physical_tiny_100m/place.area',active_clock_mhz=100,
            external_native_interconnect='not measured',integrated_timing_pass=False)
        physical['arithmetic_budget']={k:dict(sum=BASE[b]+physical[k],remaining=CAPACITY[b]-BASE[b]-physical[k])
            for k,b in [('lut6_equivalent','lut6_equivalent_gate'),('slice','slice_gate'),
                        ('registers','registers'),('eram','eram'),('dsp','dsp')]}
        core_line=next(line for line in text.splitlines() if line.startswith('|  video_npu_top_'))
        cells=[cell.strip() for cell in core_line.strip('|').split('|')]
        physical['ip_body_lut6_equivalent']=sum(int(cells[i]) for i in [2,3,7,8])
        physical['boundary_lut6_equivalent']=physical['lut6_equivalent']-physical['ip_body_lut6_equivalent']
        payload['independent_place']=physical
    routed=ROOT/'physical_tiny_route100'
    if (routed/'status.json').exists():
        text=(routed/'route.area').read_text();timing=(routed/'route.timing').read_text()
        route_result=dict(configuration='tiny_no_video',phase='independent virtual-IO route at 100MHz',
            lut6_equivalent=counter(text,'lut6'),slice=counter(text,'slice'),registers=counter(text,'slice reg'),
            eram=counter(text,'eram'),dsp=counter(text,'dsp'),feedthrough=counter(text,'feedthrough'),
            clock_resources={k:counter(text,k) for k in ['pll','gclk','lclk','sclk','mlclk','ioclk']},
            setup_ns=float(re.search(r'SWNS:\s*([-\d.]+)ns',timing)[1]),
            hold_ns=float(re.search(r'HWNS:\s*([-\d.]+)ns',timing)[1]),
            source_area='physical_tiny_route100/route.area',active_clock_mhz=100,
            external_native_interconnect='not measured',integrated_timing_pass=False,
            ip_body_lut6_equivalent=physical['ip_body_lut6_equivalent'],
            boundary_lut6_equivalent=physical['boundary_lut6_equivalent'],
            arithmetic_budget=physical['arithmetic_budget'])
        assert route_result['lut6_equivalent']==physical['lut6_equivalent'] and route_result['slice']==physical['slice']
        payload['independent_route']=route_result
    (ROOT/'resource_results.json').write_text(json.dumps(payload,indent=2)+'\n')
    cols=['configuration','ip_body_lut6_equivalent_gate','virtual_boundary_lut6_equivalent_gate',
          'lut6_equivalent_gate','slice_gate','registers','eram','dsp']
    with (ROOT/'resource_comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');writer.writeheader();writer.writerows(results)
    for row in results:print({k:row[k] for k in cols})
