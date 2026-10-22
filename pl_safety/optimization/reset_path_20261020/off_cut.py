"""Exact next-state projection of the local RUN-OFF mailbox predicate."""
import json, re, shutil, subprocess, sys, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));from equivalence import outputs
sys.path.insert(0,str(ROOT/'pl_safety/tests'));from interlock_rs485_fixture import render

def candidate():
    s=subprocess.check_output(['git','show','07745a8:pl_rs485/rtl/rs485_gp_regs.v'],cwd=ROOT).decode()
    old=' assign interlock_stop_commit=INTERLOCK_SUPPORT && write_fire && aw_run &&\n   w_run_clear && reset_count==0 && interlock_idle;'
    new=''' // Current mailbox predicate projected from exact next captured values.
 // Only the local request is registered; current safety idle remains a fence.
 // No extra OFF/expiry cycle: off_request_q equals the old predicate now.
 reg off_request_q;
 wire capture_aw=s_awvalid && s_awready;
 wire capture_w=s_wvalid && s_wready;
 wire next_ah=!write_fire && (ah || capture_aw);
 wire next_wh=!write_fire && (wh || capture_w);
 wire next_bvalid=write_fire || (s_bvalid && !s_bready);
 wire next_aw_run=capture_aw ? s_awaddr==BASE+`RG_REG_RUN:aw_run;
 wire next_w_clear=capture_w ?
   (s_wstrb[0] && s_wdata[7:0]==0 &&
    (!s_wstrb[1] || s_wdata[15:8]==0) && (!s_wstrb[2] || s_wdata[23:16]==0) &&
    (!s_wstrb[3] || s_wdata[31:24]==0)):w_run_clear;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)off_request_q<=0;
  else off_request_q<=next_ah && next_wh && !next_bvalid && next_aw_run && next_w_clear && !next_reset;
 assign interlock_stop_commit=INTERLOCK_SUPPORT && off_request_q && interlock_idle;'''
    assert s.count(old)==1
    return s.replace(old,new)

if __name__=='__main__':
    tag=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',tag)
    out=HERE/tag;out.mkdir(exist_ok=False)
    s=candidate();source=out/'rs485_gp_regs.v';source.write_text(s)
    old=subprocess.check_output(['git','show','07745a8:pl_rs485/rtl/rs485_gp_regs.v'],cwd=ROOT).decode()
    ref=out/'reference.v';ref.write_text(old.replace('module rs485_gp_regs #','module ref_rs485_gp_regs #',1))
    tb=render();m=re.search(r'rs485_gp_regs\s*#\(.*?\)\s*dut\(',tb,re.S);assert m
    end=tb.index(');',m.end())+2;clone=tb[m.start():end].replace('rs485_gp_regs #','ref_rs485_gp_regs #',1).replace(' dut(',' reference(',1)
    widths={};ports=outputs(s)
    for port,expr in re.findall(r'\.(\w+)\(([^()]*)\)',clone):
        if port in ports and re.fullmatch(r'\w+',expr):widths[expr]=ports[port]
    clone=re.sub(r'\.(\w+)\(([^()]*)\)',lambda m:'.'+m[1]+'('+m[2]+('_ref' if m[1] in ports and m[2] in widths else '')+')',clone)
    observe='\n'.join('wire '+w+' '+n+'_ref;' for n,w in widths.items())+'\n'+clone+'''
integer projection_checks=0;
always @(posedge clk)begin #1;if(rst_n)begin
 projection_checks=projection_checks+1;
 if(dut.off_request_q !== (dut.write_fire && dut.aw_run && dut.w_run_clear && dut.reset_count==0))
  $fatal(1,"OFF projection not exact current state");
'''+ '\n'.join(f'if({n} !== {n}_ref)$fatal(1,"GP OFF full output {n}");' for n in widths)+ '\nend end\n'
    extra='''
 // Repeated OFF commands, idle qualification changes and independent AW/W
 // capture across all strobes retain their existing commit and response edge.
 for(si=0;si<16;si=si+1)begin
  safe_idle=1;safe_off=1;wr(`RG_REG_LOCAL_RESET,1,15,0);ticks(4);
  ap={32'd1000000,128'd0};am=16;cr=1;
  wr(`RG_REG_RUN,1,15,0);safe_idle=0;wr(`RG_REG_RUN,0,si[3:0],si==0 ? 0:2);
  safe_idle=1;wr(`RG_REG_RUN,0,15,0);ticks(2);
 end
 // Inductive boundary proof: arbitrary mailbox/reset states with consistent
 // captured addresses and data, then let the real RTL execute one edge.
 // Only the induction start is injected; the projection is never repaired
 // after the edge being checked. Covers B stalls, reset countdown and new
 // independent AW/W captures, including LOCAL_RESET commit priority.
 for(si=0;si<65536;si=si+1)begin
  @(negedge clk);
  dut.ah=si[0];reference.ah=si[0];dut.wh=si[1];reference.wh=si[1];
  dut.s_bvalid=si[2];reference.s_bvalid=si[2];
  dut.reset_count=si[4:3];reference.reset_count=si[4:3];
  dut.aw_run=si[5];reference.aw_run=si[5];
  dut.aw_reset=!si[5];reference.aw_reset=!si[5];
  dut.wa={1'b0,`RG_BASE}+(si[5] ? `RG_REG_RUN:`RG_REG_LOCAL_RESET);reference.wa=dut.wa;
  dut.wd=si[6] ? 0:1;reference.wd=dut.wd;dut.ws=15;reference.ws=15;
  dut.w_run_clear=si[6];reference.w_run_clear=si[6];
  dut.w_reset=!si[6];reference.w_reset=!si[6];
  safe_idle=si[7];safe_off=si[8];s_awvalid=si[9];s_wvalid=si[10];s_bready=si[11];
  s_awaddr={1'b0,`RG_BASE}+(si[12] ? `RG_REG_RUN:`RG_REG_LOCAL_RESET);
  s_wdata=si[13] ? 0:1;s_wstrb=si[15:14]==0 ? 0:15;
  #1;dut.off_request_q=dut.write_fire && dut.aw_run && dut.w_run_clear && dut.reset_count==0;
  @(posedge clk);#2;
 end
 @(negedge clk);s_awvalid=0;s_wvalid=0;s_bready=0;
'''
    tb=tb.replace('  $display("PASS interlock_rs485_guard',extra+'  $display("PASS interlock_rs485_guard')
    tb=tb.replace('endmodule',observe+'\nendmodule').replace('$finish;','$display("PROJECTION_CHECKS %0d",projection_checks);$finish;')
    bench=out/'tb.v';bench.write_text(tb);result={'passed':False,'hashes_computed':False}
    try:
        cmd=[shutil.which('iverilog'),'-g2005','-s','tb_interlock_rs485','-o',str(out/'test.vvp')]
        for name in ['pl_rs485/generated','pl_rs485/tests']:cmd+=['-I',str(ROOT/name)]
        cmd+=list(map(str,[source,ref,ROOT/'pl_rs485/rtl/record_fifo.v',bench]))
        for phase,command in [('compile',cmd),('simulation',[shutil.which('vvp'),str(out/'test.vvp')])]:
            with (out/(phase+'.log')).open('w') as log:
                p=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=120)
            assert p.returncode==0,(phase,p.returncode)
        log=(out/'simulation.log').read_text();assert 'PASS interlock_rs485_guard' in log
        result.update(passed=True,cycles=int(re.search('PROJECTION_CHECKS (\d+)',log)[1]))
        print(result)
    except Exception:
        result['failure']=traceback.format_exc();raise
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
