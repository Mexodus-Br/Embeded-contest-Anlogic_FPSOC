`timescale 1ns/1ps
`include "generated/interface_defs.vh"
// Independent GP motion profile. All state and the kernel share clk_100m.
module motion_service #(
 parameter FIFO_DEPTH=`PLI_MOTION_GP_MOTION_V1_RAW_DEPTH,PLAN_DEPTH=`PLI_MOTION_GP_MOTION_V1_PLAN_DEPTH,
 parameter START_MIN_POINTS=`PLI_MOTION_GP_MOTION_V1_START_MIN_POINTS,
 parameter [255:0] STEP_HIGH_CYCLES=0,STEP_LOW_CYCLES=0,DIR_SETUP_CYCLES=0,DIR_HOLD_CYCLES=0,
 parameter [255:0] EN_SETUP_CYCLES=0,EN_DISABLE_CYCLES=0,MAX_STEP_HZ=0,
 parameter [3:0] EN_ACTIVE_LEVEL=15,parameter HOME_SUPPORT=0
)(
 input wire clk,rst_n,dma_reset_released,dma_error,input wire [3:0] fault,
 input wire [32:0] s_awaddr,s_araddr,input wire [31:0] s_wdata,input wire [3:0] s_wstrb,
 input wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready,
 output wire s_awready,s_wready,s_arready,output reg s_bvalid,s_rvalid,
 output reg [1:0] s_bresp,s_rresp,output reg [31:0] s_rdata,
 input wire [63:0] stream_data,input wire [7:0] stream_keep,input wire stream_last,stream_valid,
 output wire stream_ready,irq,
 output wire [3:0] step,dir,en,position_valid,output wire [255:0] position,
 output wire [255:0] pulses,output wire running,paused,core_busy,session_valid,
 output wire [63:0] session_id,output wire [31:0] fifo_level,prepared_level,buffered_points,
 output wire point_start,point_done,stopped,output wire [3:0] pulse_event,
 output wire slot_event,output wire [63:0] slot_id,
 input wire safety_inhibit,safety_stop,safety_disable,safety_clear,
 input wire home_owner,home_enable,home_reference,home_complete,
 input wire [2:0] home_run,home_direction,input wire [191:0] home_period,home_reference_position,
 input wire [3:0] safety_invalidate,
 output wire safety_pulse_safe,safety_idle,safety_abort,output wire [2:0] home_fault,
 output wire [3:0] safety_config_valid,safety_fault_latched
);
 wire normal_ok=HOME_SUPPORT ? !safety_inhibit : 1'b1;
 wire private_stop=HOME_SUPPORT ? safety_stop : 1'b0;
 wire private_disable=HOME_SUPPORT ? safety_disable : 1'b0;
 wire private_clear=HOME_SUPPORT ? safety_clear : 1'b0;
 localparam [32:0] BASE={1'b0,`PLI_MOTION_GP_MOTION_V1_BASE};
 reg ah,wh,aw_hit,stop_address,stop_data;reg [11:0] offset;reg [31:0] wd;reg [3:0] ws;
 wire write_fire=ah && wh && !s_bvalid;
 assign s_awready=rst_n && !ah && !s_bvalid;assign s_wready=rst_n && !wh && !s_bvalid;
 assign s_arready=rst_n && !s_rvalid;
 reg [255:0] pulse_counter;
 genvar g;generate for(g=0;g<4;g=g+1)begin: totals
 assign pulses[g*64+:64]=pulse_counter[g*64+:64]==64'hffffffffffffffff ? 64'hffffffffffffffff : pulse_counter[g*64+:64]+pulse_event[g];
 end endgenerate
 reg [31:0] snapshot[0:63];reg [31:0] snap_id;reg snap_valid;
 integer integer_word,axis_word;
 reg [31:0] opcode,arg,txn,maintenance,recover_gen;
 reg [63:0] session_shadow;reg [255:0] rebase_shadow;
 reg [31:0] ack_id,ack_error,last_id;reg ack_valid,ack_accepted,ack_completed,command_busy;
 reg [31:0] captured_opcode,captured_arg,captured_id,captured_generation;
 reg [63:0] captured_session;reg [255:0] captured_rebase;reg captured_maintenance;
 reg [447:0] last_payload;wire [447:0] shadow_payload={opcode,arg,session_shadow,rebase_shadow,maintenance,recover_gen};
 reg execute,dispatch_pending;
 reg req_open,req_enable,req_start,req_pause,req_resume,req_disable,req_rebase,req_clear;
 reg [31:0] pending,mask,error_code;
 reg link_ready;reg [31:0] link_generation,software_generation;reg stop_complete;
 reg [1:0] primary_release;
 // This reset only qualifies new transport ownership; never resets position.
 always @(posedge clk or negedge rst_n)if(!rst_n)primary_release<=0;
 else if(!dma_reset_released)primary_release<=0;else primary_release<={primary_release[0],1'b1};
 wire reset_ok=dma_reset_released && primary_release[1];
 wire start_ready,resume_ready,accepted,stale,rejected,cancelled,underflow,session_done;
 wire [3:0] fault_latched,config_valid;
 assign safety_config_valid=config_valid;assign safety_fault_latched=fault_latched;
 wire [31:0] active_sequence,done_sequence;
 reg [31:0] accepted_sequence;reg accepted_valid,done_valid,user_cancel;reg [31:0] ingress_sequence;
 reg [31:0] accept_count,done_count,stale_count,reject_count,cancel_count,stop_count,end_count;
 reg [32:0] observed_sequence;reg observed_end;
 wire rx_error,rx_error_candidate,rx_arm_ready,packet_busy,partial_empty,packet_closed;
 wire [31:0] packet_count;
 wire [63:0] rx_session,rx_duration;wire [31:0] rx_sequence;wire rx_end,rx_valid,rx_ready;
 wire [3:0] rx_mask;wire [255:0] rx_target;
 wire [3:0] enabled=en ^ ~EN_ACTIVE_LEVEL;
 wire maintenance_ok=!core_busy && !session_valid && partial_empty;
 wire cmd_open=execute && captured_opcode==`PLI_CMD_OPEN_SESSION;
 wire cmd_enable=execute && captured_opcode==`PLI_CMD_ENABLE;
 wire cmd_start=execute && captured_opcode==`PLI_CMD_START;
 wire cmd_pause=execute && captured_opcode==`PLI_CMD_PAUSE;
 wire cmd_resume=execute && captured_opcode==`PLI_CMD_RESUME;
 wire cmd_disable=execute && captured_opcode==`PLI_CMD_DISABLE;
 wire cmd_rebase=execute && captured_opcode==`PLI_CMD_REBASE;
 wire cmd_clear=execute && captured_opcode==`PLI_CMD_CLEAR_FAULT;
 wire cmd_recover=execute && captured_opcode==`PLI_CMD_LINK_RECOVER;
 reg command_ok;
 always @*begin
  command_ok=0;
  case(captured_opcode)
   `PLI_CMD_OPEN_SESSION:command_ok=maintenance_ok && link_ready && !(|fault_latched) && captured_session!=0 && captured_session!=session_id;
   `PLI_CMD_ENABLE:command_ok=maintenance_ok && captured_arg>0 && captured_arg<=15 && (captured_arg[3:0] & ~(config_valid & position_valid))==0 && !(|fault_latched);
   `PLI_CMD_START:command_ok=start_ready;
   `PLI_CMD_PAUSE:command_ok=running;
   `PLI_CMD_RESUME:command_ok=resume_ready;
   `PLI_CMD_DISABLE:command_ok=captured_arg>0 && captured_arg<=15;
   `PLI_CMD_REBASE:command_ok=maintenance_ok && captured_maintenance && captured_arg>0 && captured_arg<=15 && !(|(enabled & captured_arg[3:0])) && !(|fault_latched);
   `PLI_CMD_CLEAR_FAULT:command_ok=!core_busy && !(|fault) && !dma_error;
   `PLI_CMD_LINK_RECOVER:command_ok=maintenance_ok && !link_ready && reset_ok && !(|fault) && !dma_error && captured_generation>software_generation;
   `PLI_CMD_NOP:command_ok=1;
   default:command_ok=0;
  endcase
 end
 wire guarded_command_ok=command_ok && (!HOME_SUPPORT ||
  (captured_opcode!=`PLI_CMD_REBASE &&
   (normal_ok || captured_opcode==`PLI_CMD_NOP || captured_opcode==`PLI_CMD_DISABLE ||
    captured_opcode==`PLI_CMD_CLEAR_FAULT || captured_opcode==`PLI_CMD_LINK_RECOVER)));
 reg [1:0] write_response;
 always @*begin
  write_response=0;
  if(!aw_hit)write_response=3;
  else if(offset[1:0]!=0 || ws!=15)write_response=2;
  else case(offset)
   `PLI_MOTION_GP_MOTION_V1_REG_OPCODE,`PLI_MOTION_GP_MOTION_V1_REG_ARG,`PLI_MOTION_GP_MOTION_V1_REG_TXN,
   `PLI_MOTION_GP_MOTION_V1_REG_SESSION_LO,`PLI_MOTION_GP_MOTION_V1_REG_SESSION_HI,`PLI_MOTION_GP_MOTION_V1_REG_RECOVER_GEN:begin end
   `PLI_MOTION_GP_MOTION_V1_REG_MAINT:if(wd>1)write_response=2;
   `PLI_MOTION_GP_MOTION_V1_REG_STOP:if(wd!=1)write_response=2;
   `PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM:if(!rx_arm_ready || !session_valid || wd==0 || wd>`PLI_MOTION_GP_MOTION_V1_MAX_PACKET_RECORDS)write_response=2;
   `PLI_MOTION_GP_MOTION_V1_REG_SUBMIT:if(wd!=1 || command_busy || txn==0 || txn<last_id || (txn==last_id && shadow_payload!=last_payload))write_response=2;
   `PLI_MOTION_GP_MOTION_V1_REG_SNAP_REQ:if(wd==0 || wd<snap_id)write_response=2;
   `PLI_MOTION_GP_MOTION_V1_REG_IRQ_MASK,`PLI_MOTION_GP_MOTION_V1_REG_IRQ_PENDING:if(wd & ~`PLI_MOTION_GP_MOTION_V1_IRQ_ALL_MASK)write_response=2;
   default:if(offset<`PLI_MOTION_GP_MOTION_V1_REG_REBASE_0 || offset>`PLI_MOTION_GP_MOTION_V1_REG_REBASE_7)write_response=2;
  endcase
 end
 wire good_write=write_fire && write_response==0;
 // STOP decode must not pass through the general response mux: ARM ready
 // itself observes abort, so sharing that mux creates a structural loop.
 wire stop_write=write_fire && stop_address && stop_data;
 assign safety_idle=maintenance_ok && !command_busy && !ah && !wh && !packet_busy;
 // RX error already stops the normal kernel on its detecting edge. Register
 // only its notification to HOME to avoid error -> abort -> error feedback.
 reg safety_rx_error;
 always @(posedge clk or negedge rst_n)if(!rst_n)safety_rx_error<=0;else safety_rx_error<=rx_error;
 assign safety_abort=stop_write || req_disable || dma_error || !reset_ok || safety_rx_error || (|fault);
 wire arm_write=good_write && offset==`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM;
 wire external_cancel=private_stop || private_disable || (HOME_SUPPORT && home_enable) || stop_write || (|fault) || dma_error || !reset_ok || req_disable;
 wire cancel_transport=external_cancel || rx_error || cancelled || session_done;
 // Held reset/fault sources must suppress execution without repeatedly
 // manufacturing idle STOP completions after the first safe drain.
 reg safety_stop_seen;
 always @(posedge clk or negedge rst_n)if(!rst_n)safety_stop_seen<=0;else safety_stop_seen<=private_stop;
 // Shannon expansion on DMA error removes its serial trip through the
 // receiver abort mask before the same-edge execution STOP qualification.
 // When DMA error is 1, receiver.error is necessarily 0; otherwise the
 // private raw predicate receives exactly the original non-DMA abort mask.
 wire occupied=core_busy || session_valid;
 wire non_dma_abort=private_stop || private_disable || (HOME_SUPPORT && home_enable) || stop_write || (|fault) || !reset_ok || req_disable || cancelled || session_done;
 wire rx_without_dma=rst_n && !non_dma_abort && rx_error_candidate;
 wire stop_kernel=(private_stop && !safety_stop_seen && occupied) || stop_write ||
  ((|fault || !reset_ok || req_disable) && occupied) ||
  (dma_error ? occupied : rx_without_dma);
 wire sequence_violation=rx_valid && rx_ready && session_valid && rx_session==session_id &&
  (observed_end || {1'b0,rx_sequence}!=observed_sequence);
 motion_stream_rx receiver(.clk(clk),.rst_n(rst_n),.abort(external_cancel || cancelled || session_done),.link_ready(link_ready),
  .arm(arm_write),.arm_count(wd),.arm_ready(rx_arm_ready),.packet_busy(packet_busy),.partial_empty(partial_empty),
  .s_data(stream_data),.s_keep(stream_keep),.s_last(stream_last),.s_valid(stream_valid),.s_ready(stream_ready),
  .point_valid(rx_valid),.point_ready(rx_ready),.point_session(rx_session),.duration_tick(rx_duration),
  .point_sequence(rx_sequence),.point_end(rx_end),.point_mask(rx_mask),.point_target(rx_target),
  .error(rx_error),.error_candidate(rx_error_candidate),.packet_closed(packet_closed),.packet_count(packet_count));
 continuous_motion #(.FIFO_DEPTH(FIFO_DEPTH),.PLAN_DEPTH(PLAN_DEPTH),.START_MIN_POINTS(START_MIN_POINTS),
  .STEP_HIGH_CYCLES(STEP_HIGH_CYCLES),.STEP_LOW_CYCLES(STEP_LOW_CYCLES),.DIR_SETUP_CYCLES(DIR_SETUP_CYCLES),
  .DIR_HOLD_CYCLES(DIR_HOLD_CYCLES),.EN_SETUP_CYCLES(EN_SETUP_CYCLES),.EN_DISABLE_CYCLES(EN_DISABLE_CYCLES),
  .MAX_STEP_HZ(MAX_STEP_HZ),.EN_ACTIVE_LEVEL(EN_ACTIVE_LEVEL),.HOME_SUPPORT(HOME_SUPPORT)) kernel(
  .clk(clk),.rst_n(rst_n),.rebase_req(req_rebase && !HOME_SUPPORT),.rebase_mask(captured_arg[3:0]),.rebase_position(captured_rebase),
  .enable_req(req_enable && normal_ok),.enable_mask(captured_arg[3:0]),.disable_req(req_disable || private_disable),.disable_mask(private_disable ? 4'b0111 : captured_arg[3:0]),
  .open_req(req_open && normal_ok),.open_session_id(captured_session),.start_req(req_start && normal_ok),
  .pause_req(req_pause),.resume_req(req_resume && normal_ok),.stop_req(stop_kernel),.clear_fault(req_clear || private_clear),.fault(fault | {4{dma_error}}),
  .point_valid(rx_valid),.point_ready(rx_ready),.point_session(rx_session),.duration_tick(rx_duration),.point_sequence(rx_sequence),
  .point_end(rx_end),.point_mask(rx_mask),.point_target(rx_target),.step(step),.dir(dir),.en(en),.position_valid(position_valid),
  .fault_latched(fault_latched),.config_valid(config_valid),.position(position),.session_valid(session_valid),.session_id(session_id),
  .running(running),.paused(paused),.busy(core_busy),.start_ready(start_ready),.resume_ready(resume_ready),
  .fifo_level(fifo_level),.prepared_level(prepared_level),.buffered_points(buffered_points),.accepted(accepted),.stale(stale),
  .rejected(rejected),.cancelled(cancelled),.underflow_event(underflow),.session_done(session_done),
  .point_start(point_start),.point_done(point_done),.stopped(stopped),.active_sequence(active_sequence),.done_sequence(done_sequence),
  .pulse_event(pulse_event),.slot_event(slot_event),.slot_id(slot_id),.home_owner(home_owner),.home_enable(home_enable),
  .home_reference(home_reference),.home_complete(home_complete),.home_run(home_run),
  .home_direction(home_direction),.home_period(home_period),.home_reference_position(home_reference_position),
  .safety_invalidate(safety_invalidate),.safety_pulse_safe(safety_pulse_safe),.home_fault(home_fault));
 wire [31:0] status=(core_busy ? `PLI_MOTION_GP_MOTION_V1_STATUS_BITS_BUSY_MASK:0) |
  (session_valid ? `PLI_MOTION_GP_MOTION_V1_STATUS_BITS_SESSION_MASK:0) |
  (running ? `PLI_MOTION_GP_MOTION_V1_STATUS_BITS_RUNNING_MASK:0) |
  (paused ? `PLI_MOTION_GP_MOTION_V1_STATUS_BITS_PAUSED_MASK:0) |
  (start_ready ? `PLI_MOTION_GP_MOTION_V1_STATUS_BITS_START_READY_MASK:0) |
  (resume_ready ? `PLI_MOTION_GP_MOTION_V1_STATUS_BITS_RESUME_READY_MASK:0) |
  (stop_complete ? `PLI_MOTION_GP_MOTION_V1_STATUS_BITS_STOP_COMPLETE_MASK:0) |
  (link_ready ? `PLI_MOTION_GP_MOTION_V1_STATUS_BITS_LINK_READY_MASK:0) |
  (packet_busy ? `PLI_MOTION_GP_MOTION_V1_STATUS_BITS_PACKET_BUSY_MASK:0) |
  ((&config_valid) ? `PLI_MOTION_GP_MOTION_V1_STATUS_BITS_CONFIG_VALID_MASK:0);
 reg [63:0] timestamp;reg [6:0] tick_div;
 reg [31:0] snap_live[0:63];integer i;
 always @*begin
  for(integer_word=0;integer_word<64;integer_word=integer_word+1)snap_live[integer_word]=0;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_STATUS]=status;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_ERROR]=error_code;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_TIME_LO]=timestamp[31:0];snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_TIME_HI]=timestamp[63:32];
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_SESSION_LO]=session_id[31:0];snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_SESSION_HI]=session_id[63:32];
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_LINK_GEN]=link_generation;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_ACCEPT_SEQ]=accepted_sequence;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_DONE_SEQ]=done_sequence;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_ACTIVE_SEQ]=active_sequence;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_VALIDITY]={21'd0,running,done_valid,accepted_valid,config_valid,position_valid};
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_BUFFERED]=buffered_points;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_FIFO]=fifo_level;snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_PLAN]=prepared_level;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_SIGNALS]={20'd0,en,dir,step};
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_PACKET_COUNT]=packet_count;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_ACTIVE_VALID]={31'd0,running};
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_ACCEPT_COUNT]=accept_count;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_DONE_COUNT]=done_count;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_STALE_COUNT]=stale_count;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_REJECT_COUNT]=reject_count;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_CANCEL_COUNT]=cancel_count;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_STOP_COUNT]=stop_count;
  snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_END_COUNT]=end_count;
  for(axis_word=0;axis_word<4;axis_word=axis_word+1)begin
   snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_AXES_FIRST+axis_word*4]=position[axis_word*64+:32];
   snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_AXES_FIRST+axis_word*4+1]=position[axis_word*64+32+:32];
   snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_AXES_FIRST+axis_word*4+2]=pulses[axis_word*64+:32];
   snap_live[`PLI_MOTION_GP_MOTION_V1_SNAP_WORD_AXES_FIRST+axis_word*4+3]=pulses[axis_word*64+32+:32];
  end
 end
 reg [31:0] read_data;reg read_known;
 always @*begin
  read_data=0;read_known=1;
  case(s_araddr[11:0])
   `PLI_MOTION_GP_MOTION_V1_REG_VERSION:read_data=`PLI_MOTION_GP_MOTION_V1_VERSION;
   `PLI_MOTION_GP_MOTION_V1_REG_PROFILE:read_data=`PLI_MOTION_GP_MOTION_V1_PROFILE_ID;
   `PLI_MOTION_GP_MOTION_V1_REG_STATUS:read_data=status;
   `PLI_MOTION_GP_MOTION_V1_REG_ERROR:read_data=error_code;
   `PLI_MOTION_GP_MOTION_V1_REG_OPCODE:read_data=opcode;
   `PLI_MOTION_GP_MOTION_V1_REG_ARG:read_data=arg;
   `PLI_MOTION_GP_MOTION_V1_REG_TXN:read_data=txn;
   `PLI_MOTION_GP_MOTION_V1_REG_SESSION_LO:read_data=session_shadow[31:0];
   `PLI_MOTION_GP_MOTION_V1_REG_SESSION_HI:read_data=session_shadow[63:32];
   `PLI_MOTION_GP_MOTION_V1_REG_MAINT:read_data=maintenance;
   `PLI_MOTION_GP_MOTION_V1_REG_RECOVER_GEN:read_data=recover_gen;
   `PLI_MOTION_GP_MOTION_V1_REG_ACK_ID:read_data=ack_id;
   `PLI_MOTION_GP_MOTION_V1_REG_ACK_ERROR:read_data=ack_error;
   `PLI_MOTION_GP_MOTION_V1_REG_ACK_STATUS:read_data={28'd0,command_busy,ack_completed,ack_accepted,ack_valid};
   `PLI_MOTION_GP_MOTION_V1_REG_SNAP_ID:read_data=snap_id;
   `PLI_MOTION_GP_MOTION_V1_REG_SNAP_VALID:read_data={31'd0,snap_valid};
   `PLI_MOTION_GP_MOTION_V1_REG_IRQ_PENDING:read_data=pending;
   `PLI_MOTION_GP_MOTION_V1_REG_IRQ_MASK:read_data=mask;
   `PLI_MOTION_GP_MOTION_V1_REG_FIFO_LEVEL:read_data=fifo_level;
   `PLI_MOTION_GP_MOTION_V1_REG_PLAN_LEVEL:read_data=prepared_level;
   `PLI_MOTION_GP_MOTION_V1_REG_BUFFERED:read_data=buffered_points;
   `PLI_MOTION_GP_MOTION_V1_REG_RAW_CAPACITY:read_data=FIFO_DEPTH;
   `PLI_MOTION_GP_MOTION_V1_REG_PLAN_CAPACITY:read_data=PLAN_DEPTH;
   `PLI_MOTION_GP_MOTION_V1_REG_START_THRESHOLD:read_data=START_MIN_POINTS;
   `PLI_MOTION_GP_MOTION_V1_REG_LINK_GEN:read_data=link_generation;
   `PLI_MOTION_GP_MOTION_V1_REG_LINK_READY:read_data={31'd0,link_ready};
   `PLI_MOTION_GP_MOTION_V1_REG_PACKET_COUNT:read_data=packet_count;
   `PLI_MOTION_GP_MOTION_V1_REG_ACCEPT_SEQ:read_data=accepted_sequence;
   `PLI_MOTION_GP_MOTION_V1_REG_DONE_SEQ:read_data=done_sequence;
   `PLI_MOTION_GP_MOTION_V1_REG_ACTIVE_SEQ:read_data=active_sequence;
   `PLI_MOTION_GP_MOTION_V1_REG_ACCEPT_VALID:read_data={31'd0,accepted_valid};
   `PLI_MOTION_GP_MOTION_V1_REG_DONE_VALID:read_data={31'd0,done_valid};
   `PLI_MOTION_GP_MOTION_V1_REG_ACTIVE_VALID:read_data={31'd0,running};
   `PLI_MOTION_GP_MOTION_V1_REG_ACCEPT_COUNT:read_data=accept_count;
   `PLI_MOTION_GP_MOTION_V1_REG_DONE_COUNT:read_data=done_count;
   `PLI_MOTION_GP_MOTION_V1_REG_STALE_COUNT:read_data=stale_count;
   `PLI_MOTION_GP_MOTION_V1_REG_REJECT_COUNT:read_data=reject_count;
   `PLI_MOTION_GP_MOTION_V1_REG_CANCEL_COUNT:read_data=cancel_count;
   `PLI_MOTION_GP_MOTION_V1_REG_STOP_COUNT:read_data=stop_count;
   `PLI_MOTION_GP_MOTION_V1_REG_END_COUNT:read_data=end_count;
   `PLI_MOTION_GP_MOTION_V1_REG_CAPS:read_data=`PLI_MOTION_GP_MOTION_V1_CAPS;
   `PLI_MOTION_GP_MOTION_V1_REG_FEATURES:read_data=`PLI_MOTION_GP_MOTION_V1_FEATURES;
   default:if(s_araddr[11:0]>=`PLI_MOTION_GP_MOTION_V1_REG_SNAP_0 && s_araddr[11:0]<=`PLI_MOTION_GP_MOTION_V1_REG_SNAP_63)read_data=snapshot[(s_araddr[11:0]-`PLI_MOTION_GP_MOTION_V1_REG_SNAP_0)>>2];
    else if(s_araddr[11:0]>=`PLI_MOTION_GP_MOTION_V1_REG_REBASE_0 && s_araddr[11:0]<=`PLI_MOTION_GP_MOTION_V1_REG_REBASE_7)read_data=rebase_shadow[((s_araddr[11:0]-`PLI_MOTION_GP_MOTION_V1_REG_REBASE_0)>>2)*32+:32];else read_known=0;
  endcase
 end
 wire [31:0] w1c=good_write && offset==`PLI_MOTION_GP_MOTION_V1_REG_IRQ_PENDING ? wd:0;
 wire snapshot_write=good_write && offset==`PLI_MOTION_GP_MOTION_V1_REG_SNAP_REQ && wd!=snap_id;
 reg ack_event;wire [31:0] events=(ack_event ? `PLI_MOTION_GP_MOTION_V1_IRQ_BITS_ACK_MASK:0)|
  (cancelled ? `PLI_MOTION_GP_MOTION_V1_IRQ_BITS_CANCEL_MASK:0)|((point_done || session_done) ? `PLI_MOTION_GP_MOTION_V1_IRQ_BITS_DONE_MASK:0)|
  (accepted ? `PLI_MOTION_GP_MOTION_V1_IRQ_BITS_ACCEPT_MASK:0)|(snapshot_write ? `PLI_MOTION_GP_MOTION_V1_IRQ_BITS_SNAP_MASK:0)|
  ((rx_error || underflow || (|fault_latched)) ? `PLI_MOTION_GP_MOTION_V1_IRQ_BITS_ERROR_MASK:0)|
  (stopped ? `PLI_MOTION_GP_MOTION_V1_IRQ_BITS_STOP_MASK:0);
 assign irq=rst_n && |(pending & mask);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   ah<=0;wh<=0;aw_hit<=0;stop_address<=0;stop_data<=0;offset<=0;wd<=0;ws<=0;s_bvalid<=0;s_bresp<=0;s_rvalid<=0;s_rresp<=0;s_rdata<=0;
   opcode<=0;arg<=0;txn<=0;maintenance<=0;recover_gen<=0;session_shadow<=0;rebase_shadow<=0;
   ack_id<=0;ack_error<=0;last_id<=0;ack_valid<=0;ack_accepted<=0;ack_completed<=0;command_busy<=0;last_payload<=0;
   captured_opcode<=0;captured_arg<=0;captured_id<=0;captured_generation<=0;captured_session<=0;captured_rebase<=0;captured_maintenance<=0;
   execute<=0;dispatch_pending<=0;req_open<=0;req_enable<=0;req_start<=0;req_pause<=0;req_resume<=0;req_disable<=0;req_rebase<=0;req_clear<=0;
   ack_event<=0;pending<=0;mask<=0;error_code<=0;link_ready<=0;link_generation<=0;software_generation<=0;stop_complete<=1;
   timestamp<=0;tick_div<=0;pulse_counter<=0;accepted_sequence<=0;ingress_sequence<=0;accepted_valid<=0;done_valid<=0;user_cancel<=0;snap_id<=0;snap_valid<=0;
   accept_count<=0;done_count<=0;stale_count<=0;reject_count<=0;cancel_count<=0;stop_count<=0;end_count<=0;observed_sequence<=0;observed_end<=0;
   for(i=0;i<64;i=i+1)snapshot[i]<=0;
  end else begin
   execute<=0;dispatch_pending<=0;req_open<=0;req_enable<=0;req_start<=0;req_pause<=0;req_resume<=0;req_disable<=0;req_rebase<=0;req_clear<=0;
   ack_event<=0;pending<=(pending & ~w1c)|events;
   if(tick_div==`PLI_MOTION_GP_MOTION_V1_CYCLES_PER_TICK-1)begin tick_div<=0;timestamp<=timestamp+1'b1;end else tick_div<=tick_div+1'b1;
   pulse_counter<=pulses;
   if(accepted && !(&accept_count))accept_count<=accept_count+1;
   if(point_done && !(&done_count))done_count<=done_count+1;
   if(stale && !(&stale_count))stale_count<=stale_count+1;
   if((rejected || rx_error) && !(&reject_count))reject_count<=reject_count+1;
   if(cancelled && !(&cancel_count))cancel_count<=cancel_count+1;
   if(stopped && !(&stop_count))stop_count<=stop_count+1;
   if(session_done && !(&end_count))end_count<=end_count+1;
   if(rx_valid && rx_ready && rx_session==session_id && session_valid)ingress_sequence<=rx_sequence;
   if(rx_valid && rx_ready && rx_session==session_id && session_valid && !sequence_violation)begin observed_sequence<=observed_sequence+1;observed_end<=rx_end;end
   if(sequence_violation)error_code<=`PLI_ERR_SEQUENCE;
   if(accepted)begin accepted_valid<=1;accepted_sequence<=ingress_sequence;end
   if(point_done)done_valid<=1;
   if(point_start)stop_complete<=0;
   if(stop_write || req_disable)user_cancel<=1;
   if(stopped || (cancel_transport && !core_busy))stop_complete<=1;
   if(cancel_transport)begin
    link_ready<=0;
    if(link_ready)link_generation<=link_generation+1'b1;
    if(!session_done)begin
     if(dma_error)error_code<=`PLI_ERR_DMA;
     else if(rx_error)error_code<=`PLI_ERR_BAD_RECORD;
     else if(underflow)error_code<=`PLI_ERR_UNDERRUN;
     else if(!reset_ok && link_ready)error_code<=`PLI_ERR_LINK_RESET;
     else if(|fault)error_code<=`PLI_ERR_INTERLOCK;
     else if(cancelled && rejected && error_code==0 && !user_cancel)error_code<=`PLI_ERR_UNEXECUTABLE;
    end
   end
   if(s_awvalid && s_awready)begin ah<=1;offset<=s_awaddr[11:0];aw_hit<=s_awaddr[32:12]==BASE[32:12];stop_address<=s_awaddr==(BASE+`PLI_MOTION_GP_MOTION_V1_REG_STOP);end
   if(s_wvalid && s_wready)begin wh<=1;wd<=s_wdata;ws<=s_wstrb;stop_data<=s_wstrb==15 && s_wdata==1;end
   if(s_bvalid && s_bready)s_bvalid<=0;
   if(write_fire)begin
    ah<=0;wh<=0;s_bvalid<=1;s_bresp<=write_response;
    if(good_write)case(offset)
     `PLI_MOTION_GP_MOTION_V1_REG_OPCODE:opcode<=wd;
     `PLI_MOTION_GP_MOTION_V1_REG_ARG:arg<=wd;
     `PLI_MOTION_GP_MOTION_V1_REG_TXN:txn<=wd;
     `PLI_MOTION_GP_MOTION_V1_REG_SESSION_LO:session_shadow[31:0]<=wd;
     `PLI_MOTION_GP_MOTION_V1_REG_SESSION_HI:session_shadow[63:32]<=wd;
     `PLI_MOTION_GP_MOTION_V1_REG_MAINT:maintenance<=wd;
     `PLI_MOTION_GP_MOTION_V1_REG_RECOVER_GEN:recover_gen<=wd;
     `PLI_MOTION_GP_MOTION_V1_REG_IRQ_MASK:mask<=wd;
     `PLI_MOTION_GP_MOTION_V1_REG_SUBMIT:if(txn!=last_id)begin
      command_busy<=1;ack_valid<=0;ack_completed<=0;ack_accepted<=0;
      captured_opcode<=opcode;captured_arg<=arg;captured_id<=txn;captured_session<=session_shadow;
      captured_rebase<=rebase_shadow;captured_maintenance<=maintenance[0];captured_generation<=recover_gen;
      last_payload<=shadow_payload;last_id<=txn;execute<=1;
     end
     default:if(offset>=`PLI_MOTION_GP_MOTION_V1_REG_REBASE_0 && offset<=`PLI_MOTION_GP_MOTION_V1_REG_REBASE_7)rebase_shadow[((offset-`PLI_MOTION_GP_MOTION_V1_REG_REBASE_0)>>2)*32+:32]<=wd;
    endcase
   end
   if(snapshot_write)begin for(i=0;i<64;i=i+1)snapshot[i]<=snap_live[i];snap_id<=wd;snap_valid<=1;end
   if(execute)begin
    ack_id<=captured_id;ack_valid<=1;ack_accepted<=guarded_command_ok && !(stop_write || (|fault) || dma_error || !reset_ok || rx_error);ack_completed<=1;ack_error<=guarded_command_ok && !(stop_write || (|fault) || dma_error || !reset_ok || rx_error) ? 0:`PLI_ERR_BAD_COMMAND;
    command_busy<=0;ack_event<=1;
    if(guarded_command_ok && !(stop_write || (|fault) || dma_error || !reset_ok || rx_error))begin
     req_open<=cmd_open;req_enable<=cmd_enable;req_start<=cmd_start;req_pause<=cmd_pause;
     req_resume<=cmd_resume;req_disable<=cmd_disable;req_rebase<=cmd_rebase;req_clear<=cmd_clear;
     dispatch_pending<=1;command_busy<=1;ack_valid<=0;ack_completed<=0;ack_event<=0;
     if(cmd_recover)begin link_ready<=1;link_generation<=link_generation+1'b1;software_generation<=captured_generation;end
     if(cmd_clear)error_code<=0;
     if(cmd_open)begin user_cancel<=0;accepted_valid<=0;done_valid<=0;accepted_sequence<=0;observed_sequence<=0;observed_end<=0;end
     if(cmd_pause || cmd_disable)begin command_busy<=1;ack_completed<=0;end
    end
   end else if(dispatch_pending)begin
    ack_valid<=1;ack_event<=1;ack_completed<=!(req_pause || req_disable);command_busy<=req_pause || req_disable;
    if(stop_write || rx_error || (|fault) || dma_error || !reset_ok)begin ack_accepted<=0;ack_error<=`PLI_ERR_LINK_RESET;ack_completed<=1;command_busy<=0;end
   end else if(command_busy)begin
    if((captured_opcode==`PLI_CMD_PAUSE && paused) || (captured_opcode==`PLI_CMD_DISABLE && !core_busy && !(|(enabled & captured_arg[3:0]))))begin command_busy<=0;ack_completed<=1;ack_event<=1;end
    else if(stop_write || rx_error || (|fault) || dma_error || !reset_ok || (session_done && captured_opcode==`PLI_CMD_PAUSE))begin command_busy<=0;ack_completed<=1;ack_error<=`PLI_ERR_LINK_RESET;ack_event<=1;end
   end
   if(s_rvalid && s_rready)s_rvalid<=0;
   if(s_arvalid && s_arready)begin
    s_rvalid<=1;s_rdata<=read_data;
    s_rresp<=s_araddr[32:12]!=BASE[32:12] ? 3 : (s_araddr[1:0]!=0 || !read_known ? 2:0);
   end
  end
 end
endmodule
