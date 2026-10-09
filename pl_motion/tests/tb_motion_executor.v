`timescale 1ns/1ps
module tb_motion_executor;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,rebase_req=0,enable_req=0,stop_req=0,valid=0;
 reg [1196:0] data=0;
 wire ready,busy,boundary,safe,start,done,stopped,rejected,rebase_ok;
 wire [3:0] step,dir,en,pulse,position_valid,fl,cv,enabled;
 wire [255:0] position;wire slot;wire [63:0] slot_id;
 motion_executor #(.STEP_HIGH_CYCLES({4{64'd3}}),.STEP_LOW_CYCLES({4{64'd2}}),
  .DIR_SETUP_CYCLES({4{64'd4}}),.DIR_HOLD_CYCLES({4{64'd7}}),.EN_SETUP_CYCLES({4{64'd5}}),
  .MAX_STEP_HZ({4{64'd10000000}})) dut(
  .clk(clk),.rst_n(rst_n),.rebase_req(rebase_req),.rebase_mask(4'd15),.rebase_position(256'd0),
  .enable_req(enable_req),.enable_mask(4'd15),.disable_req(1'b0),.disable_mask(4'd0),
  .stop_req(stop_req),.fault(4'd0),.clear_fault(1'b0),.plan_valid(valid),.plan_ready(ready),.plan_data(data),
  .step(step),.dir(dir),.en(en),.position(position),.position_valid(position_valid),.fault_latched(fl),
  .config_valid(cv),.enabled_state(enabled),.busy(busy),.boundary(boundary),.pulse_safe(safe),
  .point_start(start),.done(done),.stopped(stopped),.plan_rejected(rejected),.rebase_accepted(rebase_ok),
  .pulse_event(pulse),.slot_event(slot),.slot_id(slot_id));
 integer checks=0,cycle=0,starts=0,dones=0,start_time[0:3],i;
 reg [3:0] previous=0;integer rise[0:3],fall[0:3];reg signed [63:0] model[0:3];
 reg [255:0] p1,p2;
 task check;input condition;begin checks=checks+1;if(condition!==1'b1)$fatal(1,"executor check %0d cycle=%0d",checks,cycle);end endtask
 always @(posedge clk)begin
  #1;cycle=cycle+1;
  if(!rst_n)begin previous=0;for(i=0;i<4;i=i+1)begin model[i]=0;rise[i]=-10000;fall[i]=cycle;end end
  else begin
   for(i=0;i<4;i=i+1)begin
    if(step[i]&&!previous[i])begin check(cycle-fall[i]>=2);model[i]=model[i]+(dir[i] ? 64'sd1 : -64'sd1);rise[i]=cycle;end
    if(!step[i]&&previous[i])begin check(cycle-rise[i]==3);fall[i]=cycle;end
    check($signed(position[i*64+:64])===model[i]);
   end
   check(pulse== (step&~previous));previous=step;
   if(done)begin
    check(safe);dones=dones+1;
    if(dones==1)check(cycle-start_time[0]==100 && position==p1);
    if(dones==2)check(cycle-start_time[1]==200 && position==p2);
   end
   if(start)begin start_time[starts]=cycle;starts=starts+1;end
  end
 end
 task tick;begin @(posedge clk);#2;end endtask
 initial begin
  p1={64'd0,64'd1,-64'sd2,64'd3};p2={64'd2,64'd1,64'd1,-64'sd1};
  tick;@(negedge clk);rst_n=1;repeat(10)tick;
  @(negedge clk);rebase_req=1;tick;check(rebase_ok);
  @(negedge clk);rebase_req=0;enable_req=1;tick;
  @(negedge clk);enable_req=0;repeat(8)tick;
  data={256'd0,p1,{64'd0,64'd1,64'd2,64'd3},4'd5,4'd7,64'd3,64'd13,64'd100,64'd29,64'd0,64'd1,32'd0,1'b0,4'd15};
  @(negedge clk);valid=1;tick;check(start && position==0);
  @(negedge clk);valid=0;tick;
  @(negedge clk);data={p1,p2,{64'd2,64'd0,64'd3,64'd4},4'd14,4'd11,64'd4,64'd13,64'd200,64'd46,64'd3,64'd1,32'd1,1'b1,4'd15};valid=1;
  while(!start)tick;check(starts==2 && start_time[1]-start_time[0]==100 && done);
  @(negedge clk);valid=0;
  while(busy)tick;check(dones==2 && position==p2 && cycle-start_time[0]==300);
  @(negedge clk);data={256'd0,p2,256'd0,4'd0,4'd0,64'd0,64'd0,64'd100,64'd0,64'd0,64'd1,32'd2,1'b1,4'd0};valid=1;
  tick;check(rejected && !start);@(negedge clk);valid=0;while(busy)tick;
  @(negedge clk);data={p2,p2,256'd0,4'd0,4'd0,64'd0,64'd0,64'd100,64'd0,64'd0,64'd1,32'd2,1'b1,4'd0};valid=1;stop_req=1;
  tick;check(!start);@(negedge clk);valid=0;stop_req=0;while(busy)tick;
  $display("PASS executor checks=%0d boundary_gap=0 total_cycles=300",checks);$finish;
 end
 initial begin #100000;$fatal(1,"executor timeout");end
endmodule
