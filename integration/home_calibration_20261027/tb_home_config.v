`timescale 1ns/1ps
`include "safety_defs.vh"
module tb_home_config;
localparam CONFIG_PROFILE=0;
`include "safety_parameters.vh"
reg clk=0;always #5 clk=~clk;
reg rst=0;reg [63:0] us=0;reg [3:0] active=0,released=15,pulse=0;
reg home=0,stop=0,abort_external=0,detect=0,permit=1;reg [31:0] il_causes=0;
wire [3:0] state;wire [2:0] run,dir,hit,rel,done;wire owner,reference,complete,cfg;
wire [31:0] causes;wire [191:0] travel;wire cancelled;
safety_controller #(.CONFIG_APPROVED(C_APPROVED),.INTERLOCK_SUPPORT(1),.SPLIT_RUN_PERMIT(1),
 .HOME_DIRECTION(C_HOME_DIRECTION),.SEARCH_PERIOD(C_SEARCH_PERIOD),.PULL_PERIOD(C_PULL_PERIOD),.PRE_PERIOD(C_PRE_PERIOD),
 .REFERENCE_POSITION(C_REFERENCE_POSITION),.PULL_DISTANCE(C_PULL_DISTANCE),.PRE_DISTANCE(C_PRE_DISTANCE),
 .SEARCH_MAX_STEPS(C_SEARCH_MAX_STEPS),.PULL_MAX_STEPS(C_PULL_MAX_STEPS),.PRE_MAX_STEPS(C_PRE_MAX_STEPS),
 .SEARCH_MAX_US(C_SEARCH_MAX_US),.PULL_MAX_US(C_PULL_MAX_US),.PRE_MAX_US(C_PRE_MAX_US)) dut(
 .clk(clk),.rst_n(rst),.time_us(us),.qualified(1'b1),.active(active),.released(released),
 .home_request(home),.clear_request(1'b0),.stop_request(stop),.idle(1'b1),.pulse_safe(1'b1),
 .external_abort(abort_external),.executor_fault(3'd0),.position_valid(4'd0),.pulse_event(pulse),.config_valid(4'd7),
 .config_ok(cfg),.home_owner(owner),.home_reference(reference),.home_complete(complete),.home_run(run),.home_direction(dir),
 .state(state),.causes(causes),.hit_mask(hit),.released_mask(rel),.done_mask(done),.travel(travel),.home_cancelled(cancelled),
 .interlock_run_permit(permit),.interlock_permit(permit),.interlock_detect(detect),.interlock_disable(detect),
 .interlock_clear_ok(1'b1),.interlock_causes(il_causes));
integer checks=0,i,n;reg [2:0] mask;
task check;input ok;input [511:0] label;begin checks=checks+1;if(!ok)$fatal(1,"%0s state=%d counts=%h",label,state,travel);end endtask
task cycle;begin @(posedge clk);#1;@(negedge clk);end endtask
task reset;input [3:0] contacts;begin
 rst=0;home=0;stop=0;abort_external=0;detect=0;permit=1;il_causes=0;pulse=0;us=0;active=contacts;released=~contacts;
 repeat(3)cycle;rst=1;repeat(3)cycle;check(cfg,"exact calibration configuration valid");
end endtask
task begin_home;begin home=1;cycle;home=0;end endtask
task edges;input [2:0] lanes;begin pulse={1'b0,lanes};cycle;pulse=0;cycle;end endtask
task search_ready;begin reset(0);begin_home;repeat(3)cycle;check(state==`SAF_STATES_SEARCH,"open inputs enter search");check(dir==0,"search direction 000");end endtask
task hit_all;begin active=7;released=8;repeat(5)cycle;check(state==`SAF_STATES_PULL,"all hits drain then private reference");end endtask
initial begin
 check(C_HOME_ONLY && C_REFERENCE_POSITION=={3{-64'sd150}},"count reference is contact -150, not mechanical zero");
 reset(1);begin_home;check(state==`SAF_STATES_PRE && run==1 && dir==7,"closed input pre-pull only affected axis");
 for(n=0;n<150;n=n+1)begin if(n==3)begin active=0;released=15;end edges(1);end
 repeat(3)cycle;check(state==`SAF_STATES_SEARCH,"pre-pull exactly 150 reaches search");
 for(n=0;n<9;n=n+1)begin
  mask=run;edges(mask);
  if(n==4)begin active[0]=1;released[0]=0;end
  if(n==6)begin active[1]=1;released[1]=0;end
  if(n==8)begin active[2]=1;released[2]=0;end
  cycle;
 end
 repeat(5)cycle;check(state==`SAF_STATES_PULL && hit==7,"independent 5/7/9-step search hits");check(dir==7,"pull direction 111");
 active=0;released=8;
 for(n=0;n<150;n=n+1)edges(7);
 check(travel=={3{64'd150}} && run==0,"fixed 150 pull never adds pulses while awaiting release");
 repeat(8)cycle;check(state==`SAF_STATES_PULL,"wait for stable release without stepping");
 released=15;repeat(4)cycle;check(state==`SAF_STATES_READY,"HOME complete after released and drained");
 search_ready;for(n=0;n<500;n=n+1)edges(7);repeat(3)cycle;
 check((causes & `SAF_CAUSES_SEARCH_FAIL)!=0 && run==0,"500 actual emitted pulses fail search");
 search_ready;us=10000000;repeat(3)cycle;check((causes & `SAF_CAUSES_SEARCH_FAIL)!=0,"10-second search deadline");
 reset(1);begin_home;us=3000000;repeat(3)cycle;check((causes & `SAF_CAUSES_PRE_FAIL)!=0,"3-second pre-pull deadline");
 search_ready;hit_all;us=3000000;repeat(3)cycle;check((causes & `SAF_CAUSES_PULL_FAIL)!=0,"3-second formal pull deadline");
 search_ready;hit_all;active=0;released=15;edges(7);active=1;released=14;repeat(3)cycle;
 check((causes & `SAF_CAUSES_RECONTACT)!=0 && run==0,"recontact after release cancels HOME");
 for(i=0;i<5;i=i+1)begin
  search_ready;
  case(i)
   0:stop=1;
   1:active=8;
   2:begin detect=1;il_causes=32'h8000;end
   3:begin detect=1;il_causes=32'h200;end
   4:abort_external=1;
  endcase
  cycle;check(run==0,"STOP/estop/watchdog/485/external cancel prohibit candidates");
  stop=0;active=0;detect=0;il_causes=0;abort_external=0;repeat(5)cycle;
  edges(7);check(run==0 && !owner,"late pulse/record cannot resume cancelled HOME");
 end
 $display("PASS %0d calibration controller checks; real counts/parameters, synthetic event/time driver",checks);$finish;
end
initial begin #1000000;$fatal(1,"bench timeout");end
endmodule
