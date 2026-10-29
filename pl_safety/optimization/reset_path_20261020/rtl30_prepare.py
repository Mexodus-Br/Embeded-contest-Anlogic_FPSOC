"""Local physical FIFO cleanup behind same-edge logical invalidation."""
import json,shutil
from pathlib import Path
from rtl24_prepare import replace
R=Path(__file__).resolve().parents[3];E=Path(__file__).resolve().parent
def main():
 out=E/'rtl30_candidate_r1';out.mkdir(exist_ok=False)
 for f in (E/'rtl29_candidate_r1').glob('*'):
  if f.is_file():shutil.copyfile(f,out/f.name)
 fifo=(R/'pl_motion/rtl/motion_fifo.v').read_text()
 extra='''
// Private prepared-plan FIFO. Public ready/valid/level retain original cycles.
// flush invalidates the logical epoch on its original edge; its registered
// marker resets the PHYSICAL pointer basis on the following edge. Speculative
// storage activity on a flush edge is unreachable by a valid consumer.
// The spare address preserves old-head data for every valid full pop/push.
module motion_plan_fifo #(parameter WIDTH=1197,DEPTH=8)(
 input wire clk,rst_n,flush,in_valid,
 output wire in_ready,input wire [WIDTH-1:0] in_data,
 output wire out_valid,input wire out_ready,output wire [WIDTH-1:0] out_data,
 output wire [31:0] level,input wire storage_out_ready,output wire storage_valid
);
 localparam STORAGE_DEPTH=DEPTH+1;
 localparam PB=$clog2(STORAGE_DEPTH),CB=$clog2(DEPTH+1);
 reg [WIDTH-1:0] memory[0:STORAGE_DEPTH-1];
 reg [PB-1:0] rd,wr;reg [CB-1:0] count;reg invalidate_q;
 wire [PB-1:0] read_pointer=invalidate_q ? {PB{1'b0}}:rd;
 wire [PB-1:0] write_pointer=invalidate_q ? {PB{1'b0}}:wr;
 wire [CB-1:0] owned_count=invalidate_q ? {CB{1'b0}}:count;
 assign level=owned_count;
 assign storage_valid=rst_n && owned_count!=0;
 assign out_valid=storage_valid && !flush;
 wire public_pop=out_valid && out_ready;
 assign in_ready=rst_n && !flush && (owned_count<DEPTH || public_pop);
 assign out_data=memory[read_pointer];
 wire store_pop=owned_count!=0 && storage_out_ready;
 wire store_push=in_valid && (owned_count<DEPTH || store_pop);
 always @(posedge clk)if(store_push)memory[write_pointer]<=in_data;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rd<=0;wr<=0;count<=0;invalidate_q<=0;end
  else begin
   invalidate_q<=flush;
   wr<=store_push ? (write_pointer==STORAGE_DEPTH-1 ? 0:write_pointer+1'b1):write_pointer;
   rd<=store_pop ? (read_pointer==STORAGE_DEPTH-1 ? 0:read_pointer+1'b1):read_pointer;
   case({store_push,store_pop})
    2'b10:count<=owned_count+1'b1;
    2'b01:count<=owned_count-1'b1;
    default:count<=owned_count;
   endcase
  end
 end
 // synthesis translate_off
 initial if(DEPTH<2 || WIDTH<1)$fatal(1,"invalid prepared FIFO parameters");
 always @(posedge clk)if(rst_n)begin
  if(owned_count>DEPTH || rd>=STORAGE_DEPTH || wr>=STORAGE_DEPTH)$fatal(1,"prepared FIFO bounds");
  if((wr>=rd ? wr-rd:wr+STORAGE_DEPTH-rd)!=count)$fatal(1,"physical prepared FIFO distance invariant");
  if(store_pop && store_push && write_pointer==read_pointer)$fatal(1,"prepared RAM collision");
  if(!flush && storage_out_ready !== out_ready)$fatal(1,"prepared storage/public readiness cofactor");
 end
 // synthesis translate_on
endmodule
'''
 # Existing public motion_fifo stays byte-for-byte as the first module.
 (out/'motion_fifo.v').write_bytes((fifo+extra).encode())
 s=(R/'pl_motion/rtl/motion_executor.v').read_text()
 s=replace(s,'output wire [2:0] home_fault','output wire [2:0] home_fault,output wire plan_available')
 s=replace(s,'assign plan_ready=(state==IDLE || boundary) && !(|disabling) && !(|fault_latched) && !safety && !own;',
  'assign plan_available=(state==IDLE || boundary) && !(|disabling) && !(|fault_latched) && !own;\n    assign plan_ready=plan_available && !safety;')
 (out/'motion_executor.v').write_bytes(s.encode())
 s=(R/'pl_motion/rtl/motion_planner.v').read_text()
 s=replace(s,'output wire [1196:0] plan_data,output reg error','output wire [1196:0] plan_data,output reg error,output wire plan_pending')
 s=replace(s,'assign plan_valid=state==HOLD && !cancel;','assign plan_pending=state==HOLD;\nassign plan_valid=plan_pending && !cancel;')
 (out/'motion_planner.v').write_bytes(s.encode())
 s=(out/'continuous_motion.v').read_text()
 s=replace(s,'wire planner_ready,planner_busy,planner_valid,planner_error,executor_error;',
  'wire planner_ready,planner_busy,planner_valid,planner_pending,planner_error,executor_error;\n wire prepared_available,executor_available;')
 s=replace(s,'.plan_ready(prepared_push_ready),.plan_data(planner_data),.error(planner_error));',
  '.plan_ready(prepared_push_ready),.plan_data(planner_data),.error(planner_error),.plan_pending(planner_pending));')
 s=replace(s,'motion_fifo #(.WIDTH(1197),.DEPTH(PLAN_DEPTH)) plan_fifo(', 'motion_plan_fifo #(.WIDTH(1197),.DEPTH(PLAN_DEPTH)) plan_fifo(')
 s=replace(s,'.flush(flush_all),.in_valid(planner_valid),.in_ready(prepared_push_ready)',
  '.flush(flush_all),.in_valid(planner_pending),.in_ready(prepared_push_ready)')
 s=replace(s,'.out_data(prepared_data),.level(prepared_level));',
  '.out_data(prepared_data),.level(prepared_level),.storage_out_ready(prepared_storage_ready),.storage_valid(prepared_available));')
 s=replace(s,'assign prepared_pop=launch && executor_ready;', '''assign prepared_pop=launch && executor_ready;
 // Exact !flush cofactor of prepared_pop, using only registered ownership,
 // plan data and the executor's safety-independent availability. Public
 // prepared_pop still fences every stop/error on the original edge.
 wire prepared_request_storage=((start_req && !running && !paused &&
   (buffered_points>=START_MIN_POINTS || end_seen)) || (resume_req && paused)) && gates_ok && pulse_safe;
 wire prepared_storage_ready=!own && prepared_available && session_valid && prepared_session==session_id &&
  executor_available && (prepared_request_storage || (at_boundary && !active_end && !want_pause));''')
 s=replace(s,'.plan_valid(launch),.plan_ready(executor_ready),.plan_data(prepared_data),',
  '.plan_valid(launch),.plan_ready(executor_ready),.plan_available(executor_available),.plan_data(prepared_data),')
 # planning_base is private to an owned session; OPEN initializes it, and
 # cancellation invalidates the owner before it can be read by a new request.
 s=replace(s,'planning_base<=0;','') if s.count('planning_base<=0;')==1 else s.replace('planning_base<=0;','')
 s=replace(s,'planning_base<=position;','')
 s=replace(s,'if(planner_valid && prepared_push_ready)planning_base<=planner_data[940:685];','')
 extra='''
always @(posedge clk)begin
 if(open_req && !cancel_now && !finish_now && maintenance_ok && !(|fault_latched) &&
   open_session_id!=0 && open_session_id!=session_id && !rebase_req && !enable_req && !start_req && !resume_req)
  planning_base<=position;
 if(planner_pending && (prepared_level<PLAN_DEPTH || prepared_storage_ready))
  planning_base<=planner_data[940:685];
end
// synthesis translate_off
always @(posedge clk)if(rst_n && !flush_all)
 if(prepared_storage_ready !== prepared_pop)$fatal(1,"private prepared-pop cofactor mismatch");
// synthesis translate_on
'''
 (out/'continuous_motion.v').write_bytes(s.replace('endmodule',extra+'endmodule').encode())
 (out/'local_flush_notes.json').write_text(json.dumps({'hashes_computed':False,'external_cycles_added':0,
  'internal_change':'Physical prepared queue invalidation basis follows a registered flush marker; same-edge logical validity/level stays unchanged',
  'spare':'logical prepared depth8 unchanged, physical9 addresses avoid valid same-address read/write',
  'private_data_reset_removed':256,'pending_validation':True},indent=2)+'\n')
 print('Prepared isolated RTL30 local prepared-FIFO cleanup; product remains29')
if __name__=='__main__':main()
