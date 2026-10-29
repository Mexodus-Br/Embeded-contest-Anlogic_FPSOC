"""Exercise actual candidate function against full-width arithmetic oracle."""
import argparse,json,shutil,subprocess
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
 c=Path(a.candidate).resolve();o=E/a.tag;o.mkdir(exist_ok=False)
 tb='''`timescale 1ns/1ps
module tb;
rs485_telemetry dut();
integer i,j,seed=271821;reg [31:0] x;reg [63:0] y;reg [64:0] n;reg [31:0] expected;
reg [63:0] edges[0:7];
task check;
begin n={33'd0,x}+{1'b0,y};expected=n>65'hffffffff ? 32'hffffffff:n[31:0];
 if(dut.sat(x,y)!==expected)$fatal(1,"saturating addition mismatch x=%h y=%h",x,y);end
endtask
initial begin
 edges[0]=0;edges[1]=1;edges[2]=32'hfffffffe;edges[3]=32'hffffffff;
 edges[4]=64'h100000000;edges[5]=64'h7fffffffffffffff;
 edges[6]=64'h8000000000000000;edges[7]=64'hffffffffffffffff;
 for(i=0;i<8;i=i+1)for(j=0;j<8;j=j+1)begin x=edges[i];y=edges[j];check;end
 for(i=0;i<262144;i=i+1)begin
  x=$random(seed);y={$random(seed),$random(seed)};
  if(i%3==0)y={32'd0,y[31:0]};if(i%7==0)y=~{32'd0,x};check;
 end
 $display("PASS actual 33bit saturation vs65bit oracle checks=262208");$finish;
end
endmodule
'''
 (o/'tb.v').write_text(tb);r=dict(passed=False,hashes_computed=False)
 try:
  for phase,cmd in [('compile',[shutil.which('iverilog'),'-g2005','-s','tb','-I',str(R/'pl_rs485/generated'),'-o',str(o/'test.vvp'),str(c/'rs485_telemetry.v'),str(o/'tb.v')]),('simulation',[shutil.which('vvp'),str(o/'test.vvp')])]:
   with (o/(phase+'.log')).open('w') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=180)
   assert p.returncode==0,phase
  output=(o/'simulation.log').read_text();assert 'checks=262208' in output;r.update(passed=True,output=output);print(output)
 finally:(o/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
