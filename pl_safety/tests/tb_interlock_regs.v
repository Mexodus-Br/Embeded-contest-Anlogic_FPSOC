`timescale 1ns/1ps
`include "safety_defs.vh"
`include "interlock_defs.vh"
module tb_interlock_regs;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg [32:0] awaddr=0,araddr=0;reg [31:0] wdata=0;reg [3:0] wstrb=15;
 reg awvalid=0,wvalid=0,bready=0,arvalid=0,rready=0;
 wire awready,wready,bvalid,arready,rvalid;wire [1:0] bresp,rresp;wire [31:0] rdata;
 wire fire,wknown,rknown;wire [11:0] wo,ro;wire [31:0] wd,rd;wire [3:0] ws;wire [1:0] response;
 wire hrequest,crequest,srequest,irq,apply,open_owner,close_owner,feed,admission_pending;
 reg config_ready=1,open_ok=1,close_ok=1,hb_ok=1;
 reg [63:0] owner_id=64'h123456789abcdef0,last_seq=0;
 reg [1023:0] live=0;
 wire [2:0] axes;wire [31:0] feedback_us,watchdog_us;wire [63:0] hb_owner,hb_seq;
 wire cfg_pending;wire [2:0] committed_axes;
 wire [31:0] committed_feedback,committed_watchdog;
 integer checks=0,applies=0,feeds=0,opens=0,closes=0,hits=0,k;
 reg [31:0] answer,held;
 localparam [32:0] BASE={1'b0,`SAF_BASE};
 safety_regs #(.INTERLOCK_SUPPORT(1)) endpoint(
  .clk(clk),.rst_n(rst_n),.s_awaddr(awaddr),.s_araddr(araddr),.s_wdata(wdata),.s_wstrb(wstrb),
  .s_awvalid(awvalid),.s_wvalid(wvalid),.s_bready(bready),.s_arvalid(arvalid),.s_rready(rready),
  .s_awready(awready),.s_wready(wready),.s_bvalid(bvalid),.s_arready(arready),.s_rvalid(rvalid),
  .s_bresp(bresp),.s_rresp(rresp),.s_rdata(rdata),.config_hash(256'd0),.config_ok(1'b1),
  .live_snapshot(2048'd0),.causes(32'd0),.request_ok(1'b1),.clear_ok(1'b1),
  .home_done(1'b0),.home_cancelled(1'b0),.home_owner(1'b1),.pulse_safe(1'b0),.stopped(1'b0),
  .home_request(hrequest),.clear_request(crequest),.stop_request(srequest),.irq(irq),.command_admission_pending(admission_pending),
  .ext_write_fire(fire),.ext_write_offset(wo),.ext_read_offset(ro),.ext_write_data(wd),.ext_write_strobe(ws),
  .ext_write_known(wknown),.ext_read_known(rknown),.ext_write_response(response),.ext_read_data(rd));
 safety_interlock_regs ext(.clk(clk),.rst_n(rst_n),.write_fire(fire),.write_offset(wo),.write_data(wd),
  .write_strobe(ws),.read_offset(ro),.write_known(wknown),.read_known(rknown),.write_response(response),.read_data(rd),
  .config_ready(config_ready),.owner_open_ok(open_ok),.owner_close_ok(close_ok),.heartbeat_ok(hb_ok),
  .owner_id(owner_id),.last_sequence(last_seq),.first_time(64'd0),.causes(32'd0),.first_cause(32'd0),.status(32'd0),
  .active_axes(3'd7),.active_feedback_us(32'd2000000),.active_watchdog_us(32'd2000000),.live_snapshot(live),
  .config_apply(apply),.config_pending(cfg_pending),.committed_axes(committed_axes),
  .committed_feedback_us(committed_feedback),.committed_watchdog_us(committed_watchdog),
  .owner_open(open_owner),.owner_close(close_owner),.heartbeat_commit(feed),
  .config_axes(axes),.config_feedback_us(feedback_us),.config_watchdog_us(watchdog_us),
  .heartbeat_owner(hb_owner),.heartbeat_sequence(hb_seq));
 always @(posedge clk)if(rst_n)begin
  if(apply)applies=applies+1;if(feed)feeds=feeds+1;if(open_owner)opens=opens+1;if(close_owner)closes=closes+1;
  if(hrequest)hits=hits+1;
 end
 // Observe the actual AW/W side-effect edge, independently of B consumption.
 always @(posedge clk)if(rst_n && fire && wo==`SI_REG_CONFIG_COMMIT && response==0 && ext.config_txn!=ext.accepted_txn)begin
  check(!apply,"configuration not applied on acceptance edge");
  #1;
  check(cfg_pending && apply && ext.accepted_txn==1 && ext.applied_txn==0,"accepted distinct from applied");
  check(committed_axes==3 && committed_feedback==1000000 && committed_watchdog==3000000,"whole captured payload");
  @(posedge clk);#1;
  check(!cfg_pending && !apply && ext.applied_txn==1,"application exactly next edge");
 end
 task check;input condition;input [799:0] message;
  begin checks=checks+1;if(!condition)$fatal(1,"%s",message);end
 endtask
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task write;
  input [32:0] address;input [31:0] data;input [3:0] strobes;input [1:0] expected;
  input integer order,stall;
  begin
   awaddr=address;wdata=data;wstrb=strobes;
   if(order==0)begin awvalid=1;wvalid=1;tick;awvalid=0;wvalid=0;end
   else if(order==1)begin
    awvalid=1;tick;awvalid=0;
    if(address==BASE+`SAF_REGISTERS_SUBMIT)
     check(admission_pending && !hrequest,"captured HOME submit fences configuration before W/txn validation");
    repeat(3)tick;wvalid=1;tick;wvalid=0;
   end
   else begin wvalid=1;tick;wvalid=0;repeat(3)tick;awvalid=1;tick;awvalid=0;end
   while(!bvalid)tick;
   check(bresp==expected,"B response");
   repeat(stall)begin tick;check(bvalid && bresp==expected && !awready && !wready,"B stable/backpressure");end
   bready=1;tick;bready=0;tick;
  end
 endtask
 task read;
  input [32:0] address;input [1:0] expected;input integer stall;
  begin
   araddr=address;arvalid=1;tick;arvalid=0;while(!rvalid)tick;
   held=rdata;check(rresp==expected,"R response");
   repeat(stall)begin live=live+1;tick;check(rvalid && rdata==held && rresp==expected,"R stable/backpressure");end
   answer=rdata;rready=1;tick;rready=0;tick;
  end
 endtask
 task words;input [63:0] owner,seq;
  begin
   write(BASE+`SI_REG_HEARTBEAT_OWNER_LO,owner[31:0],15,0,0,0);
   write(BASE+`SI_REG_HEARTBEAT_OWNER_HI,owner[63:32],15,0,1,0);
   write(BASE+`SI_REG_HEARTBEAT_SEQ_LO,seq[31:0],15,0,2,0);
   write(BASE+`SI_REG_HEARTBEAT_SEQ_HI,seq[63:32],15,0,0,0);
  end
 endtask
 initial begin
  tick;rst_n=1;tick;
  read(BASE+4,0,3);check(answer==`SI_PROFILE,"SAF2 explicit identity");
  write(BASE+`SAF_REGISTERS_OPCODE,1,15,0,0,0);
  write(BASE+`SAF_REGISTERS_TXN,1,15,0,1,0);
  write(BASE+`SAF_REGISTERS_SUBMIT,1,15,0,2,0);check(hits==1,"HOME mailbox busy");
  write(BASE+`SAF_REGISTERS_SUBMIT,1,15,0,1,0);check(hits==1,"replayed HOME remains idempotent");
  write(BASE+`SI_REG_OWNER_OPEN,1,15,0,0,4);check(opens==1,"open only once during B stall");
  write(BASE+`SI_REG_HEARTBEAT_COMMIT,1,15,2,1,0);check(feeds==0,"torn feed rejected");
  words(owner_id,64'h123456789);
  write(BASE+`SI_REG_HEARTBEAT_COMMIT,1,15,0,2,7);
  check(feeds==1 && hb_owner==owner_id && hb_seq==64'h123456789,"atomic feed independent of HOME busy");
  write(BASE+`SI_REG_HEARTBEAT_COMMIT,1,15,2,0,0);check(feeds==1,"no repeat without rewrite");
  words(owner_id,2);hb_ok=0;write(BASE+`SI_REG_HEARTBEAT_COMMIT,1,15,2,1,0);hb_ok=1;
  write(BASE+`SI_REG_HEARTBEAT_COMMIT,1,7,2,1,0);check(feeds==1,"illegal payload/strobe never feeds");
  write(BASE+`SI_REG_HEARTBEAT_COMMIT+33'h100000000,1,15,3,0,0);
  check(feeds==1,"A33 alias cannot feed");
  write(BASE+`SI_REG_HEARTBEAT_COMMIT+1,1,15,2,0,0);check(feeds==1,"unaligned cannot feed");
  write(BASE+`SI_REG_CONFIG_TXN,1,15,0,0,0);
  write(BASE+`SI_REG_CONFIG_COMMIT,1,15,2,0,0);check(applies==0,"torn configuration rejected");
  write(BASE+`SI_REG_SHADOW_AXES,3,15,0,0,0);
  write(BASE+`SI_REG_SHADOW_FEEDBACK_US,1000000,15,0,1,0);
  write(BASE+`SI_REG_SHADOW_WATCHDOG_US,3000000,15,0,2,0);
  config_ready=0;write(BASE+`SI_REG_CONFIG_COMMIT,1,15,2,0,0);check(applies==0,"busy rejects config");
  config_ready=1;write(BASE+`SI_REG_CONFIG_COMMIT,1,15,0,2,5);check(applies==1,"atomic config once");
  write(BASE+`SI_REG_CONFIG_COMMIT,1,15,0,0,0);check(applies==1,"duplicate config idempotent");
  write(BASE+`SI_REG_SHADOW_FEEDBACK_US,999999,15,0,0,0);
  write(BASE+`SI_REG_CONFIG_COMMIT,1,15,2,0,0);check(applies==1,"range/payload cannot change active config");
  live=1024'h123456789abcdef0;
  write(BASE+`SI_REG_SNAP_REQ,1,15,0,1,0);live=0;
  read(BASE+`SI_SNAPSHOT_BASE,0,5);check(answer==32'h9abcdef0,"snapshot low held");
  read(BASE+`SI_SNAPSHOT_BASE+4,0,3);check(answer==32'h12345678,"snapshot high same capture");
  write(BASE+`SI_REG_SNAP_REQ,1,15,2,0,0);
  words(owner_id,4);close_ok=0;write(BASE+`SI_REG_OWNER_CLOSE,1,15,2,0,0);
  close_ok=1;write(BASE+`SI_REG_OWNER_CLOSE,1,15,0,0,0);check(closes==1,"handoff explicit and qualified");
  $display("PASS interlock_regs checks=%0d",checks);$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog testbench timeout");end
endmodule
