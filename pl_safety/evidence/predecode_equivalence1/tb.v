`timescale 1ns/1ps
`include "safety_defs.vh"
module tb_regs_equivalence;
reg clk=0;
reg rst_n=0;
reg [32:0] s_awaddr=0;
reg [32:0] s_araddr=0;
reg [31:0] s_wdata=0;
reg [3:0] s_wstrb=0;
reg s_awvalid=0;
reg s_wvalid=0;
reg s_bready=0;
reg s_arvalid=0;
reg s_rready=0;
reg [255:0] config_hash=0;
reg config_ok=0;
reg [2047:0] live_snapshot=0;
reg [31:0] causes=0;
reg request_ok=0;
reg clear_ok=0;
reg home_done=0;
reg home_cancelled=0;
reg home_owner=0;
reg pulse_safe=0;
reg stopped=0;
wire s_awready;
wire s_wready;
wire s_arready;
wire s_bvalid;
wire s_rvalid;
wire [1:0] s_bresp;
wire [1:0] s_rresp;
wire [31:0] s_rdata;
wire home_request;
wire clear_request;
wire stop_request;
wire irq;
safety_regs dut(.clk(clk),.rst_n(rst_n),.s_awaddr(s_awaddr),.s_araddr(s_araddr),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_awvalid(s_awvalid),.s_wvalid(s_wvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_rready(s_rready),.config_hash(config_hash),.config_ok(config_ok),.live_snapshot(live_snapshot),.causes(causes),.request_ok(request_ok),.clear_ok(clear_ok),.home_done(home_done),.home_cancelled(home_cancelled),.home_owner(home_owner),.pulse_safe(pulse_safe),.stopped(stopped),.s_awready(s_awready),.s_wready(s_wready),.s_arready(s_arready),.s_bvalid(s_bvalid),.s_rvalid(s_rvalid),.s_bresp(s_bresp),.s_rresp(s_rresp),.s_rdata(s_rdata),.home_request(home_request),.clear_request(clear_request),.stop_request(stop_request),.irq(irq));
wire s_awready_ref;
wire s_wready_ref;
wire s_arready_ref;
wire s_bvalid_ref;
wire s_rvalid_ref;
wire [1:0] s_bresp_ref;
wire [1:0] s_rresp_ref;
wire [31:0] s_rdata_ref;
wire home_request_ref;
wire clear_request_ref;
wire stop_request_ref;
wire irq_ref;
baseline_regs reference(.clk(clk),.rst_n(rst_n),.s_awaddr(s_awaddr),.s_araddr(s_araddr),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_awvalid(s_awvalid),.s_wvalid(s_wvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_rready(s_rready),.config_hash(config_hash),.config_ok(config_ok),.live_snapshot(live_snapshot),.causes(causes),.request_ok(request_ok),.clear_ok(clear_ok),.home_done(home_done),.home_cancelled(home_cancelled),.home_owner(home_owner),.pulse_safe(pulse_safe),.stopped(stopped),.s_awready(s_awready_ref),.s_wready(s_wready_ref),.s_arready(s_arready_ref),.s_bvalid(s_bvalid_ref),.s_rvalid(s_rvalid_ref),.s_bresp(s_bresp_ref),.s_rresp(s_rresp_ref),.s_rdata(s_rdata_ref),.home_request(home_request_ref),.clear_request(clear_request_ref),.stop_request(stop_request_ref),.irq(irq_ref));

always #5 clk=~clk;
integer checks=0,cycles=0,seed=32'h71a9632,randomize_live=0;
always @(posedge clk)begin
 cycles=cycles+1;if(cycles>200000)$fatal(1,"watchdog");
 #1;if(rst_n)begin
  checks=checks+1;
  if({s_awready,s_wready,s_arready,s_bvalid,s_rvalid,s_bresp,s_rresp,s_rdata,home_request,clear_request,stop_request,irq} !== {s_awready_ref,s_wready_ref,s_arready_ref,s_bvalid_ref,s_rvalid_ref,s_bresp_ref,s_rresp_ref,s_rdata_ref,home_request_ref,clear_request_ref,stop_request_ref,irq_ref}) $fatal(1,"register cycle equivalence failed cycle=%0d",cycles);
 end
end
always @(negedge clk)begin
 if(randomize_live)begin
  live_snapshot=live_snapshot+2048'd1;
  causes=$random(seed)&15;
  home_done=cycles%7==0;home_cancelled=cycles%11==0;
  home_owner=cycles%5!=0;pulse_safe=cycles%3!=0;stopped=cycles%13==0;
  request_ok=cycles%4!=0;clear_ok=cycles%3!=0;
 end
 #2;if(rst_n)begin
  checks=checks+1;
  if({s_awready,s_wready,s_arready,s_bvalid,s_rvalid,s_bresp,s_rresp,s_rdata,home_request,clear_request,stop_request,irq} !== {s_awready_ref,s_wready_ref,s_arready_ref,s_bvalid_ref,s_rvalid_ref,s_bresp_ref,s_rresp_ref,s_rdata_ref,home_request_ref,clear_request_ref,stop_request_ref,irq_ref}) $fatal(1,"register combinational equivalence failed");
 end
end
task write;
 input [32:0] address;input [31:0] data;input [3:0] strobe;input integer adelay,wdelay;
 begin
  @(negedge clk);
  fork
   begin
    repeat(adelay)@(negedge clk);s_awaddr=address;s_awvalid=1;
    @(posedge clk);while(!s_awready)@(posedge clk);@(negedge clk);s_awvalid=0;
   end
   begin
    repeat(wdelay)@(negedge clk);s_wdata=data;s_wstrb=strobe;s_wvalid=1;
    @(posedge clk);while(!s_wready)@(posedge clk);@(negedge clk);s_wvalid=0;
   end
  join
  repeat(3)@(negedge clk);s_bready=1;
  @(posedge clk);while(!s_bvalid)@(posedge clk);@(negedge clk);s_bready=0;
 end
endtask
task read;
 input [32:0] address;
 begin
  @(negedge clk);s_araddr=address;s_arvalid=1;
  @(posedge clk);while(!s_arready)@(posedge clk);@(negedge clk);s_arvalid=0;
  repeat(4)@(negedge clk);s_rready=1;
  @(posedge clk);while(!s_rvalid)@(posedge clk);@(negedge clk);s_rready=0;
 end
endtask
reg [11:0] offsets[0:9];integer i;reg [31:0] choice,datum;reg [32:0] address;
initial begin
 offsets[0]=`SAF_REGISTERS_OPCODE;offsets[1]=`SAF_REGISTERS_ARG;offsets[2]=`SAF_REGISTERS_TXN;
 offsets[3]=`SAF_REGISTERS_SUBMIT;offsets[4]=`SAF_REGISTERS_STOP;offsets[5]=`SAF_REGISTERS_IRQ_PENDING;
 offsets[6]=`SAF_REGISTERS_IRQ_MASK;offsets[7]=`SAF_REGISTERS_SNAP_REQ;offsets[8]=0;offsets[9]=12'hffc;
 repeat(3)@(negedge clk);rst_n=1;config_ok=1;request_ok=1;clear_ok=1;pulse_safe=1;
 write({1'b0,`SAF_BASE}+`SAF_REGISTERS_OPCODE,1,15,0,3);
 write({1'b0,`SAF_BASE}+`SAF_REGISTERS_TXN,1,15,3,0);
 write({1'b0,`SAF_BASE}+`SAF_REGISTERS_SUBMIT,1,15,0,0);
 write({1'b0,`SAF_BASE}+`SAF_REGISTERS_SUBMIT,1,15,2,0);
 home_done=1;repeat(2)@(negedge clk);home_done=0;
 for(i=0;i<16;i=i+1)begin
  write({1'b0,`SAF_BASE}+`SAF_REGISTERS_STOP,1,i,0,i%4);
  write({1'b0,`SAF_BASE}+`SAF_REGISTERS_STOP,i,15,i%4,0);
 end
 randomize_live=1;
 for(i=0;i<3000;i=i+1)begin
  choice=$random(seed);address={1'b0,`SAF_BASE}+offsets[choice%10];
  if(i%11==0)address=address+1;
  if(i%17==0)address[32]=1;
  datum=$random(seed);if(i%3==0)datum=1;else if(i%3==1)datum=datum%8;
  write(address,datum,i%9==0 ? 4'd7:4'd15,i%4,(i+2)%4);
  if(i%4==0)read({1'b0,`SAF_BASE}+(i%2==0 ? `SAF_SNAPSHOT_BASE:12'h02c));
 end
 $display("PASS register equivalence checks=%0d cycles=%0d writes=3036 reads=750",checks,cycles);
 $finish;
end
endmodule
