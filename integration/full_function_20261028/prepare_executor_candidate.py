"""Isolate DIR FF control from wide bookkeeping using the proven STEP cofactor.

No ports, cycles, HOME flow, pulse timing or frozen protocol changes.
Only the reviewed frozen executor is an input; product dirty RTL is not read.
"""
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
p=R/'integration/controlled_v1_20261021/frozen/pl/gp/motion_executor.v'
s=p.read_text();out=H/'rtl';out.mkdir(exist_ok=True)
for text in ['dir<=15;','dir[i]<=home_direction[i];','dir[i]<=plan_positive[i];']:
    assert s.count(text)==1;s=s.replace(text,'')
marker='// Private plan data are overwritten before every RUN grant.'
assert s.count(marker)==1
block='''// DIR is owned by this executor on the same edge as before. FAST_STEP_STOP
// is already checked cycle-for-cycle against safety below. Reuse that exact
// cofactor here so the pad FF does not traverse the wide cancellation mux.
// All state/EN/count/pulse controls and their original priorities stay intact.
integer direction_lane;
always @(posedge clk or negedge rst_n)begin
 if(!rst_n)dir<=15;
 else if(!step_block)begin
  if(own)begin
   if(!( |home_bad))for(direction_lane=0;direction_lane<3;direction_lane=direction_lane+1)
    if(hr[direction_lane] && state==IDLE && !(|disabling) && !(|fault_latched) &&
       enabled[direction_lane] && !step[direction_lane] &&
       dir[direction_lane]!=home_direction[direction_lane] && reached(edge_age[direction_lane],q[direction_lane]))
     dir[direction_lane]<=home_direction[direction_lane];
  end else if(plan_valid && plan_available && commit_ok)
   for(direction_lane=0;direction_lane<4;direction_lane=direction_lane+1)
    if(plan_moving[direction_lane] && dir[direction_lane]!=plan_positive[direction_lane])
     dir[direction_lane]<=plan_positive[direction_lane];
 end
end

'''
s=s.replace(marker,block+marker)
(out/'motion_executor.v').write_bytes(('\n'.join(line.rstrip() for line in s.splitlines())+'\n').encode())
print(out/'motion_executor.v')
