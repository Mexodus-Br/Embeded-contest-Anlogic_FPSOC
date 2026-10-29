"""Full 1197-bit prepared record, short resets and immediate post-flush enqueue."""
import argparse,json,shutil,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
TB='''`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,flush=0,iv=0,ready=0;reg [1196:0] data=0;
wire ir,ov,ref_ir,ref_ov,sv;wire [1196:0] od,ref_od;wire [31:0] level,ref_level;
motion_plan_fifo #(.DEPTH(8)) dut(clk,rst_n,flush,iv,ir,data,ov,ready,od,level,ready,sv);
motion_fifo #(.WIDTH(1197),.DEPTH(8),.SPARE_SLOT(1)) golden(clk,rst_n,flush,iv,ref_ir,data,ref_ov,ready,ref_od,ref_level);
integer k,j,seed=20261020,checks=0,full_dual=0;
always @(posedge clk)begin
 if(rst_n && ov && ready && iv && ir && level==8)full_dual=full_dual+1;
 #1;
 if({ir,ov,level} !== {ref_ir,ref_ov,ref_level})$fatal(1,"wide FIFO ownership differs k=%0d",k);
 if(ov && od !== ref_od)$fatal(1,"1197-bit prepared record differs k=%0d",k);
 checks=checks+1;
end
initial begin
 repeat(3)@(negedge clk);rst_n=1;
 for(k=0;k<12000;k=k+1)begin
  @(negedge clk);
  iv=(k%100<30) ? 1:$random(seed);ready=(k%100<15) ? 0:$random(seed);
  flush=(k%127==0 || k%127==1 || k%997==0);
  for(j=0;j<37;j=j+1)data[j*32+:32]=$random(seed);
  data[1196:1184]=$random(seed);
  if(k%331==0)begin #1;rst_n=0;#1;
   if(level!=0 || ov || ir)$fatal(1,"async reset must immediately revoke public queue");
   #1;rst_n=1;
  end
 end
 @(negedge clk);iv=0;ready=1;flush=0;repeat(20)@(negedge clk);
 if(level!=0 || full_dual<100)$fatal(1,"wide FIFO coverage inadequate");
 $display("PASS full prepared record differential bits=1197 checks=%0d full_dual=%0d",checks,full_dual);$finish;
end
endmodule
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
 c=Path(a.candidate).resolve();out=E/a.tag;out.mkdir(exist_ok=False);(out/'tb.v').write_text(TB)
 result={'passed':False,'hashes_computed':False}
 try:
  for phase,cmd in [('compile',[shutil.which('iverilog'),'-g2005','-s','tb','-o',str(out/'test.vvp'),str(c/'motion_fifo.v'),str(out/'tb.v')]),('simulation',[shutil.which('vvp'),str(out/'test.vvp')])]:
   with (out/f'{phase}.log').open('w') as log:proc=subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=120)
   assert proc.returncode==0,phase
  text=(out/'simulation.log').read_text();assert 'PASS full prepared record differential' in text;result.update(passed=True,output=text);print(text)
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
