"""Independent 100MHz OOC TD project, no board pins/PS/IP/bitstream."""
import hashlib,json,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    td=shutil.which('td_commands_prompt')
    if not td:raise RuntimeError('TD command prompt required')
    b=ROOT/'build/td';b.mkdir(parents=True,exist_ok=True)
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
    summary={'tool':td,'device':'DR1M90GEG400','speed':2,'clock_MHz':100,'source_sha256':hashes,'profile':json.loads((ROOT/'schema.json').read_text())['profile'],'fixture':'OOC scan input/output wrapper; no board IO timing claim'}
    for stage in ['gate','place','route']:
        content=(b/(stage+'.timing')).read_text()
        if not re.search(r'100\.000\s+\d+\s+rs485_clk',content):raise RuntimeError('100MHz clock missing')
        setup=float(re.search(r'SWNS:\s*([-\d.]+)ns',content)[1]);hold=float(re.search(r'HWNS:\s*([-\d.]+)ns',content)[1])
        summary[stage]={'setup_wns_ns':setup,'hold_wns_ns':hold,'pass':setup>=0 and hold>=0}
    (b/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    e=ROOT/'evidence/td';e.mkdir(exist_ok=True)
    for name in ['run.tcl','run.log','clock.sdc','probe.v','rtl.area','gate.area','gate.timing','place.area','place.timing','route.area','route.timing','check.timing','summary.json']:
        shutil.copyfile(b/name,e/name)
    print(json.dumps(summary,indent=2))
    if not summary['route']['pass']:raise RuntimeError('routed setup/hold failed')
if __name__=='__main__':main()
