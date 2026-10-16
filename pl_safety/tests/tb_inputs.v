`timescale 1ns/1ps
module tb_inputs;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg [3:0] raw=15;wire [3:0] active,released;wire qualified;
safety_inputs #(.RELEASE_CYCLES(4)) dut(clk,rst_n,raw,active,released,qualified,);
wire [3:0] inv_active,inv_released;wire inv_qualified;
safety_inputs #(.ACTIVE_LOW(0),.RELEASE_CYCLES(2)) opposite(clk,rst_n,~raw,inv_active,inv_released,inv_qualified,);
wire disabled;wire [3:0] zactive,zreleased;
safety_inputs zero(clk,rst_n,raw,zactive,zreleased,disabled,);
integer checks=0,phase,k;reg [3:0] sample1,sample2;integer ages[0:3];reg [1:0] startup;
task check;input ok;input [255:0] msg;begin checks=checks+1;if(ok!==1'b1)$fatal(1,"inputs %0s phase=%0d",msg,phase);end endtask
// Independent delay-line oracle from physical pins, including release bounce.
always @(posedge clk)begin
 if(!rst_n)begin sample1=0;sample2=0;startup=0;for(k=0;k<4;k=k+1)ages[k]=0;end
 else begin
  for(k=0;k<4;k=k+1)begin
   if(!sample2[k] || !startup[1])ages[k]=0;else if(ages[k]<4)ages[k]=ages[k]+1;
  end
  sample2=sample1;sample1=raw;startup={startup[0],1'b1};
 end
 #1;
 check(active==~sample2,"exact two flop delay");check(!disabled && zreleased==0,"zero release config cannot qualify");
 for(k=0;k<4;k=k+1)check(released[k]==(ages[k]>=4),"continuous stable release only");
 if(qualified && inv_qualified)check(active==inv_active,"explicit polarity normalization");
end
initial begin
 repeat(3)@(negedge clk);rst_n=1;repeat(12)@(negedge clk);
 check(qualified && released==15,"boot stable open qualifies");
 for(phase=0;phase<10;phase=phase+1)begin
  @(negedge clk);#(phase);#0.2;raw=0;repeat(5)@(negedge clk);
  check(active==15 && released==0,"all assertions no debounce");
  raw=15;repeat(2)@(negedge clk);raw=0;repeat(3)@(negedge clk);
  check(released==0,"short release bounce never grants permission");
  raw=15;repeat(9)@(negedge clk);check(released==15,"stable release recovers");
 end
 $display("PASS safety_inputs checks=%0d pad_phases=10",checks);$finish;
end
endmodule
