`timescale 1ns/1ps
module tb_fifo;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,push=0,ready=0;
 reg [255:0] pd=0;
 wire valid;wire [255:0] data;wire [31:0] dropped,level;
 record_fifo #(.DEPTH(3)) dut(clk,rst_n,push,pd,ready,valid,data,dropped,level);
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 integer i;
 initial begin
  tick;rst_n=1;
  for(i=1;i<=3;i=i+1) begin push=1;pd=i;tick;end
  pd=99;tick;
  if(level!=3 || data!=1 || dropped!=1) $fatal(1,"full drop");
  ready=1;pd=4;tick;
  if(level!=3 || data!=2 || dropped!=1) $fatal(1,"full simultaneous pop/push");
  push=0;
  for(i=2;i<=4;i=i+1) begin if(data!=i) $fatal(1,"non power2 wrap ordering");tick;end
  if(valid || level!=0) $fatal(1,"empty");
  dut.dropped=32'hffffffff;ready=0;
  for(i=0;i<4;i=i+1) begin push=1;pd=i;tick;end
  if(dropped!=32'hffffffff) $fatal(1,"drop saturation");
  $display("PASS FIFO atomic full exchange, nonpower2 wrap, saturation");$finish;
 end
endmodule
