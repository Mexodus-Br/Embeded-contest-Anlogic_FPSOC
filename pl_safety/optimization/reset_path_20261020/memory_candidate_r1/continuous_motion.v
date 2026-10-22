`timescale 1ns/1ps
// Logical record interface only: no wire packet/CRC/register map is implied.
module continuous_motion #(
 parameter FIFO_DEPTH=4,PLAN_DEPTH=2,START_MIN_POINTS=2,
 parameter [255:0] STEP_HIGH_CYCLES=0,STEP_LOW_CYCLES=0,
 parameter [255:0] DIR_SETUP_CYCLES=0,DIR_HOLD_CYCLES=0,
 parameter [255:0] EN_SETUP_CYCLES=0,EN_DISABLE_CYCLES=0,MAX_STEP_HZ=0,
 parameter [3:0] EN_ACTIVE_LEVEL=15,parameter HOME_SUPPORT=0
)(
 input wire clk,rst_n,
 input wire rebase_req,input wire [3:0] rebase_mask,input wire [255:0] rebase_position,
 input wire enable_req,input wire [3:0] enable_mask,
 input wire disable_req,input wire [3:0] disable_mask,
 input wire open_req,input wire [63:0] open_session_id,
 input wire start_req,pause_req,resume_req,stop_req,clear_fault,input wire [3:0] fault,
 input wire point_valid,output wire point_ready,
 input wire [63:0] point_session,duration_tick,input wire [31:0] point_sequence,
 input wire point_end,input wire [3:0] point_mask,input wire [255:0] point_target,
 output wire [3:0] step,dir,en,position_valid,fault_latched,config_valid,
 output wire [255:0] position,
 output reg session_valid,output reg [63:0] session_id,
 output reg running,paused,output wire busy,start_ready,resume_ready,
 output wire [31:0] fifo_level,prepared_level,output reg [31:0] buffered_points,
 output reg accepted,stale,rejected,cancelled,underflow_event,session_done,
 output wire point_start,point_done,stopped,
 output reg [31:0] active_sequence,done_sequence,
 output wire [3:0] pulse_event,output wire slot_event,output wire [63:0] slot_id,
 input wire home_owner,home_enable,home_reference,home_complete,
 input wire [2:0] home_run,home_direction,input wire [191:0] home_period,home_reference_position,
 input wire [3:0] safety_invalidate,output wire safety_pulse_safe,
 output wire [2:0] home_fault
);
 wire own=HOME_SUPPORT ? home_owner : 1'b0;
 wire raw_ready,raw_valid,raw_pop;
 wire [420:0] raw_data;
 wire prepared_valid,prepared_push_ready,prepared_pop;
 wire [1196:0] prepared_data,planner_data;
 wire planner_ready,planner_busy,planner_valid,planner_pending,planner_error,executor_error;
 wire executor_ready,executor_busy,boundary,pulse_safe;
 assign safety_pulse_safe=pulse_safe;
 wire [3:0] enabled,enable_ready;
 reg [255:0] planning_base;
 reg [32:0] next_sequence;
 reg end_seen,pause_pending,active_end;
 wire old_record=!session_valid || point_session!=session_id;
 wire invalid_order=!old_record && (end_seen || {1'b0,point_sequence}!=next_sequence);
 // Invalid current-session metadata is always ready for an error handshake.
 // Do not feed the FIFO-derived ready path back into its own cancel/flush.
 wire bad_ingress=rst_n && point_valid && invalid_order;
 wire at_boundary=running && boundary;
 wire want_pause=pause_pending || pause_req;
 // Read registered occupancy here: out_valid is gated by flush, so deriving
 // flush/underflow from out_valid would create a combinational feedback loop.
 wire missing_next=at_boundary && !active_end && !want_pause && prepared_level==0;
 wire protocol_error=planner_error || executor_error || bad_ingress;
 wire cancel_now=stop_req || disable_req || (|fault) || protocol_error || missing_next;
 wire finish_now=at_boundary && active_end && !cancel_now;
 wire flush_all=cancel_now || finish_now;
 assign point_ready=rst_n && (old_record || invalid_order || (raw_ready && !cancel_now));
 wire raw_push=point_valid && !old_record && !invalid_order && !cancel_now;
 wire ingress=raw_push && raw_ready;
 motion_fifo #(.WIDTH(421),.DEPTH(FIFO_DEPTH),.SPARE_SLOT(1)) raw_fifo(
  .clk(clk),.rst_n(rst_n),.flush(flush_all),.in_valid(raw_push),.in_ready(raw_ready),
  .in_data({point_target,duration_tick,point_session,point_sequence,point_end,point_mask}),
  .out_valid(raw_valid),.out_ready(raw_pop),.out_data(raw_data),.level(fifo_level));
 wire [255:0] raw_target;wire [63:0] raw_duration,raw_session;
 wire [31:0] raw_sequence;wire raw_end;wire [3:0] raw_mask;
 assign {raw_target,raw_duration,raw_session,raw_sequence,raw_end,raw_mask}=raw_data;
 assign raw_pop=planner_ready && session_valid && !flush_all;
 motion_planner #(.STEP_HIGH_CYCLES(STEP_HIGH_CYCLES),.STEP_LOW_CYCLES(STEP_LOW_CYCLES),
  .DIR_SETUP_CYCLES(DIR_SETUP_CYCLES),.DIR_HOLD_CYCLES(DIR_HOLD_CYCLES),
  .EN_SETUP_CYCLES(EN_SETUP_CYCLES),.MAX_STEP_HZ(MAX_STEP_HZ)) planner(
  .clk(clk),.rst_n(rst_n),.cancel(flush_all),.req_valid(raw_valid && session_valid && !flush_all),
  .req_ready(planner_ready),.busy(planner_busy),.base_position(planning_base),.target_position(raw_target),
  .axis_mask(raw_mask),.duration_tick(raw_duration),.request_session(raw_session),
  .request_sequence(raw_sequence),.request_end(raw_end),.plan_valid(planner_valid),
  .plan_ready(prepared_push_ready),.plan_data(planner_data),.error(planner_error),.plan_pending(planner_pending));
 motion_fifo #(.WIDTH(1197),.DEPTH(PLAN_DEPTH),.SPECULATIVE_STORAGE(1)) plan_fifo(
  .clk(clk),.rst_n(rst_n),.flush(flush_all),.in_valid(planner_pending),.in_ready(prepared_push_ready),
  .in_data(planner_data),.out_valid(prepared_valid),.out_ready(prepared_pop),
  .out_data(prepared_data),.level(prepared_level));
 wire [3:0] prepared_mask=prepared_data[3:0];
 wire [63:0] prepared_session=prepared_data[100:37];
 wire gates_ok=(prepared_mask & ~(enable_ready & position_valid & config_valid))==0;
 assign start_ready=session_valid && !running && !paused && prepared_valid &&
  (buffered_points>=START_MIN_POINTS || end_seen) && gates_ok && pulse_safe && executor_ready && !cancel_now;
 assign resume_ready=session_valid && paused && prepared_valid && gates_ok && pulse_safe && executor_ready && !cancel_now;
 wire request_launch=(start_req && start_ready) || (resume_req && resume_ready);
 wire boundary_launch=at_boundary && !active_end && !want_pause && prepared_valid;
 wire launch=!own && (request_launch || boundary_launch) && session_valid && prepared_session==session_id && !cancel_now;
 assign prepared_pop=launch && executor_ready;
 wire maintenance_ok=!session_valid && !running && !paused && buffered_points==0 &&
  !planner_busy && prepared_level==0 && fifo_level==0 && !executor_busy;
 assign busy=running || paused || buffered_points!=0 || planner_busy || executor_busy;
 motion_executor #(.STEP_HIGH_CYCLES(STEP_HIGH_CYCLES),.STEP_LOW_CYCLES(STEP_LOW_CYCLES),
  .DIR_SETUP_CYCLES(DIR_SETUP_CYCLES),.DIR_HOLD_CYCLES(DIR_HOLD_CYCLES),
  .EN_SETUP_CYCLES(EN_SETUP_CYCLES),.EN_DISABLE_CYCLES(EN_DISABLE_CYCLES),
  .MAX_STEP_HZ(MAX_STEP_HZ),.EN_ACTIVE_LEVEL(EN_ACTIVE_LEVEL),.HOME_SUPPORT(HOME_SUPPORT)) executor(
  .clk(clk),.rst_n(rst_n),.rebase_req(rebase_req && maintenance_ok),.rebase_mask(rebase_mask),
  .rebase_position(rebase_position),.enable_req(enable_req && maintenance_ok),.enable_mask(enable_mask),
  .disable_req(disable_req),.disable_mask(disable_mask),
  .stop_req(stop_req || (cancel_now && session_valid)),.fault(fault),.clear_fault(clear_fault),
  .plan_valid(launch),.plan_ready(executor_ready),.plan_data(prepared_data),
  .step(step),.dir(dir),.en(en),.position(position),.position_valid(position_valid),
  .fault_latched(fault_latched),.config_valid(config_valid),.enabled_state(enabled),.enable_ready_state(enable_ready),
  .busy(executor_busy),.boundary(boundary),.pulse_safe(pulse_safe),.point_start(point_start),
  .done(point_done),.stopped(stopped),.plan_rejected(executor_error),.rebase_accepted(),
  .pulse_event(pulse_event),.slot_event(slot_event),.slot_id(slot_id),.home_owner(home_owner),.home_enable(home_enable),
  .home_reference(home_reference),.home_complete(home_complete),.home_run(home_run),
  .home_direction(home_direction),.home_period(home_period),.home_reference_position(home_reference_position),
  .safety_invalidate(safety_invalidate),.home_fault(home_fault));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   session_valid<=0;session_id<=0;running<=0;paused<=0;planning_base<=0;
   next_sequence<=0;end_seen<=0;pause_pending<=0;active_end<=0;buffered_points<=0;
   accepted<=0;stale<=0;rejected<=0;cancelled<=0;underflow_event<=0;session_done<=0;
   active_sequence<=0;done_sequence<=0;
  end else begin
   accepted<=0;stale<=0;rejected<=0;cancelled<=0;underflow_event<=0;session_done<=0;
   if(point_valid && point_ready && old_record)stale<=1;
   if(cancel_now)begin
    if(session_valid)cancelled<=1;
    if(missing_next)underflow_event<=1;
    if(protocol_error)rejected<=1;
    session_valid<=0;running<=0;paused<=0;end_seen<=0;pause_pending<=0;
    buffered_points<=0;planning_base<=0;next_sequence<=0;
   end else if(finish_now)begin
    session_done<=1;session_valid<=0;running<=0;paused<=0;end_seen<=0;pause_pending<=0;
    buffered_points<=0;planning_base<=0;next_sequence<=0;done_sequence<=active_sequence;
   end else begin
    if((rebase_req || enable_req) && !maintenance_ok)rejected<=1;
    if(open_req)begin
     if(maintenance_ok && !(|fault_latched) && open_session_id!=0 && open_session_id!=session_id &&
        !rebase_req && !enable_req && !start_req && !resume_req)begin
      session_id<=open_session_id;session_valid<=1;planning_base<=position;
      next_sequence<=0;end_seen<=0;buffered_points<=0;
     end else rejected<=1;
    end
    if(ingress)begin accepted<=1;next_sequence<=next_sequence+33'd1;if(point_end)end_seen<=1;end
    case({ingress,prepared_pop})
     2'b10:buffered_points<=buffered_points+1'b1;
     2'b01:buffered_points<=buffered_points-1'b1;
     default:begin end
    endcase
    if(planner_valid && prepared_push_ready)planning_base<=planner_data[940:685];
    if(pause_req && running)pause_pending<=1;
    else if(pause_req && !running)rejected<=1;
    if(at_boundary)begin
     done_sequence<=active_sequence;
     if(want_pause)begin running<=0;paused<=1;pause_pending<=0;end
    end
    if(prepared_pop)begin
     running<=1;paused<=0;pause_pending<=0;active_sequence<=prepared_data[36:5];active_end<=prepared_data[4];
    end
    if(start_req && !start_ready)rejected<=1;
    if(resume_req && !resume_ready)rejected<=1;
   end
  end
 end
 // synthesis translate_off
 initial if(FIFO_DEPTH<2 || PLAN_DEPTH<2 || START_MIN_POINTS<1 ||
  START_MIN_POINTS>FIFO_DEPTH+PLAN_DEPTH+1)$fatal(1,"invalid continuous cache parameters");
 // synthesis translate_on
endmodule
