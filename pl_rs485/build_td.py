"""Independent 100MHz OOC TD project, no board pins/PS/IP/bitstream."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--multirate',action='store_true');ap.add_argument('--gp',action='store_true');ap.add_argument('--fast',action='store_true');ap.add_argument('--tag',default='');a=ap.parse_args()
    if a.fast and not (a.multirate or a.gp):raise ValueError('--fast requires --multirate')
    if a.tag and not a.tag.replace('_','').replace('-','').isalnum():raise ValueError('invalid tag')
    td=shutil.which('td_commands_prompt')
    if not td:raise RuntimeError('TD command prompt required')
    name=('td_multirate_fast' if a.fast else 'td_multirate') if a.multirate else 'td'
    if a.gp:name='td_gp_fast' if a.fast else 'td_gp'
    if a.tag:name+='_'+a.tag
    b=ROOT/'build'/name;b.mkdir(parents=True,exist_ok=True)
    staged=[]
    for p in sorted((ROOT/'rtl').glob('*.v')):
        source=p.read_text()
        source=re.sub(r'`include "([^"]+)"',lambda m:(ROOT/'generated'/m[1]).read_text(),source)
        q=b/p.name;q.write_text(source,encoding='ascii');staged.append(q)
    # Observation wrapper retains all functional outputs for OOC timing/area.
    wrapper='''module td_probe(input clk,rst_n,scan_in,load,rx_async,output scan_out,tx,de);
reg [70:0] inp;
reg [416:0] obs;
wire valid,busy;
wire [255:0] record;
wire [31:0] level,dropped,accepted,errors,ignored;
always @(posedge clk) begin
 inp<={inp[69:0],scan_in};
 if(load) obs<={record,level,dropped,accepted,errors,ignored,valid};
 else obs<={obs[415:0],busy};
end
assign scan_out=obs[416];
rs485_master dut(.clk(clk),.rst_n(rst_n),.enable(inp[70]),.query_mask(inp[69:65]),
 .time_us(inp[63:0]),.rx(rx_async),.tx(tx),.de(de),.record_ready(inp[64]),
 .record_valid(valid),.record_data(record),.fifo_level(level),.dropped(dropped),
 .accepted(accepted),.errors(errors),.ignored_rx(ignored),.busy(busy));
endmodule
'''
    if a.multirate or a.gp:
        module='rs485_gp_bridge' if a.gp else 'rs485_multirate'
        header=(ROOT/('rtl/'+module+'.v')).read_text().split(')(input',1)[1].split(');',1)[0]
        ports={}
        for m in re.finditer(r'\b(input|output)\s+(?:wire|reg)\s*(?:\[(\d+):0\]\s*)?(.*?)(?=\binput|\boutput|$)','input'+header,re.S):
            direction,width,names=m.groups()
            for n in names.split(','):
                n=n.strip()
                if n:ports[n]=(direction,int(width)+1 if width else 1)
        ins={n:w for n,(d,w) in ports.items() if d=='input' and n not in ['clk','rst_n','rx']}
        outs={n:w for n,(d,w) in ports.items() if d=='output'}
        iw,ow=sum(ins.values()),sum(outs.values())
        wrapper=f'module td_probe(input clk,rst_n,scan_in,load,rx_async,output scan_out,tx,de);\nreg [{iw-1}:0] inp;\nreg [{ow-1}:0] obs;\n'
        for n,w in outs.items():
            if n not in ['tx','de']:wrapper+=f'wire [{w-1}:0] {n};\n'
        wrapper+=f"always @(posedge clk) begin inp<={{inp[{iw-2}:0],scan_in}}; if(load) obs<={{{','.join(outs)}}}; else obs<={{obs[{ow-2}:0],1'b0}}; end\nassign scan_out=obs[{ow-1}];\n"
        params=''
        if a.fast:
            clock=json.loads((ROOT/'schema.json').read_text())['profile']['CLK_HZ'];cycles=clock//1000
            params=f'#(.NORMAL_CYCLES({cycles}),.POLL_CYCLES({cycles}))'
        wrapper+=module+' '+params+' dut(.clk(clk),.rst_n(rst_n),.rx(rx_async),\n'
        bindings=[];offset=0
        for n,w in ins.items():bindings.append(f'.{n}(inp[{offset} +: {w}])');offset+=w
        bindings += [f'.{n}({n})' for n in outs]
        wrapper+=',\n'.join(bindings)+');\nendmodule\n'
    (b/'probe.v').write_text(wrapper,encoding='ascii');staged.append(b/'probe.v')
    # rst_n is required to be synchronously released by the integrating system.
    (b/'clock.sdc').write_text('create_clock -name rs485_clk -period 10 [get_ports {clk}]\n',encoding='ascii')
    t=f'cd {{{b.as_posix()}}}\nimport_device dr1_90.db -package DR1M90GEG400 -speed 2\n'
    for p in staged:t+=f'analyze -file {{{p.as_posix()}}}\n'
    t+='''elaborate -top td_probe
optimize_rtl
read_sdc clock.sdc
report_area -file rtl.area
optimize_gate -maparea gate.area
read_sdc clock.sdc
update_timing
report_timing_summary -file gate.timing -path_num 3
export_db gate.db
legalize_phy_inst
place
update_timing -mode manhattan
report_timing_summary -file place.timing -path_num 3
report_area -io_info -file place.area
export_db place.db
route
update_timing -mode final
report_timing_summary -file route.timing -path_num 3
report_area -io_info -file route.area
check_timing -verbose -file check.timing
report_route_status -drc -file route.drc
export_db route.db
puts RS485_TD_COMPLETE
exit
'''
    (b/'run.tcl').write_text(t,encoding='ascii')
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['rtl','generated'] for p in (ROOT/folder).glob('*') if p.is_file()}
    with (b/'run.log').open('w',encoding='utf-8') as log:
        p=subprocess.run([td,(b/'run.tcl').as_posix()],cwd=b,stdout=log,stderr=subprocess.STDOUT,timeout=900)
    log=(b/'run.log').read_text()
    # OOC scan/serial ports intentionally have no physical board assignments.
    serious='\n'.join(x for x in log.splitlines() if 'SYN-6021' not in x)
    if p.returncode or 'RS485_TD_COMPLETE' not in log or re.search(r'\bERROR:|CRITICAL-WARNING',serious):raise RuntimeError('TD failed; build/td/run.log retained')
    summary={'tool':td,'top':'rs485_gp_bridge' if a.gp else 'rs485_multirate' if a.multirate else 'rs485_master','fast_simulation_candidate':a.fast,'device':'DR1M90GEG400','speed':2,'clock_MHz':100,'source_sha256':hashes,'profile':json.loads((ROOT/'schema.json').read_text())['profile'],'fixture':'OOC scan input/output wrapper; no board IO timing claim'}
    summary['constraint_sha256']=hashlib.sha256((b/'clock.sdc').read_bytes()).hexdigest()
    summary['fixture_sha256']=hashlib.sha256((b/'probe.v').read_bytes()).hexdigest()
    if a.multirate or a.gp:summary['rate_design_sha256']=hashlib.sha256((ROOT/'rate_design.json').read_bytes()).hexdigest()
    for stage in ['gate','place','route']:
        content=(b/(stage+'.timing')).read_text()
        if not re.search(r'100\.000\s+\d+\s+rs485_clk',content):raise RuntimeError('100MHz clock missing')
        setup=float(re.search(r'SWNS:\s*([-\d.]+)ns',content)[1]);hold=float(re.search(r'HWNS:\s*([-\d.]+)ns',content)[1])
        summary[stage]={'setup_wns_ns':setup,'hold_wns_ns':hold,'pass':setup>=0 and hold>=0}
    (b/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    e=ROOT/'evidence'/name;e.mkdir(exist_ok=True)
    for name in ['route.qor','run.tcl','run.log','clock.sdc','probe.v','rtl.area','gate.area','gate.timing','place.area','place.timing','route.area','route.timing','check.timing','summary.json']:
        shutil.copyfile(b/name,e/name)
    print(json.dumps(summary,indent=2))
    if not summary['route']['pass']:raise RuntimeError('routed setup/hold failed')
if __name__=='__main__':main()
