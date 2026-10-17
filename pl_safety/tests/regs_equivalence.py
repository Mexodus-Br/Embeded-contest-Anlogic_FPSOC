"""Compare every register interface output before/after AW/W predecode."""
import hashlib,json,subprocess,sys,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'pl_safety'
sys.path.insert(0,str(R/'pl_motion'))
from sim_tools import Simulator

def main():
 out=D/'evidence'/sys.argv[1];out.mkdir(exist_ok=False);sim=Simulator(out)
 source=D/'rtl/safety_regs.v';base_commit='4e75142'
 baseline=subprocess.check_output(['git','show',base_commit+':pl_safety/rtl/safety_regs.v'],cwd=R)
 (out/'baseline.v').write_bytes(baseline.replace(b'module safety_regs(',b'module baseline_regs('))
 inputs={'clk':1,'rst_n':1,'s_awaddr':33,'s_araddr':33,'s_wdata':32,'s_wstrb':4,
  's_awvalid':1,'s_wvalid':1,'s_bready':1,'s_arvalid':1,'s_rready':1,'config_hash':256,'config_ok':1,
  'live_snapshot':2048,'causes':32,'request_ok':1,'clear_ok':1,'home_done':1,'home_cancelled':1,'home_owner':1,'pulse_safe':1,'stopped':1}
 outputs={'s_awready':1,'s_wready':1,'s_arready':1,'s_bvalid':1,'s_rvalid':1,'s_bresp':2,'s_rresp':2,'s_rdata':32,'home_request':1,'clear_request':1,'stop_request':1,'irq':1}
 tb='`timescale 1ns/1ps\n`include "safety_defs.vh"\nmodule tb_regs_equivalence;\n'
 for name,width in inputs.items():tb+='reg '+('' if width==1 else f'[{width-1}:0] ')+name+'=0;\n'
 for suffix in ['', '_ref']:
  for name,width in outputs.items():tb+='wire '+('' if width==1 else f'[{width-1}:0] ')+name+suffix+';\n'
  tb+=('safety_regs dut' if not suffix else 'baseline_regs reference')+'('+','.join('.'+n+'('+n+')' for n in inputs)+','+','.join('.'+n+'('+n+suffix+')' for n in outputs)+');\n'
 lhs=','.join(outputs);rhs=','.join(n+'_ref' for n in outputs)
 tb+=f'''
always #5 clk=~clk;
integer checks=0,cycles=0,seed=32'h71a9632,randomize_live=0;
always @(posedge clk)begin
 cycles=cycles+1;if(cycles>200000)$fatal(1,"watchdog");
 #1;if(rst_n)begin
  checks=checks+1;
  if({{{lhs}}} !== {{{rhs}}}) $fatal(1,"register cycle equivalence failed cycle=%0d",cycles);
 end
end
always @(negedge clk)begin
 if(randomize_live)begin
  live_snapshot=live_snapshot+2048'd1;
  causes=$random(seed)&15;
  home_done=cycles%7==0;home_cancelled=cycles%11==0;
  home_owner=cycles%5!=0;pulse_safe=cycles%3!=0;stopped=cycles%13==0;
  request_ok=cycles%4!=0;clear_ok=cycles%3!=0;
 end
 #2;if(rst_n)begin
  checks=checks+1;
  if({{{lhs}}} !== {{{rhs}}}) $fatal(1,"register combinational equivalence failed");
 end
end
task write;
 input [32:0] address;input [31:0] data;input [3:0] strobe;input integer adelay,wdelay;
 begin
  @(negedge clk);
  fork
   begin
    repeat(adelay)@(negedge clk);s_awaddr=address;s_awvalid=1;
    @(posedge clk);while(!s_awready)@(posedge clk);@(negedge clk);s_awvalid=0;
   end
   begin
    repeat(wdelay)@(negedge clk);s_wdata=data;s_wstrb=strobe;s_wvalid=1;
    @(posedge clk);while(!s_wready)@(posedge clk);@(negedge clk);s_wvalid=0;
   end
  join
  repeat(3)@(negedge clk);s_bready=1;
  @(posedge clk);while(!s_bvalid)@(posedge clk);@(negedge clk);s_bready=0;
 end
endtask
task read;
 input [32:0] address;
 begin
  @(negedge clk);s_araddr=address;s_arvalid=1;
  @(posedge clk);while(!s_arready)@(posedge clk);@(negedge clk);s_arvalid=0;
  repeat(4)@(negedge clk);s_rready=1;
  @(posedge clk);while(!s_rvalid)@(posedge clk);@(negedge clk);s_rready=0;
 end
endtask
reg [11:0] offsets[0:9];integer i;reg [31:0] choice,datum;reg [32:0] address;
initial begin
 offsets[0]=`SAF_REGISTERS_OPCODE;offsets[1]=`SAF_REGISTERS_ARG;offsets[2]=`SAF_REGISTERS_TXN;
 offsets[3]=`SAF_REGISTERS_SUBMIT;offsets[4]=`SAF_REGISTERS_STOP;offsets[5]=`SAF_REGISTERS_IRQ_PENDING;
 offsets[6]=`SAF_REGISTERS_IRQ_MASK;offsets[7]=`SAF_REGISTERS_SNAP_REQ;offsets[8]=0;offsets[9]=12'hffc;
 repeat(3)@(negedge clk);rst_n=1;config_ok=1;request_ok=1;clear_ok=1;pulse_safe=1;
 write({{1'b0,`SAF_BASE}}+`SAF_REGISTERS_OPCODE,1,15,0,3);
 write({{1'b0,`SAF_BASE}}+`SAF_REGISTERS_TXN,1,15,3,0);
 write({{1'b0,`SAF_BASE}}+`SAF_REGISTERS_SUBMIT,1,15,0,0);
 write({{1'b0,`SAF_BASE}}+`SAF_REGISTERS_SUBMIT,1,15,2,0);
 home_done=1;repeat(2)@(negedge clk);home_done=0;
 for(i=0;i<16;i=i+1)begin
  write({{1'b0,`SAF_BASE}}+`SAF_REGISTERS_STOP,1,i,0,i%4);
  write({{1'b0,`SAF_BASE}}+`SAF_REGISTERS_STOP,i,15,i%4,0);
 end
 randomize_live=1;
 for(i=0;i<3000;i=i+1)begin
  choice=$random(seed);address={{1'b0,`SAF_BASE}}+offsets[choice%10];
  if(i%11==0)address=address+1;
  if(i%17==0)address[32]=1;
  datum=$random(seed);if(i%3==0)datum=1;else if(i%3==1)datum=datum%8;
  write(address,datum,i%9==0 ? 4'd7:4'd15,i%4,(i+2)%4);
  if(i%4==0)read({{1'b0,`SAF_BASE}}+(i%2==0 ? `SAF_SNAPSHOT_BASE:12'h02c));
 end
 $display("PASS register equivalence checks=%0d cycles=%0d writes=3036 reads=750",checks,cycles);
 $finish;
end
endmodule
'''
 (out/'tb.v').write_text(tb)
 result={'passed':False,'baseline_commit':base_commit,'baseline_sha256':hashlib.sha256(baseline).hexdigest(),'source_sha256':{source.relative_to(R).as_posix():hashlib.sha256(source.read_bytes()).hexdigest()}}
 try:
  target=out/'equivalence.vvp'
  (out/'compile.log').write_text(sim.compile([source,out/'baseline.v',out/'tb.v'],'tb_regs_equivalence',target,includes=[D/'generated']))
  log=sim.simulate(target,timeout=120);(out/'run.log').write_text(log)
  assert 'PASS register equivalence' in log
  result['passed']=True;print(log)
 except Exception:result['failure']=traceback.format_exc();raise
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
