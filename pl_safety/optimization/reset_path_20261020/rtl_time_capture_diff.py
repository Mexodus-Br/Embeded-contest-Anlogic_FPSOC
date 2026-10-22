"""Same-EMIT raw/timing capture, independent Python modulo-time oracle."""
import argparse,json,random,re,shutil,subprocess
from pathlib import Path
from equivalence import outputs
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
 c=Path(a.candidate).resolve();out=E/a.tag;out.mkdir(exist_ok=False)
 original=(R/'pl_rs485/rtl/rs485_transaction.v').read_text();(out/'reference.v').write_text(original.replace('module rs485_transaction','module ref_transaction',1))
 rand=random.Random(20261020);mask=(1<<64)-1;vectors=[]
 for k in range(65536):
  ref=rand.getrandbits(64);d=[0,1,(1<<63)-1,1<<63,(1<<63)+1,mask][k%6] if k%8<6 else rand.getrandbits(64)
  request=(ref+d)&mask;event=rand.getrandbits(64) if k%3 else (ref+1)&mask
  flags=int(((request-ref)&mask)<1<<63)|(int(((event-ref)&mask)<1<<63)<<1)
  vectors.append((ref<<130)|(request<<66)|(event<<2)|flags)
 (out/'vectors.hex').write_text(''.join(f'{v:049x}\n' for v in vectors))
 fields=outputs(original);decl='\n'.join('wire '+w+' '+n+',ref_'+n+';' for n,w in fields.items())
 args=".clk(clk),.rst_n(rst_n),.time_us(now_us),.rx(1'b1),.request_valid(1'b0),.request_address(8'he0),.request_query(3'd4),.request_sequence(32'd0)"
 inst=[]
 for mod,name,suffix in [('rs485_transaction','dut',''),('ref_transaction','golden','ref_')]:
  ports=args+','+','.join('.'+n+'('+suffix+n+')' for n in fields)
  if name=='dut':ports+=',.next_round_reference(round_next),.protection_time_valid(time_valid)'
  inst.append(mod+" #(.INTERLOCK_PREDECODE(1),.PROTECTION_ADDRS(80'he2e1e0)) "+name+'('+ports+');')
 compare='\n'.join(f'if({n} !== ref_{n})$fatal(1,"EMIT original output differs {n}");' for n in fields)
 tb='''`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg [63:0] now_us=0,round_next=0;
wire [1:0] time_valid;reg [193:0] vectors[0:65535];
integer k,checks=0;
'''+decl+'\n'+'\n'.join(inst)+'''
initial begin
 $readmemh("vectors.hex",vectors);repeat(3)@(negedge clk);rst_n=1;
 for(k=0;k<65536;k=k+1)begin
  @(negedge clk);round_next=vectors[k][193:130];now_us=vectors[k][65:2];
  dut.state=7;golden.state=7;
  dut.request_time=vectors[k][129:66];golden.request_time=vectors[k][129:66];
  dut.event_time=vectors[k][65:2];golden.event_time=vectors[k][65:2];
  dut.address=8'he0+k%3;golden.address=8'he0+k%3;
  dut.command=8'h3e;golden.command=8'h3e;
  dut.length=1;golden.length=1;dut.status=k%3;golden.status=k%3;
  dut.payload=k%256;golden.payload=k%256;
  @(posedge clk);#1;
'''+compare+'''
  if(!push || time_valid !== vectors[k][1:0])$fatal(1,"same-EMIT timestamp qualification mismatch k=%0d",k);
  checks=checks+1;
  @(negedge clk);round_next=round_next+1;
  @(posedge clk);#1;
'''+compare+'''
  if(push)$fatal(1,"new qualification must not add/repeat push");
 end
 $display("PASS same-EMIT original outputs and Python modulo-time vectors=%0d",checks);$finish;
end
endmodule
'''
 (out/'tb.v').write_text(tb);result={'passed':False,'hashes_computed':False}
 try:
  for phase,cmd in [('compile',[shutil.which('iverilog'),'-g2005','-I',str(R/'pl_rs485/generated'),'-s','tb','-o',str(out/'test.vvp'),str(c/'rs485_transaction.v'),str(R/'pl_rs485/rtl/uart_rx.v'),str(R/'pl_rs485/rtl/uart_tx.v'),str(out/'reference.v'),str(out/'tb.v')]),('simulation',[shutil.which('vvp'),str(out/'test.vvp')])]:
   with (out/f'{phase}.log').open('w') as log:proc=subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=120)
   assert proc.returncode==0,phase
  log=(out/'simulation.log').read_text();assert 'PASS same-EMIT original outputs' in log;result.update(passed=True,vectors=65536,output=log);print(log)
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
