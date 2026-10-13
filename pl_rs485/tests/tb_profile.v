`timescale 1ns/1ps
// Real 100MHz/115200 confirmed profile. Independent line slave and cycle measurements.
module tb_profile;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,enable=0,rx=1;
 wire tx,de,valid,busy;
 wire [255:0] data;
 wire [31:0] level,drop,ok,err,ignored;
 reg [63:0] time_us=64'd900000;
 integer div=0,cycles=0;
 always @(posedge clk) begin
  cycles=cycles+1;
  if(div==99) begin div=0;time_us<=time_us+1;end else div=div+1;
 end
 rs485_master dut(clk,rst_n,enable,5'b00001,time_us,rx,tx,de,1'b1,valid,data,level,drop,ok,err,ignored,busy);
 task ticks;input integer n;begin repeat(n) @(negedge clk);end endtask
 task read_byte;output [7:0] b;integer j;
  begin ticks(1302);for(j=0;j<8;j=j+1) begin b[j]=tx;ticks(868);end
   if(tx!==1) $fatal(1,"stop");ticks(434);end
 endtask
 task send_byte;input [7:0] b;integer j;
  begin rx=0;ticks(868);for(j=0;j<8;j=j+1) begin rx=b[j];ticks(868);end rx=1;ticks(868);end
 endtask
 reg [7:0] a,c,k,check;
 integer count=0,requests=0,rise,stop,previous_rise=0;
 always @(posedge de) begin
  if(previous_rise!=0) $display("PROFILE request interval cycles=%0d us=%0.2f",cycles-previous_rise,(cycles-previous_rise)/100.0);
  rise=cycles;previous_rise=cycles;
 end
 initial forever begin
  @(negedge tx);
  if(cycles-rise<1000) $fatal(1,"pre too short");
  read_byte(a);@(negedge tx);read_byte(c);@(negedge tx);read_byte(k);stop=cycles;
  if(a!=(8'he0+requests) || c!=8'h30 || k!=((a+c)&255)) $fatal(1,"profile request");
  requests=requests+1;
  @(negedge de);
  if(cycles-stop<1000) $fatal(1,"last stop hold");
  $display("PROFILE DE pre-to-release cycles=%0d stop-to-release=%0d",cycles-rise,cycles-stop);
  ticks(2000);check=a;send_byte(a);
  send_byte(8'hff);check=check+8'hff;send_byte(8'hff);check=check+8'hff;
  send_byte(8'hff);check=check+8'hff;send_byte(8'hff);check=check+8'hff;
  send_byte(8'he6);check=check+8'he6;send_byte(8'h7e);check=check+8'h7e;
  send_byte(check);
 end
 always @(posedge clk) if(valid) begin
  if(data[231:224]!=0 || data[47:0]!=48'hFFFFFFFFE67E || data[215:208]!=6 ||
     data[175:112]>data[111:48] || data[111:48]>time_us) $fatal(1,"profile record");
  count=count+1;
  if(count==3) begin enable=0;$display("PASS profile 100MHz 115200 8N1, three nodes encoder, timestamps, DE full stop");$finish;end
 end
 initial begin ticks(10);rst_n=1;enable=1;end
 initial begin #100000000;$fatal(1,"profile watchdog");end
endmodule
