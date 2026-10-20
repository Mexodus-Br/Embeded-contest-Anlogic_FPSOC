`timescale 1ns/1ps
`include "safety_defs.vh"
// Inductive projection check. Each case starts with a legal encoded state and
// its matching cached bit, then checks their relation after the real RTL edge.
// Exhaustive effective predicates include contradictory combinations to cover
// every priority collision; these hierarchical injections are simulation only.
module tb_interlock_owner_projection;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,home_request=0,clear_request=0,pulse_safe=0,interlock_disable=0;
 reg f_abort=0,f_limit=0,f_estop=0,f_request=0,f_clear=0,f_complete=0;
 wire [3:0] state;wire owner;
 integer s,p,checks=0;
 safety_controller #(.INTERLOCK_SUPPORT(1)) dut(
  .clk(clk),.rst_n(rst_n),.time_us(64'd0),.qualified(1'b1),.active(4'd0),.released(4'd15),
  .home_request(home_request),.clear_request(clear_request),.stop_request(1'b0),
  .idle(1'b1),.pulse_safe(pulse_safe),.external_abort(1'b0),.executor_fault(3'd0),
  .position_valid(4'd0),.pulse_event(4'd0),.config_valid(4'd0),
  .state(state),.home_owner(owner),.interlock_permit(1'b1),.interlock_detect(1'b0),
  .interlock_disable(interlock_disable),.interlock_clear_ok(1'b1),.interlock_causes(32'd0));
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  for(s=0;s<=`SAF_STATES_FAULT;s=s+1)for(p=0;p<2048;p=p+1)begin
   @(negedge clk);
   dut.state=s;
   dut.home_owner_q=(s>=`SAF_STATES_PRE && s<=`SAF_STATES_FINISH) || s==`SAF_STATES_DRAIN;
   dut.causes=p[4] ? 32'd8:32'd0;
   f_abort=p[0];f_limit=p[1];f_estop=p[2];interlock_disable=p[3];
   home_request=p[5];f_request=p[6];clear_request=p[7];f_clear=p[8];
   pulse_safe=p[9];f_complete=p[10];
   force dut.abort_now=f_abort;
   force dut.ordinary_limit=f_limit;
   force dut.estop=f_estop;
   force dut.request_ok=f_request;
   force dut.clear_ok=f_clear;
   force dut.home_complete=f_complete;
   @(posedge clk);#1;checks=checks+1;
   if(owner!==((state>=`SAF_STATES_PRE && state<=`SAF_STATES_FINISH) || state==`SAF_STATES_DRAIN))
    $fatal(1,"owner projection differs: prior=%0d predicates=%h next=%0d owner=%b",s,p,state,owner);
   release dut.abort_now;release dut.ordinary_limit;release dut.estop;
   release dut.request_ok;release dut.clear_ok;release dut.home_complete;
  end
  $display("PASS interlock_owner_projection checks=%0d",checks);$finish;
 end
 initial begin #5000000;$fatal(1,"owner projection timeout");end
endmodule
