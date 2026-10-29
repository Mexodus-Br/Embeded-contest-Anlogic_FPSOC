"""Separate collector statistics initialization from asynchronous control reset."""
import json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent

def main():
 out=E/'rtl25_candidate_r1';out.mkdir(exist_ok=False)
 for f in (E/'rtl24_candidate_r1').glob('*.v'):shutil.copyfile(f,out/f.name)
 (out/'before').mkdir()
 p=R/'pl_rs485/rtl/rs485_multirate.v';shutil.copyfile(p,out/'before'/p.name)
 s=p.read_text()
 s=replace(s,'for(i=0;i<TASKS;i=i+1) begin next_due[i]<=0;scheduled[i]<=0;sent[i]<=0;valid_count[i]<=0;missed[i]<=0;max_late[i]<=0;end','')
 init='if(!initialized) begin initialized<=1;for(i=0;i<TASKS;i=i+1) next_due[i]<=time_us;end'
 s=replace(s,init,'if(!initialized)initialized<=1;')
 s=replace(s,'valid_count[inflight]<=sat_add(valid_count[inflight],1);','')
 s=replace(s,'sent[selected]<=sat_add(sent[selected],1);','')
 s=replace(s,'if(lateness>max_late[selected]) max_late[selected]<=sat_add(0,lateness);','')
 s=replace(s,'scheduled[selected]<=sat_add(scheduled[selected],1);','')
 s=replace(s,'next_due[inflight]<=dispatch_time-remainder+dispatch_period;','')
 s=replace(s,'missed[inflight]<=sat_add(missed_operand,quotient);','')
 s=replace(s,"scheduled[inflight]<=sat_add(scheduled_operand,quotient+1'b1);",'')
 s=replace(s,'for(j=0;j<5;j=j+1) next_due[inflight_node*5+j]<=time_us;','')
 s=replace(s,'for(i=0;i<TASKS;i=i+1) next_due[i]<=time_us;','')
 # Externally visible counters still read zero immediately on asynchronous reset.
 for n in ['scheduled','sent','valid_count','missed','max_late']:
  s=s.replace('debug_task<TASKS?'+n, 'initialized && debug_task<TASKS?'+n)
 s=replace(s,'if(view<TASKS) assign observe_tasks[view*160 +:160]={max_late[view],missed[view],valid_count[view],sent[view],scheduled[view]};',
  "if(view<TASKS) assign observe_tasks[view*160 +:160]=initialized ? {max_late[view],missed[view],valid_count[view],sent[view],scheduled[view]}:160'd0;")
 extra='''
// Only the one-bit initialized/control owner needs asynchronous invalidation.
// The first clock after each reset initializes all observable statistics while
// their public read views are still zero. Scheduling already waits for that
// same original initialized edge; no query/configuration cycle is added.
integer si,sj;
reg [63:0] statistics_lateness;
always @(posedge clk)begin
 if(!initialized)begin
  for(si=0;si<TASKS;si=si+1)begin
   scheduled[si]<=0;sent[si]<=0;valid_count[si]<=0;missed[si]<=0;max_late[si]<=0;
  end
 end else begin
  if(engine_done && engine_result==`RS_STATUS_VALID)valid_count[inflight]<=sat_add(valid_count[inflight],1);
  if(state==DISPATCH && !pending && found && enable && !(cfg_valid && cfg_ready) && engine_ready)begin
   sent[selected]<=sat_add(sent[selected],1);
   statistics_lateness=time_us-best_due;
   if(statistics_lateness>max_late[selected])max_late[selected]<=sat_add(0,statistics_lateness);
   if(selected_probe)scheduled[selected]<=sat_add(scheduled[selected],1);
  end
  if(state==ADVANCE_WAIT && div_done)begin
   missed[inflight]<=sat_add(missed_operand,quotient);
   scheduled[inflight]<=sat_add(scheduled_operand,quotient+1'b1);
  end
 end
 // Private deadlines are initialized by the existing startup/configuration
 // state before SCAN can read them. Keep original last-assignment priority.
 if(!initialized)for(si=0;si<TASKS;si=si+1)next_due[si]<=time_us;
 if(engine_done && engine_result==`RS_STATUS_VALID && inflight_probe)
  for(sj=0;sj<5;sj=sj+1)next_due[inflight_node*5+sj]<=time_us;
 if(state==ADVANCE_WAIT && div_done)next_due[inflight]<=dispatch_time-remainder+dispatch_period;
 if(state==CFG_WAIT && !engine_active && cfg_revision!=32'hffffffff)
  for(si=0;si<TASKS;si=si+1)next_due[si]<=time_us;
end
'''
 (out/p.name).write_text(s.replace('endmodule',extra+'endmodule'))
 (out/'notes.json').write_text(json.dumps({'hashes_computed':False,'collector_removed_async_source_bits':'SLAVE_COUNT*5*(5*32+64) = 3360 for three nodes',
  'public_counter_reset':'immediate zero via original async initialized owner; synchronous array initialization before original first SCAN',
  'latency_changes':0,'status':'module validation pending'},indent=2)+'\n')
 print('Prepared RTL25 collector candidate; product sources unchanged')
if __name__=='__main__':main()
