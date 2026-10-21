`timescale 1ns/1ps
module tb_motor;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,rebase=0,enable=0,open=0,start=0,stop=0,valid=0;
reg [63:0] ticks=282;
reg [255:0] target=0;
wire ready,accepted,rejected,started,done,session_done,busy,start_ready,stopped;
wire [3:0] step,dir,en,pulse,faults;
wire [255:0] pos;
continuous_motion #(.FIFO_DEPTH(64),.PLAN_DEPTH(8),.START_MIN_POINTS(32),
 .STEP_HIGH_CYCLES({64'd0,{3{64'd3125}}}),.STEP_LOW_CYCLES({64'd0,{3{64'd3125}}}),
 .DIR_SETUP_CYCLES({64'd0,{3{64'd500}}}),.DIR_HOLD_CYCLES({64'd0,{3{64'd500}}}),
 .EN_SETUP_CYCLES({64'd0,{3{64'd500}}}),.EN_DISABLE_CYCLES({64'd0,{3{64'd500}}}),
 .MAX_STEP_HZ({64'd0,{3{64'd16000}}})) dut(
 .clk(clk),.rst_n(rst_n),.rebase_req(rebase),.rebase_mask(4'd7),.rebase_position(256'd0),
 .enable_req(enable),.enable_mask(4'd7),.disable_req(1'b0),.disable_mask(4'd0),
 .open_req(open),.open_session_id(64'd1),.start_req(start),.pause_req(1'b0),.resume_req(1'b0),
 .stop_req(stop),.clear_fault(1'b0),.fault(4'd0),.point_valid(valid),.point_ready(ready),
 .point_session(64'd1),.duration_tick(ticks),.point_sequence(32'd0),.point_end(1'b1),
 .point_mask(4'd7),.point_target(target),.step(step),.dir(dir),.en(en),.position(pos),
 .fault_latched(faults),.busy(busy),.start_ready(start_ready),.accepted(accepted),
 .rejected(rejected),.point_start(started),.point_done(done),.session_done(session_done),
 .stopped(stopped),.pulse_event(pulse));
integer cycle=0,checks=0,i,point_cycle,done_count=0;
integer rise[0:3],fall[0:3],counts[0:3]; reg [3:0] prev=0;
task check; input condition; begin checks=checks+1; if(condition!==1)$fatal(1,"check %0d cycle %0d",checks,cycle);end endtask
always @(posedge clk) begin #1;cycle=cycle+1;
 if(!rst_n)begin prev=0;for(i=0;i<4;i=i+1)begin rise[i]=-10000;fall[i]=-10000;counts[i]=0;end end
 else begin
  check(step[3]==0 && en[3]==0);
  for(i=0;i<3;i=i+1)begin
   if(step[i]&&!prev[i])begin check(cycle-fall[i]>=3125);rise[i]=cycle;counts[i]=counts[i]+1;end
   if(!step[i]&&prev[i])begin check(cycle-rise[i]==3125);fall[i]=cycle;end
  end
  check(pulse==(step&~prev)); prev=step;
  if(started)point_cycle=cycle;
  if(done)begin check(cycle-point_cycle==28200);check(step==0);done_count=done_count+1;end
 end
end
task tick;begin @(posedge clk);#2;end endtask
task initialize;begin
 @(negedge clk);rst_n=0;rebase=0;enable=0;open=0;valid=0;start=0;stop=0;repeat(3)tick;
 @(negedge clk);rst_n=1;repeat(3130)tick;
 @(negedge clk);rebase=1;tick;@(negedge clk);rebase=0;enable=1;tick;
 @(negedge clk);enable=0;repeat(505)tick;@(negedge clk);open=1;tick;@(negedge clk);open=0;
end endtask
task submit;begin
 @(negedge clk);valid=1;while(!ready)tick;tick;check(accepted);@(negedge clk);valid=0;
end endtask
task run_start;begin while(!start_ready)tick;@(negedge clk);start=1;tick;@(negedge clk);start=0;end endtask
integer phase;
initial begin
 $dumpfile("motor3125.vcd");$dumpvars(1,tb_motor);
 target={64'd0,-64'sd2,64'd3,64'd4}; initialize;submit;run_start;
 while(!session_done)tick;
 check(counts[0]==4&&counts[1]==3&&counts[2]==2);check(pos==target&&faults==0&&done_count==1);
 // Positive and negative physical direction, independently from model signs.
 target={64'd0,64'd2,-64'sd3,-64'sd4};initialize;submit;run_start;while(!session_done)tick;
 check(counts[0]==4&&counts[1]==3&&counts[2]==2);check(pos==target&&faults==0&&dir[2:0]==4);
 // 281us cannot contain guard3127 plus four periods of6250 cycles.
 initialize;ticks=281;submit;while(!rejected)tick;check(step==0);ticks=282;
 // STOP early/middle/last high cycle and inside the minimum low interval.
 for(phase=0;phase<4;phase=phase+1)begin
  initialize;submit;run_start;while(!step[0])tick;
  if(phase==1)repeat(1560)tick;
  if(phase==2)repeat(3123)tick;
  if(phase==3)repeat(4000)tick;
  @(negedge clk);stop=1;tick;@(negedge clk);stop=0;
  while(busy)tick;
  check(step==0&&counts[0]==1&&counts[1]==1&&counts[2]==1);
 end
 $display("PASS MOTOR3125 checks=%0d H=3125 L>=3125 END-duration=28200 STOP-phases=4",checks);$finish;
end
initial begin #5000000;$fatal(1,"timeout");end
endmodule
