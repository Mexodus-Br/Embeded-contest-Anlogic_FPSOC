`timescale 1ns/1ps
module tb_motion_planner;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cancel=0,req_valid=0,plan_ready=0;
 reg [255:0] base=0,target=0;reg [3:0] mask=15;
 reg [63:0] duration=2,sid=11;reg [31:0] seq=0;reg last=1;
 wire req_ready,valid,error;wire [1196:0] data;
 motion_planner #(.STEP_HIGH_CYCLES({4{64'd3}}),.STEP_LOW_CYCLES({4{64'd2}}),
  .DIR_SETUP_CYCLES({4{64'd4}}),.DIR_HOLD_CYCLES({4{64'd7}}),
  .EN_SETUP_CYCLES({4{64'd5}}),.MAX_STEP_HZ({4{64'd10000000}})) dut(
  .clk(clk),.rst_n(rst_n),.cancel(cancel),.req_valid(req_valid),.req_ready(req_ready),
  .base_position(base),.target_position(target),.axis_mask(mask),.duration_tick(duration),
  .request_session(sid),.request_sequence(seq),.request_end(last),.plan_valid(valid),
  .plan_ready(plan_ready),.plan_data(data),.error(error));
 wire [255:0] pb,pe,counts;wire [3:0] positive,moving,pm;
 wire [63:0] master,guard,cycles,quotient,remainder,ps;wire [31:0] pq;wire pl;
 assign {pb,pe,counts,positive,moving,master,guard,cycles,quotient,remainder,ps,pq,pl,pm}=data;
 integer checks=0,i,n;
 reg [1196:0] snapshot;
 task check;input condition;begin checks=checks+1;if(condition!==1'b1)$fatal(1,"planner check %0d",checks);end endtask
 task tick;begin @(posedge clk);#2;end endtask
 task request;begin @(negedge clk);req_valid=1;tick;@(negedge clk);req_valid=0;end endtask
 initial begin
  tick;@(negedge clk);rst_n=1;
  target={64'd0,-64'sd3,64'd5,64'd7};request;
  n=0;while(!valid && n<70)begin tick;n=n+1;end
  check(valid && n==65);check(pb==0 && pe==target && counts=={64'd0,64'd3,64'd5,64'd7});
  check(positive[2:0]==3 && moving==7 && master==7 && guard==13 && cycles==200);
  check(quotient==26 && remainder==5 && ps==11 && pq==0 && pl && pm==15);
  snapshot=data;target={4{64'hffffffffffffffff}};duration=0;base={4{64'd1}};
  repeat(9)begin tick;check(valid && data==snapshot && !req_ready);end
  @(negedge clk);plan_ready=1;tick;@(negedge clk);plan_ready=0;check(req_ready);
  base=0;target=0;mask=0;duration=1;request;check(valid && master==0 && cycles==100 && pb==pe);
  @(negedge clk);cancel=1;tick;@(negedge clk);cancel=0;#1;check(req_ready && !valid);
  mask=15;duration=2;
  for(i=0;i<70;i=i+1)begin
   target={64'd0,-64'sd3,64'd5,64'd7};request;repeat(i)tick;
   @(negedge clk);cancel=1;tick;check(!valid);@(negedge clk);cancel=0;
   repeat(70)tick;check(req_ready && !valid);
  end
  duration=0;request;check(error && !valid);
  duration=64'hffffffffffffffff;request;check(error && !valid);
  base={4{64'h8000000000000000}};target={4{64'h7fffffffffffffff}};duration=2;request;
  n=0;while(!error && n<70)begin tick;n=n+1;end check(error && !valid);
  $display("PASS planner checks=%0d cancel_offsets=70",checks);$finish;
 end
endmodule
