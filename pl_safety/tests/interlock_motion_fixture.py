"""Reuse the frozen pin-edge oracle and MMIO/record drivers, not its scenarios."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def render():
    text = (ROOT / 'pl_safety/tests/tb_safety.v').read_text()
    text = text[:text.index('initial begin\n if(MODE==1')]
    # Old MODE selects deliberately broken HOME contacts for old scenarios.
    # New scenario numbering must not inherit those fault injections.
    text = text.replace('MODE==', '0==').replace('MODE>=', '0>=').replace('case(MODE)', 'case(0)')
    text = text.replace('rec[160]=1;', 'rec[160]=(MODE==8 ? 0:1);')
    # A single non-END point is deliberately paused at its boundary. Select a
    # one-point startup threshold only for that isolated pause fixture; full
    # actual-top evidence retains the product's unchanged FIFO/thresholds.
    text = text.replace('.START_MIN_POINTS(2)', '.START_MIN_POINTS(MODE==8 ? 1:2)')
    text = text.replace('module tb_safety;', 'module tb_interlock_motion;\n`include "interlock_defs.vh"')
    text = text.replace('reg [63:0] time_us=0;', 'reg [63:0] injected_time=0;reg inject=0;\nreg [63:0] time_us=0;')
    text = text.replace('else if(div>=', 'else if(inject)time_us<=injected_time;\n else if(div>=')
    text = text.replace('safety_motion_service #(', '''reg poll_run=0,collector_busy=0,feedback_commit=0,dma_released=1;reg [255:0] feedback_raw=0;
wire [5:0] fixture_task;wire fixture_formed,fixture_valid,fixture_known;
wire [63:0] fixture_value;wire [31:0] fixture_carry;wire [15:0] fixture_word;wire [7:0] fixture_enum;
rs485_light_parse fixture_parser(feedback_raw,fixture_task,fixture_formed,fixture_valid,fixture_known,
 fixture_value,fixture_carry,fixture_word,fixture_enum);
wire [2:0] fixture_axes={fixture_task==14,fixture_task==9,fixture_task==4} &
 {3{fixture_formed && fixture_valid && fixture_known}};
wire [5:0] fixture_decoded={fixture_axes & {3{fixture_enum==1}},fixture_axes};
wire interlock_idle,interlock_idle_off;
safety_motion_service #(.INTERLOCK_SUPPORT(1),''')
    text = text.replace('.clk(clk),.rst_n(rst_n),.dma_reset_released', '''.collector_run(poll_run),.collector_stop_commit(1'b0),.collector_reset(1'b0),.collector_config_pending(1'b0),.collector_config_stored_pending(1'b0),
.collector_config_change(1'b0),.collector_busy(collector_busy),.collector_generation(32'd1),.collector_revision(32'd1),
.collector_next_generation(32'd1),.collector_next_revision(32'd1),.feedback_predecoded(fixture_decoded),
.collector_next_reset(1'b0),.collector_next_config_change(1'b0),
.collector_periods({32'd1000000,128'd0}),.collector_mask(5'd16),
.feedback_commit(feedback_commit),.feedback_raw(feedback_raw),
.interlock_idle(interlock_idle),.interlock_idle_off(interlock_idle_off),
.clk(clk),.rst_n(rst_n),.dma_reset_released''')
    text = text.replace('.dma_reset_released(1\'b1)', '.dma_reset_released(dma_released)')
    return text + r'''
// Admission may lag drain, but never precede pulse-safe or ownership release.
always @(posedge clk)if(rst_n)begin
 if(dut.owner!==((dut.state>=`SAF_STATES_PRE && dut.state<=`SAF_STATES_FINISH) ||
                dut.state==`SAF_STATES_DRAIN))
  $fatal(1,"cached HOME owner differs from same-cycle state decode");
end
always @(posedge clk)if(rst_n && interlock_idle)begin
 if(!dut.pulse_safe || dut.owner || dut.motion.core_busy ||
    !dut.motion.partial_empty || dut.motion.session_valid)
  $fatal(1,"registered idle grant before complete safe drain");
end
task drive_feedback;input integer axis;input [7:0] enumeration;begin
 feedback_raw=0;feedback_raw[255:248]=1;feedback_raw[247:240]=8'he0+axis;
 feedback_raw[239:232]=8'h3e;feedback_raw[215:208]=1;feedback_raw[7:0]=enumeration;
 feedback_raw[175:112]=time_us;feedback_raw[111:48]=time_us;feedback_commit=1;
end endtask
task feedback;input integer axis;input [7:0] enumeration;begin
 @(negedge clk);drive_feedback(axis,enumeration);@(negedge clk);feedback_commit=0;
end endtask
reg [63:0] owner_token;reg [3:0] collision_step_before;
task heartbeat;input [63:0] seq;begin
 wr(1,`SI_REG_HEARTBEAT_OWNER_LO,owner_token[31:0],0);
 wr(1,`SI_REG_HEARTBEAT_OWNER_HI,owner_token[63:32],0);
 wr(1,`SI_REG_HEARTBEAT_SEQ_LO,seq[31:0],0);
 wr(1,`SI_REG_HEARTBEAT_SEQ_HI,seq[63:32],0);
 wr(1,`SI_REG_HEARTBEAT_COMMIT,1,0);
end endtask
initial begin
 repeat(6)@(negedge clk);rst_n=1;repeat(15)@(negedge clk);
 command(`SAF_COMMANDS_HOME_START);
 check(!dut.registers.ack_accepted && en==0,"HOME requires first feedback/heartbeat");
 // A collector can launch a request on its idle edge while RUN=1. Safety
 // parameter commits must therefore require RUN=0 AND no remaining in-flight
 // transaction, in addition to actuator/owner idle admission.
 wr(1,`SI_REG_SHADOW_AXES,7,0);
 wr(1,`SI_REG_SHADOW_FEEDBACK_US,2000000,0);
 wr(1,`SI_REG_SHADOW_WATCHDOG_US,2000000,0);
 wr(1,`SI_REG_CONFIG_TXN,1,0);
 poll_run=1;repeat(3)@(negedge clk);
 wr(1,`SI_REG_CONFIG_COMMIT,1,2);
 check(dut.interlocks.extension.applied_txn==0,"RUN blocks safety config at query-start boundary");
 poll_run=0;collector_busy=1;repeat(3)@(negedge clk);
 wr(1,`SI_REG_CONFIG_COMMIT,1,2);
 check(dut.interlocks.extension.applied_txn==0,"in-flight collector blocks safety config");
 collector_busy=0;repeat(3)@(negedge clk);
 wr(1,`SI_REG_CONFIG_COMMIT,1,0);
 rd({1'b0,`SAF_BASE}+`SI_REG_CONFIG_ACCEPTED,0,value);check(value==1,"safety config accepted tag");
 rd({1'b0,`SAF_BASE}+`SI_REG_CONFIG_APPLIED,0,value);check(value==1,"safety config applied tag");
 poll_run=1;repeat(3)@(negedge clk);
 feedback(0,2);feedback(1,2);feedback(2,2);
 wr(1,`SI_REG_OWNER_OPEN,1,0);
 rd({1'b0,`SAF_BASE}+`SI_REG_OWNER_LO,0,value);owner_token={32'd0,value};
 heartbeat(1);
 command(`SAF_COMMANDS_HOME_START);check(dut.registers.ack_accepted,"qualified HOME accepted");
 if(MODE==15)begin
  while(!dut.hcomplete)@(negedge clk);
  check(dut.state==`SAF_STATES_FINISH && dut.pulse_safe,"HOME completion candidate prepared");
 end else if(MODE==5 || MODE==6)begin
  while(dut.state!=`SAF_STATES_SEARCH)@(negedge clk);
 end else begin
  while(dut.state!=`SAF_STATES_READY)@(negedge clk);
  check(valid[2:0]==7,"HOME restores valid only at completion");
  if(MODE!=7)start_normal;
 end
 if(MODE==8)begin mcommand(`PLI_CMD_PAUSE,0);while(!dut.motion.paused)@(negedge clk);end
 if(MODE==9)begin
  wr(0,`PLI_MOTION_GP_MOTION_V1_REG_STOP,1,0);repeat(25)@(negedge clk);
  check(dut.interlocks.owner_active,"ordinary STOP does not disarm watchdog");
 end
 if(MODE==10)begin
  dma_released=0;repeat(8)@(negedge clk);dma_released=1;repeat(8)@(negedge clk);
  check(dut.interlocks.owner_active,"DMA-only reset does not disarm watchdog");
 end
 if(MODE==13)begin
  wr(0,`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,1,0);
  for(b=0;b<4;b=b+1)begin
   @(negedge clk);stream_data=rec[b*64+:64];stream_last=0;stream_valid=1;
   @(posedge clk);while(!stream_ready)@(posedge clk);@(negedge clk);stream_valid=0;
  end
  check(!dut.motion.partial_empty,"transport partial packet prepared");
 end
 repeat(OFFSET)@(negedge clk);
 if(MODE==14)begin
  while(!dut.motion.kernel.executor.boundary)@(negedge clk);
  check(dut.motion.kernel.active_end,"normal END boundary candidate prepared");
 end
 if(MODE==16)begin
  while(!(dut.motion.kernel.executor.slot_due && dut.motion.kernel.executor.emission_ok &&
          (|dut.motion.kernel.executor.emit)))@(negedge clk);
  check(!step[0],"new STEP candidate prepared while output low");
 end
 if(MODE==11)begin limit_n=6;@(negedge clk);end
 if(MODE==12)begin estop_n=0;@(negedge clk);end
 if(MODE>=14)begin
  collision_step_before=step;
  drive_feedback(0,1);
  #1;if(MODE==15)check(!dut.hcomplete,"fault suppresses same-edge HOME completion");
  @(negedge clk);feedback_commit=0;
  check((step & ~collision_step_before)==0,"collision detecting edge forbids every new STEP");
  if(MODE==14)check(dut.motion.done_count==0 && !dut.motion.done_valid,"END collision is cancelled, not successful completion");
  if(MODE==15)check(!dut.hdone,"HOME collision never publishes success");
 end else if(MODE<3 || MODE==5 || MODE>=11)feedback(MODE<3 ? MODE:0,1);
 else begin
  // Explicit synthetic-time injection tests expiry, not the 1MHz divider.
  if(MODE==4)begin
   inject=1;injected_time=1000000;repeat(2)@(negedge clk);
   feedback(0,2);feedback(1,2);feedback(2,2);
   injected_time=2000000+dut.interlocks.monitor.watchdog_start;
  end else begin inject=1;injected_time=time_us+2000000;end
  repeat(2)@(negedge clk);
 end
 check(valid[2:0]==0,"fault detecting edge invalidates all axes");
 repeat(30)@(negedge clk);
 check(!session && !running && !dut.owner && en[2:0]==0,"group cancel and original OFF delay");
 check(dut.motion.buffered_points==0 && dut.motion.partial_empty && !dut.motion.link_ready,
       "session/queues/planner/transport cancelled");
 check(dut.causes!=0 && !dut.interlocks.owner_active,"fault and lost owner latched");
 if(MODE==13)begin
  stream_valid=1;stream_last=1;
  repeat(8)begin @(negedge clk);check(!stream_ready,"late old partial packet cannot be accepted");end
  stream_valid=0;stream_last=0;
 end
 if(MODE==11)check(dut.first_cause==1,"same-edge limit takes first-reason priority");
 if(MODE==12)check(dut.first_cause==8,"same-edge estop takes first-reason priority");
 lastpos=pulses;
 wr(1,`SAF_REGISTERS_IRQ_PENDING,15,0);
 repeat(10)@(negedge clk);check(pulses==lastpos && !dut.request_ok,"IRQ clear never restarts");
 // Recover feedback and establish a new owner without clearing the latch.
 limit_n=7;estop_n=1;repeat(10)@(negedge clk);
 poll_run=0;repeat(2)@(negedge clk);poll_run=1;repeat(3)@(negedge clk);
 feedback(0,2);feedback(1,2);feedback(2,2);
 wr(1,`SI_REG_OWNER_OPEN,1,0);
 rd({1'b0,`SAF_BASE}+`SI_REG_OWNER_LO,0,value);check(value!=owner_token[31:0],"fresh owner on recovery");
 owner_token={32'd0,value};heartbeat(1);
 check(dut.causes!=0 && valid[2:0]==0 && pulses==lastpos,"health recovery never clears or moves");
 command(`SAF_COMMANDS_CLEAR_FAULT);repeat(8)@(negedge clk);
 check(dut.causes==0 && valid[2:0]==0 && en[2:0]==0,"manual clear requires HOME and leaves EN off");
 inject=0;
 // Synthetic jumps cannot resume the old divider's epoch; no motion is
 // started after removing the injection in these expiry-only cases.
 $display("PASS interlock_motion mode=%0d offset=%0d checks=%0d",MODE,OFFSET,checks);
 $finish;
end
endmodule
'''
