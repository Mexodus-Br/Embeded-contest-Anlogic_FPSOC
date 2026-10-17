"""Cycle-exact old controller oracle, plus threshold/carry boundary injection."""
import argparse,hashlib,json,sys,traceback
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[2];D=R/'pl_safety'
sys.path.insert(0,str(R/'pl_motion'));from sim_tools import Simulator
I={'clk':1,'rst_n':1,'time_us':64,'qualified':1,'active':4,'released':4,'home_request':1,'clear_request':1,'stop_request':1,'idle':1,'pulse_safe':1,'external_abort':1,'executor_fault':3,'position_valid':4,'pulse_event':4,'config_valid':4}
O={'config_ok':1,'normal_inhibit':1,'home_owner':1,'home_enable':1,'home_reference':1,'home_complete':1,'home_run':3,'home_direction':3,'home_period':192,'home_reference_position':192,'stop_motion':1,'disable_motion':1,'invalidate':4,'clear_executor':1,'state':4,'causes':32,'first_cause':32,'first_time':64,'event_sequence':64,'home_start_time':64,'home_done_time':64,'hit_mask':3,'released_mask':3,'done_mask':3,'travel':192,'accepted':1,'rejected':1,'home_done':1,'home_cancelled':1,'request_ok':1,'clear_ok':1}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args();out=E/a.tag;out.mkdir(exist_ok=False);sim=Simulator(out)
 old=E/'baseline/safety_controller.v';ref=out/'reference.v';ref.write_text(old.read_text().replace('module safety_controller #(','module reference_controller #('))
 tb='`timescale 1ns/1ps\nmodule tb;parameter [63:0] T=5;\n'
 for n,w in I.items():tb+='reg '+('' if w==1 else f'[{w-1}:0] ')+n+'=0;\n'
 params='.CONFIG_APPROVED(1),.SEARCH_PERIOD({3{64\'d20}}),.PULL_PERIOD({3{64\'d20}}),.PRE_PERIOD({3{64\'d20}}),.SEARCH_MAX_STEPS({3{T}}),.PULL_MAX_STEPS({3{T}}),.PRE_MAX_STEPS({3{T}}),.PRE_DISTANCE({3{T}}),.PULL_DISTANCE({3{T}}),.SEARCH_MAX_US(64\'d10000),.PULL_MAX_US(64\'d10000),.PRE_MAX_US(64\'d10000)'
 for suf,module,inst in [('', 'safety_controller','dut'),('_ref','reference_controller','reference')]:
  for n,w in O.items():tb+='wire '+('' if w==1 else f'[{w-1}:0] ')+n+suf+';\n'
  tb+=module+' #('+params+') '+inst+'('+','.join('.'+n+'('+n+')' for n in I)+','+','.join('.'+n+'('+n+suf+')' for n in O)+');\n'
 lhs=','.join(O);rhs=','.join(n+'_ref' for n in O)
 tb+="""
 always #5 clk=~clk;
 integer checks=0,seed=32'h501710,cy=0,i,j,ph;
 reg [63:0] value;
 task verify;begin
 checks=checks+1;
 if({LHS} !== {RHS})begin
  $display("cycle=%0d count=%h state=%d pulse=%b",cy,dut.count[0],state,pulse_event);
  $fatal(1,"controller all-output equivalence");
 end
 for(j=0;j<3;j=j+1)begin
  if(dut.search_at[j] !== (dut.count[j]>=T) || dut.search_before[j] !== (T!=0 && dut.count[j]==T-1) || dut.count_full[j] !== (&dut.count[j])) $fatal(1,"boundary invariant");
 end
 end endtask
 always @(posedge clk)begin cy=cy+1;#1;if(rst_n)verify;end
 always @(negedge clk)begin #2;if(rst_n)verify;end
 task set_count;input [63:0] v;integer k;begin
 for(k=0;k<3;k=k+1)begin
  dut.count[k]=v;reference.count[k]=v;
  dut.search_at[k]=v>=T;dut.search_before[k]=T!=0 && v==T-1;
  dut.pre_at[k]=v>=T;dut.pre_before[k]=T!=0 && v==T-1;
  dut.pull_at[k]=v>=T;dut.pull_before[k]=T!=0 && v==T-1;
  dut.count_full[k]=&v;
 end
 end endtask
 initial begin
 #2;rst_n=0;#10;rst_n=1;qualified=1;released=15;idle=1;pulse_safe=1;config_valid=15;
 // Natural control/state transitions with random contacts, stops and pulses.
 for(i=0;i<16000;i=i+1)begin
  @(negedge clk);time_us=time_us+1;
  pulse_event=$random(seed)&7;active=(i%100<75)?0:($random(seed)&7);
  released=~active;home_request=i%100==1;clear_request=i%100==0;
  stop_request=i%293==0;external_abort=i%419==0;executor_fault=i%509==0;
  idle=i%5!=0;pulse_safe=i%3!=0;
 end
 // Inject mathematically consistent current state at unsigned carry/threshold
 // boundaries; subsequent updates/flags are entirely implementation-driven.
 for(ph=1;ph<=9;ph=ph+1)for(i=0;i<12;i=i+1)begin
  @(negedge clk);home_request=0;clear_request=0;stop_request=0;external_abort=0;executor_fault=0;
  active=0;released=0;idle=1;pulse_safe=0;time_us=0;
  dut.state=ph;reference.state=ph;dut.causes=0;reference.causes=0;
  dut.phase_time=0;reference.phase_time=0;dut.phase_deadline=10000;dut.phase_wrap=0;dut.pre_mask=7;reference.pre_mask=7;
  dut.hit_mask=0;reference.hit_mask=0;dut.released_mask=0;reference.released_mask=0;
  case(i)
   0:value=0;1:value=1;2:value=T-2;3:value=T-1;4:value=T;5:value=T+1;
   6:value=64'hfffffffffffffffd;7:value=64'hfffffffffffffffe;8:value=64'hffffffffffffffff;
   9:value=64'h7fffffffffffffff;10:value=64'h8000000000000000;default:value=64'hffffffff;
  endcase
  set_count(value);pulse_event=0;
  #1;verify;
  repeat(5)begin @(negedge clk);pulse_event=$random(seed)&7;end
 end
 @(negedge clk);rst_n=0;#11;rst_n=1;repeat(5)@(negedge clk);
 $display("PASS controller equivalence checks=%0d threshold=%h",checks,T);$finish;
 end
 endmodule
""".replace('{LHS}','{'+lhs+'}').replace('{RHS}','{'+rhs+'}')
 (out/'tb.v').write_text(tb);sources=[E/'deadline_candidate.v',ref,out/'tb.v']
 result={'passed':False,'baseline_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'source_sha256':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'cases':[]}
 try:
  for t in [0,1,2,5,0xffffffff,0x100000000,0xfffffffffffffffe,0xffffffffffffffff]:
   exe=out/(str(t)+'.vvp');log=sim.compile(sources,'tb',exe,includes=[D/'generated'],extra=[f"-Ptb.T=64'd{t}"]);(out/(str(t)+'_compile.log')).write_text(log)
   log=sim.simulate(exe,timeout=90);(out/(str(t)+'.log')).write_text(log);assert 'PASS controller equivalence' in log;result['cases'].append(log);print(log,flush=True)
  result['passed']=True
 except Exception:result['failure']=traceback.format_exc();raise
 finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
