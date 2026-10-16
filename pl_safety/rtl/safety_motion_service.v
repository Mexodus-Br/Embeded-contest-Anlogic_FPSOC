`include "safety_defs.vh"
`timescale 1ns/1ps
`include "generated/interface_defs.vh"
// Independent GP motion profile. All state and the kernel share clk_100m.
module safety_motion_service #(
 parameter FIFO_DEPTH=`PLI_MOTION_GP_MOTION_V1_RAW_DEPTH,PLAN_DEPTH=`PLI_MOTION_GP_MOTION_V1_PLAN_DEPTH,
 parameter START_MIN_POINTS=`PLI_MOTION_GP_MOTION_V1_START_MIN_POINTS,
 parameter [255:0] STEP_HIGH_CYCLES=0,STEP_LOW_CYCLES=0,DIR_SETUP_CYCLES=0,DIR_HOLD_CYCLES=0,
 parameter [255:0] EN_SETUP_CYCLES=0,EN_DISABLE_CYCLES=0,MAX_STEP_HZ=0,
 parameter [3:0] EN_ACTIVE_LEVEL=15,parameter CONFIG_PROFILE=0
)(
 input wire clk,rst_n,dma_reset_released,dma_error,input wire [3:0] fault,
 input wire [32:0] s_awaddr,s_araddr,input wire [31:0] s_wdata,input wire [3:0] s_wstrb,
 input wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready,
 output wire s_awready,s_wready,s_arready,output wire s_bvalid,s_rvalid,
 output wire [1:0] s_bresp,s_rresp,output wire [31:0] s_rdata,
 input wire [63:0] stream_data,input wire [7:0] stream_keep,input wire stream_last,stream_valid,
 output wire stream_ready,irq,
 output wire [3:0] step,dir,en,position_valid,output wire [255:0] position,
 output wire [255:0] pulses,output wire running,paused,core_busy,session_valid,
 output wire [63:0] session_id,output wire [31:0] fifo_level,prepared_level,buffered_points,
 output wire point_start,point_done,stopped,output wire [3:0] pulse_event,
 output wire slot_event,output wire [63:0] slot_id,
 input wire [2:0] limit_n,input wire estop_n,input wire [63:0] shared_time_us,
 input wire [32:0] saf_awaddr,saf_araddr,input wire [31:0] saf_wdata,input wire [3:0] saf_wstrb,
 input wire saf_awvalid,saf_wvalid,saf_bready,saf_arvalid,saf_rready,
 output wire saf_awready,saf_wready,saf_arready,saf_bvalid,saf_rvalid,
 output wire [1:0] saf_bresp,saf_rresp,output wire [31:0] saf_rdata,output wire safety_irq
);
`include "safety_parameters.vh"
wire [3:0] active,released;wire qualified,sampled;
safety_inputs #(.RELEASE_CYCLES(C_RELEASE_CYCLES)) inputs(.clk(clk),.rst_n(rst_n),
 .contact_n({estop_n,limit_n}),.active(active),.released(released),.qualified(qualified),.sampled(sampled));
wire normal_inhibit,owner,hen,href,hcomplete,ctrl_stop,ctrl_disable,ctrl_clear;
// The accepted HOME request revokes position/normal ownership immediately.
// Its executor EN authorization follows one clock later, when HOME already
// owns the idle kernel. This breaks pulse_safe -> request_ok -> home_enable
// -> normal execution/cancel controls; all STOP/contact paths stay direct.
reg hen_execute;
always @(posedge clk or negedge rst_n)
 if(!rst_n)hen_execute<=0;else hen_execute<=hen;
wire [2:0] run,hdirection,hfault;wire [191:0] period,reference_position,travel;
wire [3:0] invalid,state;wire [31:0] causes,first_cause;
wire [63:0] first_time,event_sequence,start_time,done_time;
wire [2:0] hit_mask,released_mask,done_mask;
wire config_ok,request_ok,clear_ok,accepted,rejected,hdone,hcancel;
wire idle,pulse_safe,abort_service;wire hrequest,clear_request,stop_request;
wire [3:0] cfg_native,cfg,executor_faults;
assign cfg[3]=cfg_native[3];
genvar g;generate for(g=0;g<3;g=g+1)begin: home_config
 localparam [63:0] RATE=MAX_STEP_HZ[g*64+:64];
 localparam [64:0] MIN_PERIOD={1'b0,STEP_HIGH_CYCLES[g*64+:64]}+{1'b0,STEP_LOW_CYCLES[g*64+:64]};
 localparam [127:0] MIN_RATE_PERIOD=RATE==0 ? 128'hffffffffffffffffffffffffffffffff : (128'd100000000+RATE-1)/RATE;
 localparam signed [64:0] REF_POS={C_REFERENCE_POSITION[g*64+63],C_REFERENCE_POSITION[g*64+:64]};
 localparam signed [64:0] DIST={1'b0,C_PULL_DISTANCE[g*64+:64]};
 localparam signed [64:0] END_POS=C_HOME_DIRECTION[g] ? REF_POS-DIST : REF_POS+DIST;
 assign cfg[g]=cfg_native[g] && END_POS[64]==END_POS[63] && !C_PULL_DISTANCE[g*64+63] && !C_PRE_DISTANCE[g*64+63] &&
  {1'b0,C_SEARCH_PERIOD[g*64+:64]}>=MIN_PERIOD && {1'b0,C_PULL_PERIOD[g*64+:64]}>=MIN_PERIOD &&
  {1'b0,C_PRE_PERIOD[g*64+:64]}>=MIN_PERIOD && C_SEARCH_PERIOD[g*64+:64]>=MIN_RATE_PERIOD &&
  C_PULL_PERIOD[g*64+:64]>=MIN_RATE_PERIOD && C_PRE_PERIOD[g*64+:64]>=MIN_RATE_PERIOD;
end endgenerate
safety_controller #(.CONFIG_APPROVED(C_APPROVED && C_RELEASE_CYCLES!=0),.HOME_DIRECTION(C_HOME_DIRECTION),
 .SEARCH_PERIOD(C_SEARCH_PERIOD),.PULL_PERIOD(C_PULL_PERIOD),.PRE_PERIOD(C_PRE_PERIOD),
 .REFERENCE_POSITION(C_REFERENCE_POSITION),.PULL_DISTANCE(C_PULL_DISTANCE),.PRE_DISTANCE(C_PRE_DISTANCE),
 .SEARCH_MAX_STEPS(C_SEARCH_MAX_STEPS),.PULL_MAX_STEPS(C_PULL_MAX_STEPS),.PRE_MAX_STEPS(C_PRE_MAX_STEPS),
 .SEARCH_MAX_US(C_SEARCH_MAX_US),.PULL_MAX_US(C_PULL_MAX_US),.PRE_MAX_US(C_PRE_MAX_US)) controller(
 .clk(clk),.rst_n(rst_n),.time_us(shared_time_us),.qualified(sampled),.active(active),.released(released),
 .home_request(hrequest),.clear_request(clear_request),.stop_request(stop_request),
 .idle(idle),.pulse_safe(pulse_safe),.external_abort(abort_service),.executor_fault(hfault | executor_faults[2:0]),
 .position_valid(position_valid),.pulse_event(pulse_event),.config_valid(cfg),
 .config_ok(config_ok),.normal_inhibit(normal_inhibit),.home_owner(owner),.home_enable(hen),
 .home_reference(href),.home_complete(hcomplete),.home_run(run),.home_direction(hdirection),
 .home_period(period),.home_reference_position(reference_position),.stop_motion(ctrl_stop),
 .disable_motion(ctrl_disable),.invalidate(invalid),.clear_executor(ctrl_clear),
 .state(state),.causes(causes),.first_cause(first_cause),.first_time(first_time),.event_sequence(event_sequence),
 .home_start_time(start_time),.home_done_time(done_time),.hit_mask(hit_mask),.released_mask(released_mask),
 .done_mask(done_mask),.travel(travel),.accepted(accepted),.rejected(rejected),.home_done(hdone),
 .home_cancelled(hcancel),.request_ok(request_ok),.clear_ok(clear_ok));
reg [2047:0] live;
always @*begin
 live=0;
 live[`SAF_SNAPSHOT_STATE*32+:32]={28'd0,state};
 live[`SAF_SNAPSHOT_ACTIVE*32+:32]={28'd0,active};
 live[`SAF_SNAPSHOT_RELEASED*32+:32]={28'd0,released};
 live[`SAF_SNAPSHOT_CAUSES*32+:32]=causes;
 live[`SAF_SNAPSHOT_FIRST_CAUSE*32+:32]=first_cause;
 live[`SAF_SNAPSHOT_FIRST_TIME_LO*32+:32]=first_time[31:0];
 live[`SAF_SNAPSHOT_FIRST_TIME_HI*32+:32]=first_time[63:32];
 live[`SAF_SNAPSHOT_EVENT_SEQ_LO*32+:32]=event_sequence[31:0];
 live[`SAF_SNAPSHOT_EVENT_SEQ_HI*32+:32]=event_sequence[63:32];
 live[`SAF_SNAPSHOT_MASKS*32+:32]={21'd0,done_mask,1'b0,released_mask,1'b0,hit_mask};
 live[`SAF_SNAPSHOT_VALID*32+:32]={28'd0,position_valid};
 live[`SAF_SNAPSHOT_EN*32+:32]={28'd0,(en ^ ~EN_ACTIVE_LEVEL)};
 live[`SAF_SNAPSHOT_PULSE_SAFE*32+:32]={31'd0,pulse_safe};
 live[`SAF_SNAPSHOT_TIME_LO*32+:32]=shared_time_us[31:0];
 live[`SAF_SNAPSHOT_TIME_HI*32+:32]=shared_time_us[63:32];
 live[`SAF_SNAPSHOT_HOME_START_LO*32+:32]=start_time[31:0];
 live[`SAF_SNAPSHOT_HOME_START_HI*32+:32]=start_time[63:32];
 live[`SAF_SNAPSHOT_HOME_DONE_LO*32+:32]=done_time[31:0];
 live[`SAF_SNAPSHOT_HOME_DONE_HI*32+:32]=done_time[63:32];
 live[`SAF_SNAPSHOT_POSITION_0*32+:32]=position[0+:32];
 live[`SAF_SNAPSHOT_POSITION_1*32+:32]=position[32+:32];
 live[`SAF_SNAPSHOT_POSITION_2*32+:32]=position[64+:32];
 live[`SAF_SNAPSHOT_POSITION_3*32+:32]=position[96+:32];
 live[`SAF_SNAPSHOT_POSITION_4*32+:32]=position[128+:32];
 live[`SAF_SNAPSHOT_POSITION_5*32+:32]=position[160+:32];
 live[`SAF_SNAPSHOT_TRAVEL_0*32+:32]=travel[0+:32];
 live[`SAF_SNAPSHOT_TRAVEL_1*32+:32]=travel[32+:32];
 live[`SAF_SNAPSHOT_TRAVEL_2*32+:32]=travel[64+:32];
 live[`SAF_SNAPSHOT_TRAVEL_3*32+:32]=travel[96+:32];
 live[`SAF_SNAPSHOT_TRAVEL_4*32+:32]=travel[128+:32];
 live[`SAF_SNAPSHOT_TRAVEL_5*32+:32]=travel[160+:32];
 live[`SAF_SNAPSHOT_PULSES_0*32+:32]=pulses[0+:32];
 live[`SAF_SNAPSHOT_PULSES_1*32+:32]=pulses[32+:32];
 live[`SAF_SNAPSHOT_PULSES_2*32+:32]=pulses[64+:32];
 live[`SAF_SNAPSHOT_PULSES_3*32+:32]=pulses[96+:32];
 live[`SAF_SNAPSHOT_PULSES_4*32+:32]=pulses[128+:32];
 live[`SAF_SNAPSHOT_PULSES_5*32+:32]=pulses[160+:32];
end
safety_regs registers(.clk(clk),.rst_n(rst_n),
.s_awaddr(saf_awaddr),.s_araddr(saf_araddr),.s_wdata(saf_wdata),.s_wstrb(saf_wstrb),.s_awvalid(saf_awvalid),.s_wvalid(saf_wvalid),.s_bready(saf_bready),.s_arvalid(saf_arvalid),.s_rready(saf_rready),.s_awready(saf_awready),.s_wready(saf_wready),.s_arready(saf_arready),.s_bvalid(saf_bvalid),.s_rvalid(saf_rvalid),.s_bresp(saf_bresp),.s_rresp(saf_rresp),.s_rdata(saf_rdata),
 .config_hash(C_CONFIG_HASH),.config_ok(config_ok),.live_snapshot(live),.causes(causes),
 .request_ok(request_ok),.clear_ok(clear_ok),.home_done(hdone),.home_cancelled(hcancel),
 .home_owner(owner),.pulse_safe(pulse_safe),.stopped(stopped),.home_request(hrequest),
 .clear_request(clear_request),.stop_request(stop_request),.irq(safety_irq));
motion_service #(.FIFO_DEPTH(FIFO_DEPTH),.PLAN_DEPTH(PLAN_DEPTH),.START_MIN_POINTS(START_MIN_POINTS),.STEP_HIGH_CYCLES(STEP_HIGH_CYCLES),.STEP_LOW_CYCLES(STEP_LOW_CYCLES),.DIR_SETUP_CYCLES(DIR_SETUP_CYCLES),.DIR_HOLD_CYCLES(DIR_HOLD_CYCLES),.EN_SETUP_CYCLES(EN_SETUP_CYCLES),.EN_DISABLE_CYCLES(EN_DISABLE_CYCLES),.MAX_STEP_HZ(MAX_STEP_HZ),.EN_ACTIVE_LEVEL(EN_ACTIVE_LEVEL),.HOME_SUPPORT(1)) motion(
.clk(clk),.rst_n(rst_n),.dma_reset_released(dma_reset_released),.dma_error(dma_error),.fault(fault),.s_awaddr(s_awaddr),.s_araddr(s_araddr),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_awvalid(s_awvalid),.s_wvalid(s_wvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_rready(s_rready),.s_awready(s_awready),.s_wready(s_wready),.s_arready(s_arready),.s_bvalid(s_bvalid),.s_rvalid(s_rvalid),.s_bresp(s_bresp),.s_rresp(s_rresp),.s_rdata(s_rdata),.stream_data(stream_data),.stream_keep(stream_keep),.stream_last(stream_last),.stream_valid(stream_valid),.stream_ready(stream_ready),.irq(irq),.step(step),.dir(dir),.en(en),.position_valid(position_valid),.position(position),.pulses(pulses),.running(running),.paused(paused),.core_busy(core_busy),.session_valid(session_valid),.session_id(session_id),.fifo_level(fifo_level),.prepared_level(prepared_level),.buffered_points(buffered_points),.point_start(point_start),.point_done(point_done),.stopped(stopped),.pulse_event(pulse_event),.slot_event(slot_event),.slot_id(slot_id),
 .safety_inhibit(normal_inhibit),.safety_stop(ctrl_stop),.safety_disable(ctrl_disable),.safety_clear(ctrl_clear),
 .home_owner(owner),.home_enable(hen_execute),.home_reference(href),.home_complete(hcomplete),.home_run(run),
 .home_direction(hdirection),.home_period(period),.home_reference_position(reference_position),
 .safety_invalidate(invalid),.safety_pulse_safe(pulse_safe),.safety_idle(idle),.safety_abort(abort_service),.home_fault(hfault),.safety_config_valid(cfg_native),.safety_fault_latched(executor_faults));
endmodule
