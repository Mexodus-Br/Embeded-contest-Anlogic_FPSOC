`timescale 1ns/1ps
module tb_divider;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0;reg [63:0] n;reg [31:0] d;
 wire busy,done;wire [63:0] q;wire [31:0] r;
 div_u64_u32 dut(clk,rst_n,start,n,d,busy,done,q,r);
 integer i,seed=20261013,steps,seed_arg;
 task trial;input [63:0] nn;input [31:0] dd;
  begin @(negedge clk);n=nn;d=dd;start=1;@(negedge clk);start=0;steps=0;
   while(!done && steps<70) begin @(negedge clk);steps=steps+1;end
   if(steps!=64 || q!==nn/dd || r!==nn%dd) $fatal(1,"divider n=%h d=%h q=%h r=%h steps=%0d",nn,dd,q,r,steps);
  end
 endtask
 initial begin
  if($value$plusargs("seed=%d",seed_arg)) seed=seed_arg;
  @(negedge clk);rst_n=1;
  trial(0,1);trial(64'hffffffffffffffff,1);trial(64'hffffffffffffffff,32'hffffffff);
  trial(64'h8000000000000000,32'h80000000);
  for(i=0;i<200;i=i+1) trial({$random(seed),$random(seed)},($random(seed)|1));
  @(negedge clk);n=64'habcdef1234567890;d=17;start=1;@(negedge clk);start=0;
  repeat(20) @(negedge clk);rst_n=0;@(negedge clk);
  if(busy || done) $fatal(1,"reset division");rst_n=1;trial(12345,97);
  $display("PASS divider 64 iterations, seeded arithmetic, reset");$finish;
 end
endmodule
