`timescale 1ns/1ps
module tb_physical_timing;
reg clk=0;always #5 clk=~clk;
reg rst=0,hen=0,href=0,stop=0;reg [2:0] run=0,direction=0;reg [3:0] contact=0;
wire [3:0] active,released,step,dir,en,cfg;wire sampled,qualified,safe;integer cycle=0,checks=0,i;
safety_inputs #(.RELEASE_CYCLES(2000000)) inputs(clk,rst,contact,active,released,qualified,sampled);
motion_executor #(.STEP_HIGH_CYCLES({64'd0,{3{64'd3125}}}),.STEP_LOW_CYCLES({64'd0,{3{64'd3125}}}),
 .DIR_SETUP_CYCLES({64'd0,{3{64'd500}}}),.DIR_HOLD_CYCLES({64'd0,{3{64'd500}}}),
 .EN_SETUP_CYCLES({64'd0,{3{64'd500}}}),.EN_DISABLE_CYCLES({64'd0,{3{64'd500}}}),
 .MAX_STEP_HZ({64'd0,{3{64'd16000}}}),.HOME_SUPPORT(1),.FAST_STEP_STOP(1)) dut(
 .clk(clk),.rst_n(rst),.rebase_req(1'b0),.rebase_mask(4'd0),.rebase_position(256'd0),
 .enable_req(1'b0),.enable_mask(4'd0),.disable_req(1'b0),.disable_mask(4'd0),.stop_req(stop),.fault(4'd0),.clear_fault(1'b0),
 .plan_valid(1'b0),.plan_data(1197'd0),.step(step),.dir(dir),.en(en),.config_valid(cfg),.pulse_safe(safe),
 .home_owner(1'b1),.home_enable(hen),.home_reference(href),.home_complete(1'b0),
 .home_run(run),.home_direction(direction),.home_period({3{64'd1000000}}),.home_reference_position({3{-64'sd150}}),
 .safety_invalidate(4'd0),.fast_step_stop(stop));
integer rise[0:2],fall[0:2],dir_change[0:2],en_rise[0:2],pulses[0:2];reg [3:0] prevstep=0,prevdir=15,preven=0;
task check;input ok;input [511:0] label;begin checks=checks+1;if(!ok)$fatal(1,"%0s cycle=%0d",label,cycle);end endtask
always @(negedge clk)if(rst)begin
 cycle=cycle+1;
 for(i=0;i<3;i=i+1)begin
  if(dir[i]!=prevdir[i])begin check(!step[i]&&cycle-rise[i]>=500,"DIR hold and STEP low");dir_change[i]=cycle;end
  if(en[i]&&!preven[i])en_rise[i]=cycle;
  if(step[i]&&!prevstep[i])begin
   if(pulses[i])check(cycle-rise[i]>=1000000,"100Hz minimum edge interval");
   check(cycle-fall[i]>=3125&&cycle-dir_change[i]>=500&&cycle-en_rise[i]>=500,"low/DIR/EN setup guards");
   rise[i]=cycle;pulses[i]=pulses[i]+1;
  end
  if(!step[i]&&prevstep[i])begin check(cycle-rise[i]==3125,"STEP high exactly 31.25us even after STOP");fall[i]=cycle;end
 end
 prevstep=step;prevdir=dir;preven=en;
end
initial begin
 for(i=0;i<3;i=i+1)begin rise[i]=-10000000;fall[i]=-10000000;dir_change[i]=-10000000;en_rise[i]=-10000000;pulses[i]=0;end
 repeat(4)@(posedge clk);@(posedge clk);#1;rst=1;contact=15;
 repeat(2000000)@(posedge clk);#1;check(released==0,"no stable release before full 20ms plus synchronization");
 repeat(8)@(posedge clk);#1;check(released==15,"all inputs stable released after 20ms");
 contact[0]=0;repeat(4)@(posedge clk);#1;check(active[0]&&!released[0],"assertion stays fast and revokes stable release");
 contact[0]=1;
 @(posedge clk);#1;hen=1;@(posedge clk);#1;hen=0;href=1;@(posedge clk);#1;href=0;run=7;
 wait(pulses[0]>=2);@(posedge clk);#1;stop=1;run=0;
 repeat(7000)@(posedge clk);#1;
 check(step==0&&safe,"STOP drains complete pulses");
 check(pulses[0]==2&&pulses[1]==2&&pulses[2]==2,"exact two home edges, no late edge");
 check(cfg[2:0]==7&&en[3]==0&&step[3]==0,"motor3125 parameters compatible, M4 inactive");
 $display("PASS %0d exact 100MHz pulse/release timing checks over %0d cycles",checks,cycle);$finish;
end
initial begin #50000000;$fatal(1,"timing bench deadline");end
endmodule
