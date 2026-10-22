"""Store wrap carry with each deadline; remove a redundant runtime comparator."""
import json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 out=E/'rtl35_candidate_r1';out.mkdir(exist_ok=False)
 for f in (E/'rtl34_candidate_r1').glob('*'):
  if f.is_file():shutil.copyfile(f,out/f.name)
 s=(R/'pl_safety/rtl/safety_interlock.v').read_text()
 s=replace(s,'parameter LOOKAHEAD_CONTEXT=0)', 'parameter LOOKAHEAD_CONTEXT=0,parameter LOOKAHEAD_WRAP=0)')
 s=replace(s,'reg [63:0] feedback_start[0:2],feedback_deadline[0:2];',
  'reg [63:0] feedback_start[0:2],feedback_deadline[0:2];\n reg watchdog_wrap;reg [2:0] feedback_wrap;')
 s=replace(s,'wire watchdog_expired=owner_active && expired(time_us,watchdog_start,watchdog_deadline);',
  'wire watchdog_expired=owner_active && (LOOKAHEAD_WRAP ? expired_marked(time_us,watchdog_start,watchdog_deadline,watchdog_wrap):expired(time_us,watchdog_start,watchdog_deadline));')
 s=replace(s,'expired(time_us,feedback_start[a],feedback_deadline[a]);',
  '(LOOKAHEAD_WRAP ? expired_marked(time_us,feedback_start[a],feedback_deadline[a],feedback_wrap[a]):expired(time_us,feedback_start[a],feedback_deadline[a]));')
 s=replace(s,'watchdog_start<=0;watchdog_deadline<=0;feedback_seen<=0;',
  'watchdog_start<=0;watchdog_deadline<=0;watchdog_wrap<=0;feedback_wrap<=0;feedback_seen<=0;')
 s=replace(s,'feedback_deadline[i]<=time_us+(config_apply ? config_feedback_us:feedback_timeout_us);',
  "{feedback_wrap[i],feedback_deadline[i]}<={1'b0,time_us}+{33'd0,(config_apply ? config_feedback_us:feedback_timeout_us)};")
 s=replace(s,'feedback_start[i]<=time_us;feedback_deadline[i]<=time_us+feedback_timeout_us;',
  "feedback_start[i]<=time_us;{feedback_wrap[i],feedback_deadline[i]}<={1'b0,time_us}+{33'd0,feedback_timeout_us};")
 old='watchdog_start<=time_us;watchdog_deadline<=time_us+watchdog_timeout_us;';assert s.count(old)==2
 s=s.replace(old,"watchdog_start<=time_us;{watchdog_wrap,watchdog_deadline}<={1'b0,time_us}+{33'd0,watchdog_timeout_us};")
 extra='''
// A u32 timeout added to u64 start wraps iff the carry bit is set. Store
// that carry on the SAME deadline update edge, so this is the original
// CURRENT comparison deadline<start, not a delayed expiry observation.
// now may still jump or wrap arbitrarily; the original two-arc rule holds.
function expired_marked;
 input [63:0] now_us,start_us,deadline_us;input wrapped;
 begin expired_marked=wrapped ? (now_us>=deadline_us && now_us<start_us):
                               (now_us>=deadline_us || now_us<start_us);end
endfunction
// synthesis translate_off
integer wrap_axis;
always @(posedge clk)if(rst_n && LOOKAHEAD_WRAP)begin
 if(watchdog_wrap !== (watchdog_deadline<watchdog_start))$fatal(1,"watchdog current wrap projection mismatch");
 for(wrap_axis=0;wrap_axis<3;wrap_axis=wrap_axis+1)
  if(feedback_wrap[wrap_axis] !== (feedback_deadline[wrap_axis]<feedback_start[wrap_axis]))
   $fatal(1,"feedback current wrap projection mismatch");
end
// synthesis translate_on
'''
 (out/'safety_interlock.v').write_bytes(s.replace('endmodule',extra+'endmodule').encode())
 s=(out/'safety_motion_service.v').read_text()
 s=replace(s,'.LOOKAHEAD_CONTEXT(1)) monitor(','.LOOKAHEAD_CONTEXT(1),.LOOKAHEAD_WRAP(1)) monitor(')
 (out/'safety_motion_service.v').write_bytes(s.encode())
 (out/'wrap_notes.json').write_text(json.dumps({'hashes_computed':False,'register_cost':4,'external_cycles_added':0,
  'math':'For u64 start and u32 delta, carry(start+delta) iff (deadline mod2^64)<start; capture carry and deadline atomically',
  'preserved':'original expiry edge, wrap arcs, arbitrary time jumps, same-edge expiry priority, timeout values and all old default parameters',
  'status':'isolated module validation pending'},indent=2)+'\n')
 print('Prepared RTL35 exact current deadline wrap flags (+4 FF)')
if __name__=='__main__':main()
