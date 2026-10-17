"""Exploratory current-timer predicate: full transaction outputs vs frozen RTL."""
import argparse,hashlib,json,sys,traceback
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2]
sys.path.insert(0,str(R/'pl_motion'));from sim_tools import Simulator

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--production',action='store_true');a=ap.parse_args();o=E/a.tag;o.mkdir(exist_ok=False);sim=Simulator(o)
 source=R/'pl_rs485/rtl/rs485_transaction.v' if a.production else E/'poll_zero_candidate.v'
 old=E/'baseline/rs485_transaction.v';ref=o/'reference.v';ref.write_text(old.read_text().replace('module rs485_transaction #(','module reference_transaction #('))
 ins={'clk':1,'rst_n':1,'time_us':64,'rx':1,'request_valid':1,'request_address':8,'request_query':3,'request_sequence':32}
 outs={'request_ready':1,'tx':1,'de':1,'active':1,'done':1,'result':8,'bus_blocked':1,'push':1,'push_data':256,'accepted':32,'errors':32,'ignored_rx':32}
 tb='`timescale 1ns/1ps\nmodule tb;parameter [31:0] P=5;\n'
 for n,w in ins.items():tb+='reg '+('' if w==1 else f'[{w-1}:0] ')+n+'=0;\n'
 for suffix,module,inst in [('', 'rs485_transaction','dut'),('_ref','reference_transaction','reference')]:
  for n,w in outs.items():tb+='wire '+('' if w==1 else f'[{w-1}:0] ')+n+suffix+';\n'
  tb+=module+''' #(.CLK_HZ(100),.BAUD(10),.POLL_CYCLES(P),.TIMEOUT_CYCLES(240),.INTERBYTE_CYCLES(30),.RETRIES(1),.PRE_CYCLES(2),.POST_CYCLES(2),.TURN_CYCLES(2),.NORMAL_CYCLES(20),.ERROR_CYCLES(30)) '''+inst+'('+','.join('.'+n+'('+n+')' for n in ins)+','+','.join('.'+n+'('+n+suffix+')' for n in outs)+');\n'
 lhs=','.join(outs);rhs=','.join(n+'_ref' for n in outs)
 tb+='''always #5 clk=~clk;
 integer i,j,seed=32'h501720,checks=0;reg [31:0] injected;
 always @(posedge clk)begin #1;if(rst_n)begin
  checks=checks+1;
  if({LHS} !== {RHS})$fatal(1,"transaction public outputs differ");
  if(dut.poll_zero !== (dut.poll_timer==0))$fatal(1,"current timer predicate invariant");
 end end
 initial begin
 #2;rst_n=0;rx=1;#10;rst_n=1;
 for(i=0;i<40000;i=i+1)begin
  @(negedge clk);time_us=time_us+1;request_valid=$random(seed)&1;
  request_address=1+($random(seed)&3);request_query=$random(seed)%5;request_sequence=request_sequence+1;
  rx=(i%1000<700)?1:($random(seed)&1);
  if(i%257==0)begin
   case((i/257)%7)
    0:injected=0;1:injected=1;2:injected=2;3:injected=32'hffffffff;
    4:injected=32'h80000000;5:injected=P;default:injected=P-1;
   endcase
   dut.poll_timer=injected;reference.poll_timer=injected;dut.poll_zero=injected==0;
  end
  if(i%5003==0)rst_n=0;else rst_n=1;
 end
 @(negedge clk);$display("PASS transaction differential checks=%0d poll=%h",checks,P);$finish;
 end
 endmodule
'''.replace('{LHS}','{'+lhs+'}').replace('{RHS}','{'+rhs+'}')
 (o/'tb.v').write_text(tb)
 sources=[source,ref,R/'pl_rs485/rtl/uart_rx.v',R/'pl_rs485/rtl/uart_tx.v',o/'tb.v']
 result={'passed':False,'source_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'cases':[]}
 try:
  for p in [0,1,2,5,50000,0x80000000,0xffffffff]:
   exe=o/(str(p)+'.vvp');log=sim.compile(sources,'tb',exe,includes=[R/'pl_rs485/generated'],extra=[f"-Ptb.P=32'd{p}"]);(o/(str(p)+'_compile.log')).write_text(log)
   log=sim.simulate(exe,timeout=90);(o/(str(p)+'.log')).write_text(log);assert 'PASS transaction differential' in log;result['cases'].append(log);print(log,flush=True)
  result['passed']=True
 except Exception:result['failure']=traceback.format_exc();raise
 finally:(o/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
