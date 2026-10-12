"""Real TD converter + GP core OOC gate/10ns probe. No board bitstream."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
from prepare_gp_ip import prepare
ROOT=Path(__file__).resolve().parent

def inputs_hash():
    files=[ROOT/'rtl/gp_control_regs.v',ROOT/'rtl/gp_control_top.v',ROOT/'rtl/gp_ps_write_adapter.v',ROOT/'rtl/gp_ps_control_top.v',ROOT.parent/'pl_interface/generated/interface_defs.vh']
    return {str(p):hashlib.sha256(p.read_text().encode()).hexdigest() for p in files}

def physical(b,td,manifest,top):
    saved=json.loads((b/'summary.json').read_text())
    if saved['inputs_sha256_lf']!=inputs_hash() or saved['converter']!=manifest:
        raise RuntimeError('gate inputs differ; rerun gate synthesis')
    if saved['top']!=top:raise RuntimeError('gate top differs; rerun gate synthesis')
    if saved['constraints_sha256']!=hashlib.sha256((b/'gp.sdc').read_bytes()).hexdigest():
        raise RuntimeError('gate constraints differ; rerun gate synthesis')
    if not saved['timing_pass']:raise RuntimeError('gate must pass before physical flow')
    t=f'cd {{{b.as_posix()}}}\nimport_device dr1_90.db -package DR1M90GEG400 -speed 2\nimport_db gate.db\nread_sdc gp.sdc\nlegalize_phy_inst\nplace\nupdate_timing -mode manhattan\nreport_timing_summary -file place.timing -path_num 5\nreport_area -io_info -file place.area\nexport_db place.db\nroute\nupdate_timing -mode final\nreport_timing_summary -file route.timing -path_num 5\nreport_area -io_info -file route.area\ncheck_timing -verbose -file route.check\nreport_route_status -drc -file route.drc\nexport_db route.db\nputs GP_TD_PHYSICAL_COMPLETE\nexit\n'
    (b/'physical.tcl').write_text(t)
    with (b/'physical.log').open('w') as log:
        r=subprocess.run([td,(b/'physical.tcl').as_posix()],cwd=b,stdout=log,stderr=subprocess.STDOUT,timeout=900)
    log=(b/'physical.log').read_text()
    if r.returncode or 'GP_TD_PHYSICAL_COMPLETE' not in log or re.search(r'\bERROR:|CRITICAL-WARNING',log):raise RuntimeError('TD physical failure: '+str(b/'physical.log'))
    start=log.index('RUN-1002 : start command "report_route_status')
    end=log.index('RUN-1002 : start command "export_db route.db"',start)
    (b/'route_check.log').write_text(log[start:end])
    results={}
    for stage in ['place','route']:
        report=(b/(stage+'.timing')).read_text()
        if not re.search(r'100\.000\s+\d+\s+gp_clk',report):raise RuntimeError('100MHz clock missing')
        w=float(re.search(r'SWNS:\s*([-\d.]+)ns',report).group(1));h=float(re.search(r'HWNS:\s*([-\d.]+)ns',report).group(1))
        results[stage]={'wns_ns':w,'hold_wns_ns':h,'timing_pass':w>=0 and h>=0,
                        'critical_start':re.search(r'Begin Point\s*:\s*(.+)',report).group(1),
                        'critical_end':re.search(r'End Point\s*:\s*(.+)',report).group(1)}
    (b/'physical_summary.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
    if not results['route']['timing_pass']:raise RuntimeError('final GP timing failed')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',default='r1')
    ap.add_argument('--top',choices=['gp_control_top','gp_ps_control_top'],default='gp_ps_control_top')
    ap.add_argument('--place-route',action='store_true');ap.add_argument('--physical-only',action='store_true');args=ap.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+',args.tag):raise ValueError('invalid tag')
    vendor,manifest=prepare();td=shutil.which('td_commands_prompt')
    b=ROOT/'build'/('td_gp_'+args.tag);b.mkdir(parents=True,exist_ok=True)
    if args.physical_only:
        physical(b,td,manifest,args.top);return
    source=(ROOT/('rtl/'+args.top+'.v')).read_text()
    header=source.split('module '+args.top+'(',1)[1].split(');',1)[0]
    ports={}
    for m in re.finditer(r'\b(input|output)\s+wire\s+(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)',header,re.S):
        direction,width,names=m.groups()
        for n in names.split(','):
            n=n.strip()
            if n:ports[n]=(direction,int(width)+1 if width else 1)
    ins={n:w for n,(d,w) in ports.items() if d=='input' and n not in ['clk_100m','arst_n']}
    outs={n:w for n,(d,w) in ports.items() if d=='output' and n!='gp0_aclk'}
    iw,ow=sum(ins.values()),sum(outs.values())
    probe=f'module gp_td_probe(input clk,arst_n,serial_in,load,output serial_out);\nreg [{iw-1}:0] inp;\nreg [{ow-1}:0] obs;\n'
    for n,w in outs.items():probe+=f'wire [{w-1}:0] {n};\n'
    probe+=f'always @(posedge clk) begin inp<={{inp[{iw-2}:0],serial_in}}; if(load) obs<={{{",".join(outs)}}}; else obs<={{obs[{ow-2}:0],1\'b0}}; end\nassign serial_out=obs[{ow-1}];\n'
    probe+=args.top+' dut(.clk_100m(clk),.arst_n(arst_n),.gp0_aclk(),\n'
    k=0;bindings=[]
    for n,w in ins.items():bindings.append(f'.{n}(inp[{k} +: {w}])');k+=w
    bindings += [f'.{n}({n})' for n in outs]
    probe+=',\n'.join(bindings)+'\n);\nendmodule\n'
    (b/'probe.v').write_text(probe)
    sdc='create_clock -name gp_clk -period 10 [get_ports {clk}]\n'
    (b/'gp.sdc').write_text(sdc)
    files=[vendor]
    definitions=(ROOT.parent/'pl_interface/generated/interface_defs.vh').read_text()
    for name in ['gp_control_regs','gp_control_top','gp_ps_write_adapter','gp_ps_control_top']:
        original=(ROOT/'rtl'/(name+'.v')).read_text()
        if original.count('`include "generated/interface_defs.vh"')>1:raise RuntimeError('unexpected include')
        expanded=b/(name+'.v')
        expanded.write_text(original.replace('`include "generated/interface_defs.vh"',definitions))
        files.append(expanded)
    files.append(b/'probe.v')
    t=f'cd {{{b.as_posix()}}}\nimport_device dr1_90.db -package DR1M90GEG400 -speed 2\n'
    for f in files:t+=f'analyze -file {{{f.as_posix()}}}\n'
    t+='elaborate -top gp_td_probe\noptimize_rtl\nwrite_verilog rtl_netlist.v\nread_sdc gp.sdc\noptimize_gate -maparea gate.area\nread_sdc gp.sdc\nupdate_timing\nreport_timing_summary -file gate.timing -path_num 5\ncheck_timing -verbose -file gate.check\nexport_db gate.db\nputs GP_TD_GATE_COMPLETE\nexit\n'
    (b/'run.tcl').write_text(t)
    with (b/'run.log').open('w') as log:
        r=subprocess.run([td,(b/'run.tcl').as_posix()],cwd=b,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    log=(b/'run.log').read_text()
    serious='\n'.join(x for x in log.splitlines() if 'SYN-6021' not in x)
    if r.returncode or 'GP_TD_GATE_COMPLETE' not in log or re.search(r'\bERROR:|CRITICAL-WARNING',serious):raise RuntimeError('TD GP failed: '+str(b/'run.log'))
    timing=(b/'gate.timing').read_text()
    if not re.search(r'100\.000\s+\d+\s+gp_clk',timing):raise RuntimeError('actual report missing 100MHz gp_clk')
    wns=float(re.search(r'SWNS:\s*([-\d.]+)ns',timing).group(1))
    hold=float(re.search(r'HWNS:\s*([-\d.]+)ns',timing).group(1))
    result={'status':'GATE_ESTIMATE_NOT_BOARD_TIMING','top':args.top,'tool':td,'device':'DR1M90GEG400','reference_speed':2,'clock_period_ns':10,
            'gate_wns_ns':wns,'gate_hold_wns_ns':hold,'timing_pass':wns>=0 and hold>=0,'converter':manifest,
            'critical_start':re.search(r'Begin Point\s*:\s*(.+)',timing).group(1),
            'critical_end':re.search(r'End Point\s*:\s*(.+)',timing).group(1),
            'reports':{x:str(b/x) for x in ['gate.timing','gate.area','gate.check','run.log']},
            'source_sha256_lf':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_text().encode()).hexdigest() for p in files},
            'inputs_sha256_lf':inputs_hash(),'constraints_sha256':hashlib.sha256((b/'gp.sdc').read_bytes()).hexdigest()}
    (b/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['timing_pass']:raise RuntimeError('GP 10ns gate timing failed')
    if args.place_route:physical(b,td,manifest,args.top)

if __name__=='__main__':main()
