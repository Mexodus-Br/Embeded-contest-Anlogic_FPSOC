"""Reproducible TD gate synthesis/10ns timing probe; no bitstream/deployment."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--top',default='continuous_motion',choices=['continuous_motion','four_axis_motion'])
    ap.add_argument('--speed',default='2',choices=['2','3'])
    a=ap.parse_args()
    td=shutil.which('td_commands_prompt')
    if not td:raise RuntimeError('TD td_commands_prompt required')
    build=ROOT/'build'/('td_'+a.top);build.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'rtl'/f'{a.top}.v').read_text()
    header=source.split(')(\n',1)[1].split(');',1)[0]
    ports={}
    for match in re.finditer(r'\b(input|output)\s+(?:wire|reg)\s+(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)',header,re.S):
        direction,width,names=match.groups()
        for name in names.split(','):
            name=name.strip()
            if name:ports[name]=(direction,int(width)+1 if width else 1)
    ins={n:w for n,(d,w) in ports.items() if d=='input' and n not in ['clk','rst_n']}
    outs={n:w for n,(d,w) in ports.items() if d=='output'}
    iw,ow=sum(ins.values()),sum(outs.values())
    s=f'module td_probe(input clk,rst_n,serial_in,load,output serial_out);\nreg [{iw-1}:0] inp;\nreg [{ow-1}:0] obs;\n'
    for n,w in outs.items():s+=f'wire [{w-1}:0] {n};\n'
    s+=f'always @(posedge clk) begin\n inp<={{inp[{iw-2}:0],serial_in}};\n if(load) obs<={{{",".join(outs)}}};\n else obs<={{obs[{ow-2}:0],1\'b0}};\nend\nassign serial_out=obs[{ow-1}];\n'
    params=dict(STEP_HIGH_CYCLES=3,STEP_LOW_CYCLES=2,DIR_SETUP_CYCLES=4,
                DIR_HOLD_CYCLES=7,EN_SETUP_CYCLES=5,EN_DISABLE_CYCLES=3,MAX_STEP_HZ=10000000)
    s+=a.top+' #(\n'+',\n'.join(f'.{n}({{4{{64\'d{v}}}}})' for n,v in params.items())+'\n) dut(\n.clk(clk),.rst_n(rst_n),\n'
    k=0;bindings=[]
    for n,w in ins.items():bindings.append(f'.{n}(inp[{k} +: {w}])');k+=w
    bindings += [f'.{n}({n})' for n in outs]
    s+=',\n'.join(bindings)+'\n);\nendmodule\n'
    (build/'probe.v').write_text(s,encoding='ascii')
    (build/'motion.sdc').write_text('create_clock -name motion_clk -period 10 [get_ports {clk}]\n',encoding='ascii')
    files=['motion_fifo.v','motion_planner.v','motion_executor.v','continuous_motion.v'] if a.top=='continuous_motion' else ['four_axis_motion.v']
    t=f'cd {{{build.as_posix()}}}\nimport_device dr1_90.db -package DR1M90GEG400 -speed {a.speed}\n'
    for f in files:t+=f'analyze -file {{{(ROOT/"rtl"/f).as_posix()}}}\n'
    t+=f'analyze -file {{{(build/"probe.v").as_posix()}}}\nelaborate -top td_probe\noptimize_rtl\nread_sdc motion.sdc\nreport_area -file rtl.area\noptimize_gate -maparea gate.area\nread_sdc motion.sdc\nupdate_timing\nreport_timing_summary -file gate.timing -path_num 3\nexport_db gate.db\nputs TD_PROBE_COMPLETE\nexit\n'
    (build/'run.tcl').write_text(t,encoding='ascii')
    with (build/'run.log').open('w',encoding='utf-8') as log:
        p=subprocess.run([td,(build/'run.tcl').as_posix()],cwd=build,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    log=(build/'run.log').read_text()
    # OOC observation ports intentionally have no board location assignment.
    # Preserve that report, but do not confuse it with synthesis/loop failures.
    serious='\n'.join(x for x in log.splitlines() if 'SYN-6021' not in x)
    if p.returncode or 'TD_PROBE_COMPLETE' not in log or re.search(r'\bERROR:|CRITICAL-WARNING',serious):
        raise RuntimeError('TD failed; inspect '+str(build/'run.log'))
    timing=(build/'gate.timing').read_text()
    if not re.search(r'100\.000\s+\d+\s+motion_clk',timing):
        raise RuntimeError('10ns/100MHz clock not present in actual TD timing report')
    summary=dict(top=a.top,tool=td,device='DR1M90GEG400',speed=a.speed,
                 stage='gate estimate; not placed/routed',fixture=params,
                 area=str(build/'gate.area'),timing=str(build/'gate.timing'))
    (build/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    print(next(x.strip() for x in timing.splitlines() if 'SWNS:' in x))

if __name__=='__main__':main()
