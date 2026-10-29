`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,flush=0,vin=0,ready=0;reg [39:0] wd=0;
 wire valid,in_ready;wire [39:0] head,rd;wire [31:0] level;
 motion_fifo #(.WIDTH(40),.DEPTH(64),.SPARE_SLOT(1)) fifo(
  clk,rst_n,flush,vin,in_ready,wd,valid,ready,head,level);
 wire wen=vin && in_ready,ren=valid && ready;
 // Exact bank parameters are inserted from the complete top's exported netlist.
 DR1_PHY_ERAM #(
 ACTUAL_PARAMETERS
 ) bank(
 .clka(clk),.clkb(clk),.addra({2'b00,fifo.wr,5'b11111}),.addrb({2'b00,fifo.rd,5'b11111}),
 .csa({wen,2'b00}),.csb({ren,2'b00}),
 .dia({wd[18:15],wd[13:10],wd[8:5],wd[3:0]}),.dia_extra({wd[19],wd[14],wd[9],wd[4]}),
 .dib({wd[38:35],wd[33:30],wd[28:25],wd[23:20]}),.dib_extra({wd[39],wd[34],wd[29],wd[24]}),
 .doa({rd[18:15],rd[13:10],rd[8:5],rd[3:0]}),.doa_extra({rd[19],rd[14],rd[9],rd[4]}),
 .dob({rd[38:35],rd[33:30],rd[28:25],rd[23:20]}),.dob_extra({rd[39],rd[34],rd[29],rd[24]}));
 reg [39:0] model[0:63];reg [39:0] expected;
 integer count=0,checks=0,full_dual=0,single_dual=0,i,j,seed=20261020;
 reg pop,push;
 task tick;
  input v,r,f;input [39:0] data;
  begin
   @(negedge clk);vin=v;ready=r;flush=f;wd=data;
   @(posedge clk);
   pop=ren;push=wen;
   if(!rst_n || flush)begin count=0;pop=0;push=0;end
   else begin
    if(valid!==(count!=0) || in_ready!==(count<64 || pop))$fatal(1,"logical capacity/handshake");
    if(valid && head!==model[0])$fatal(1,"RTL FIFO old head");
    if(pop && push)begin
     if(fifo.rd==fifo.wr)$fatal(1,"physical RAM collision");
     if(count==64)full_dual=full_dual+1;
     if(count==1)single_dual=single_dual+1;
    end
    if(pop)begin expected=model[0];for(j=0;j<count-1;j=j+1)model[j]=model[j+1];count=count-1;end
    if(push)begin model[count]=data;count=count+1;end
   end
   #2;
   checks=checks+1;
   if(level!==count)$fatal(1,"FIFO level");
   if(pop && rd!==expected)begin
    $display("got=%h expected=%h",rd,expected);$fatal(1,"actual vendor RAM queue order");
   end
  end
 endtask
 initial begin
  #1000;tick(0,0,0,0);@(negedge clk);rst_n=1;
  for(i=0;i<64;i=i+1)tick(1,0,0,40'h1234500000+i);
  repeat(8)tick(1,0,0,40'hfffffffffe);
  for(i=0;i<520;i=i+1)tick(1,1,0,40'h8000000000+i);
  for(i=0;i<63;i=i+1)tick(0,1,0,0);
  for(i=0;i<256;i=i+1)tick(1,1,0,40'h7fffffffff-i);
  for(i=0;i<4096;i=i+1)tick($random(seed),$random(seed),i%173==0,{$random(seed),$random(seed)});
  tick(0,0,1,0);
  for(i=0;i<64;i=i+1)tick(1,0,0,40'hff00000000+i);
  // A between-clock epoch reset invalidates old RAM contents immediately.
  @(negedge clk);vin=0;ready=0;#1;rst_n=0;count=0;#2;rst_n=1;
  for(i=0;i<64;i=i+1)tick(1,0,0,40'h5500000000+i);
  repeat(64)tick(0,1,0,0);
  if(full_dual<520 || single_dual<256 || count!=0)$fatal(1,"insufficient directed coverage");
  $display("PASS spare_vendor_eram checks=%0d full_dual=%0d single_dual=%0d",checks,full_dual,single_dual);$finish;
 end
 initial begin #1000000;$fatal(1,"RAM FIFO watchdog");end
endmodule
