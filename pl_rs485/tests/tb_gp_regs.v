`timescale 1ns/1ps
module tb_gp_regs;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg [63:0] time_us=64'h12345678ffffff00;
 always @(posedge clk) time_us<=time_us+1;
 `include "gp_bfm.vh"
 wire run,collector_rst_n,cv,rr,irq;
 reg cr=1,ca=0,ce=0,busy=0;reg [7:0] cerr=0;
 wire [159:0] cp;wire [4:0] cm;
 reg [159:0] ap=0;reg [4:0] am=0;reg [31:0] rev=1,seq=0,load=0;
 wire rv;wire [255:0] data;reg push=0;reg [255:0] push_data=0;
 wire [31:0] level,drop;reg [31:0] ok=0,err=0,ignored=0,be=0;reg [9:0] offline=0;
 reg [7999:0] tasks=0;reg [1279:0] nodes=0;
 record_fifo #(.DEPTH(8)) fifo(clk,collector_rst_n,push,push_data,rr,rv,data,drop,level);
 rs485_gp_regs dut(.clk(clk),.rst_n(rst_n),.time_us(time_us),
 .s_awaddr(s_awaddr),.s_araddr(s_araddr),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
 .s_awvalid(s_awvalid),.s_wvalid(s_wvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_rready(s_rready),
 .s_awready(s_awready),.s_wready(s_wready),.s_bvalid(s_bvalid),.s_arready(s_arready),.s_rvalid(s_rvalid),.s_bresp(s_bresp),.s_rresp(s_rresp),.s_rdata(s_rdata),.irq(irq),
 .run(run),.collector_rst_n(collector_rst_n),.cfg_valid(cv),.cfg_ready(cr),.cfg_applied(ca),.cfg_rejected(ce),.cfg_error(cerr),.cfg_period_us(cp),.cfg_mask(cm),
 .active_period_us(ap),.active_mask(am),.cfg_revision(rev),.cfg_apply_sequence(seq),.config_load_ppm(load),.busy(busy),
 .record_valid(rv),.record_data(data),.record_ready(rr),.fifo_level(level),.dropped(drop),.accepted(ok),.errors(err),.ignored_rx(ignored),.bus_busy_events(be),.node_offline(offline),
 .observe_push(push),.observe_data(push_data),.observe_tasks(tasks),.observe_nodes(nodes));
 integer pops=0,configs=0,k;reg [159:0] captured;reg [4:0] captured_mask;
 always @(posedge clk) begin
  if(rr && rv) pops=pops+1;
  if(cv && cr) begin configs=configs+1;captured=cp;captured_mask=cm;cr<=0;end
  if(collector_rst_n) begin
   tasks[31:0]<=tasks[31:0]+1;tasks[63:32]<=tasks[31:0]+1;
   nodes[95:32]<=time_us;
  end
 end
 task apply;input reject;input [7:0] reason;
  begin ticks(1);cerr=reason;ca=!reject;ce=reject;if(!reject) begin rev=rev+1;ap=captured;am=captured_mask;end
   ticks(1);ca=0;ce=0;cr=1;ticks(2);end
 endtask
 task put;input [31:0] id;input [7:0] st,q;
  begin ticks(1);push_data={8'd1,8'he0,q,st,8'd0,8'd1,id,64'd100,64'd200,48'd1};push=1;ticks(1);push=0;end
 endtask
 reg [31:0] v,id,oldid,before_pops,lo,hi,sv;reg [255:0] rec,first;
 reg [63:0] sampled;
 initial begin
  ticks(5);rst_n=1;ticks(3);
  eq(`RG_REG_VERSION,1);eq(`RG_REG_PROFILE,`RG_PROFILE);eq(`RG_REG_RUN,0);
  wr_abs(33'h180700000,0,15,1,3,3);rd_abs(33'h180700000,2,3,v);
  wr(3,0,15,2);rd(1,2,v);wr(`RG_REG_VERSION,2,15,2);rd(`RG_REG_CAPTURE,2,v);rd(32'h120,2,v);
  wr(`RG_REG_RUN,1,1,0);eq(`RG_REG_RUN,1);wr(`RG_REG_RUN,256,2,2);eq(`RG_REG_RUN,1);
  wr(`RG_REG_RUN,0,0,0);eq(`RG_REG_RUN,1);wr(`RG_REG_RUN,0,15,0);
  wr(`RG_REG_SHADOW_PERIOD0,32'h12345678,15,0);wr(`RG_REG_SHADOW_PERIOD0,32'habcdef00,2,0);eq(`RG_REG_SHADOW_PERIOD0,32'h1234ef78);
  wr(`RG_REG_SHADOW_MASK,32'h20,15,2);wr(`RG_REG_SHADOW_MASK,5,15,0);wr(`RG_REG_TXN_ID,1,15,0);
  wr(`RG_REG_CFG_SUBMIT,1,1,2);wr(`RG_REG_CFG_SUBMIT,1,15,0);wait(configs==1);
  eq(`RG_REG_CFG_STATE,`RG_CFG_ACCEPTED|`RG_CFG_PENDING);
  wr(`RG_REG_CFG_SUBMIT,1,15,0);if(configs!=1) $fatal(1,"duplicate pending submit");
  wr(`RG_REG_SHADOW_PERIOD0,999,15,0);if(captured[31:0]!=32'h1234ef78) $fatal(1,"atomic payload");
  wr(`RG_REG_CFG_SUBMIT,1,15,2);wr(`RG_REG_TXN_ID,2,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,2);
  apply(0,0);eq(`RG_REG_CFG_STATE,5);eq(`RG_REG_CURRENT_PERIOD0,32'h1234ef78);
  wr(`RG_REG_CFG_SUBMIT,1,15,0);wait(configs==2);apply(1,`RG_CFG_ERR_LOAD);eq(`RG_REG_CFG_STATE,9);eq(`RG_REG_CFG_ERROR,2);
  wr(`RG_REG_CFG_SUBMIT,1,15,0);if(configs!=2) $fatal(1,"duplicate terminal submit");
  wr(`RG_REG_TXN_ID,1,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,2);
  wr(`RG_REG_CAPTURE,1,15,2);rd(`RG_REG_WORD0,2,v);
  put(11,0,8'h3e);first=push_data;wr(`RG_REG_CAPTURE,1,15,0);rd(`RG_REG_CAPTURE_ID,0,id);eq(`RG_REG_CAPTURE_REVISION,2);
  wr(`RG_REG_CAPTURE,1,15,0);eq(`RG_REG_CAPTURE_ID,id);wr(`RG_REG_CONSUME_ID,id,15,2);
  rev=3;put(12,0,8'h30);read_record(rec);if(rec!==first) $fatal(1,"mixed record");
  eq(`RG_REG_CAPTURE_STATUS,32'hff01);before_pops=pops;wr(`RG_REG_CONSUME_ID,id,15,0);
  wr(`RG_REG_CONSUME_ID,id,15,0);if(pops!=before_pops+1) $fatal(1,"duplicate pop");
  wr(`RG_REG_CAPTURE,1,15,0);eq(`RG_REG_CAPTURE_REVISION,3);rd(`RG_REG_CAPTURE_ID,0,oldid);
  rd(`RG_REG_WORD0,0,v);wr(`RG_REG_ABANDON_ID,oldid,15,0);eq(`RG_REG_FIFO_LEVEL,1);
  wr(`RG_REG_CAPTURE,1,15,0);rd(`RG_REG_CAPTURE_ID,0,id);if(id<=oldid) $fatal(1,"capture reuse");
  wr(`RG_REG_CONSUME_ID,oldid,15,2);read_record(rec);wr(`RG_REG_CONSUME_ID,id,15,0);
  // Full FIFO, immutable tags across config changes, saturated drop rule.
  for(k=0;k<10;k=k+1) begin rev=100+k;put(k,0,8'h30);end
  eq(`RG_REG_FIFO_LEVEL,8);if(drop!=2) $fatal(1,"full drop");
  for(k=0;k<8;k=k+1) begin
   wr(`RG_REG_CAPTURE,1,15,0);eq(`RG_REG_CAPTURE_REVISION,100+k);rd(`RG_REG_CAPTURE_ID,0,id);read_record(rec);
   if(rec[207:176]!=k) $fatal(1,"FIFO order");wr(`RG_REG_CONSUME_ID,id,15,0);
  end
  wr(`RG_REG_IRQ_MASK,127,15,0);if(!irq) $fatal(1,"masked event retained");
  wr(`RG_REG_IRQ_PENDING,127,1,2);wr(`RG_REG_IRQ_PENDING,127,15,0);ticks(1);if(irq) $fatal(1,"clear after drain");
  put(77,1,8'h30);wr(`RG_REG_IRQ_PENDING,127,15,0);rd(`RG_REG_IRQ_PENDING,0,v);if(!(v&1)) $fatal(1,"persistent DATA");
  // Event and W1C exactly same edge: set wins, independently classified.
  ticks(1);write_address({1'b0,`RG_BASE}+`RG_REG_IRQ_PENDING);write_data(127,15);
  push=1;push_data[231:224]=6;@(posedge clk);@(negedge clk);push=0;s_bready=1;@(posedge clk);@(negedge clk);s_bready=0;
  rd(`RG_REG_IRQ_PENDING,0,v);if(!(v & `RG_IRQ_BUS_DIAGNOSTIC)) $fatal(1,"IRQ set clear race");
  wr(`RG_REG_SNAP_REQ_ID,1,15,0);
  // Snapshot simultaneous dynamic values checked against same-edge input model.
  ticks(1);write_address({1'b0,`RG_BASE}+`RG_REG_SNAP_SUBMIT);write_data(1,15);sampled=time_us;
  @(posedge clk);sv=tasks[31:0];@(negedge clk);s_bready=1;@(posedge clk);@(negedge clk);s_bready=0;
  rd(`RG_SNAPSHOT_BASE+`RG_SNAP_TIME_LO*4,0,lo);rd(`RG_SNAPSHOT_BASE+`RG_SNAP_TIME_HI*4,0,hi);
  if({hi,lo}!==sampled) $fatal(1,"snapshot time");eq(`RG_TASK_BASE,sv);eq(`RG_TASK_BASE+4,sv);
  eq(`RG_NODE_BASE+4,sampled[31:0]-1);
  rd(`RG_NODE_BASE+8,0,v);if(v!==((sampled-1)>>32)) $fatal(1,"node time torn");
  eq(`RG_NODE_BASE+3*16,0);eq(`RG_TASK_BASE+15*32,0);
  wr(`RG_REG_SNAP_SUBMIT,1,15,0);eq(`RG_TASK_BASE,sv);
  wr(`RG_REG_SNAP_REQ_ID,2,15,0);wr(`RG_REG_SNAP_SUBMIT,1,15,0);rd(`RG_TASK_BASE,0,v);if(v<=sv) $fatal(1,"new snapshot");
  busy=1;wr(`RG_REG_LOCAL_RESET,1,15,2);busy=0;cr=0;wr(`RG_REG_LOCAL_RESET,1,15,2);cr=1;
  wr(`RG_REG_RUN,1,15,0);wr(`RG_REG_LOCAL_RESET,1,15,2);wr(`RG_REG_RUN,0,15,0);
  wr(`RG_REG_CAPTURE,1,15,0);rd(`RG_REG_CAPTURE_ID,0,oldid);
  wr(`RG_REG_LOCAL_RESET,1,15,0);ticks(5);eq(`RG_REG_GENERATION,1);eq(`RG_REG_CAPTURE_STATUS,0);eq(`RG_REG_FIFO_LEVEL,0);eq(`RG_REG_SNAP_STATUS,0);eq(`RG_REG_IRQ_MASK,127);
  if(time_us<sampled) $fatal(1,"time reset");wr(`RG_REG_CONSUME_ID,oldid,15,2);wr(`RG_REG_SNAP_SUBMIT,1,15,2);
  wr(`RG_REG_CFG_SUBMIT,1,15,2);put(90,0,8'h30);wr(`RG_REG_CAPTURE,1,15,0);rd(`RG_REG_CAPTURE_ID,0,id);if(id<=oldid) $fatal(1,"ID reset");
  force dut.cap_watermark=32'hffffffff;wr(`RG_REG_ABANDON_ID,id,15,0);wr(`RG_REG_CAPTURE,1,15,2);release dut.cap_watermark;
  force dut.generation=32'hffffffff;wr(`RG_REG_LOCAL_RESET,1,15,2);release dut.generation;
  $display("PASS GP regs checks=%0d pops=%0d seeded AXI/atomic/FIFO/IRQ/reset",checks,pops);$finish;
 end
 initial begin #3000000;$fatal(1,"GP watchdog");end
endmodule
