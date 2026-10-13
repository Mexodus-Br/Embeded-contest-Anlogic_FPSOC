`timescale 1ns/1ps
module tb_gp_stress;
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

 integer produced=0,admitted=0,rejected=0,consumed=0,model_count=0,model_wr=0,model_rd=0;
 integer producer_seed=121212,rand_gap;
 reg producer_done=0,producer_enable=0;
 reg [255:0] model[0:7];reg [31:0] model_revision[0:7];
 wire take=push && (level<8 || rr);
 always @(posedge clk) if(collector_rst_n) begin
  if(rr && rv) begin
   if(data!==model[model_rd]) $fatal(1,"stress popped mixed/out of order record");
   model_rd=(model_rd+1)%8;consumed=consumed+1;
  end
  if(push) begin
   produced=produced+1;
   if(take) begin model[model_wr]=push_data;model_revision[model_wr]=rev;model_wr=(model_wr+1)%8;admitted=admitted+1;end
   else rejected=rejected+1;
  end
  case({take,rr && rv}) 2'b10:model_count=model_count+1;2'b01:model_count=model_count-1;endcase
  if(model_count<0 || model_count>8) $fatal(1,"model count");
 end
 always @(negedge collector_rst_n) begin model_count=0;model_wr=0;model_rd=0;end
 always @(negedge clk) if(collector_rst_n && model_count!=level) $fatal(1,"metadata/reference queue level");
 task consume_head;
  begin
   wr(`RG_REG_CAPTURE,1,15,0);rd(`RG_REG_CAPTURE_ID,0,id);read_record(rec);
   if(rec!==model[model_rd]) $fatal(1,"stress capture mixed");
   eq(`RG_REG_CAPTURE_REVISION,model_revision[model_rd]);wr(`RG_REG_CONSUME_ID,id,15,0);
  end
 endtask
 initial begin
  wait(producer_enable);producer_seed=seed^32'h1357;
  repeat(200) begin
   rand_gap=($random(producer_seed)&32'h7fffffff)%25+3;ticks(rand_gap);
   rev=1000+produced;push_data={8'd1,8'he1,8'h3a,8'd0,8'd0,8'd1,produced[31:0],64'd1,64'd2,48'd2};push=1;ticks(1);push=0;
  end
  producer_done=1;
 end
 initial begin
  ticks(5);rst_n=1;ticks(3);
  // Full exchange: 8 occupied, incoming tag and data accepted on consume edge.
  for(k=0;k<8;k=k+1) begin rev=10+k;put(k,0,8'h3a);end
  wr(`RG_REG_CAPTURE,1,15,0);rd(`RG_REG_CAPTURE_ID,0,id);read_record(rec);
  ticks(1);write_address({1'b0,`RG_BASE}+`RG_REG_CONSUME_ID);write_data(id,15);
  rev=99;push_data={8'd1,8'he0,8'h3a,8'd0,8'd0,8'd1,32'd99,64'd1,64'd2,48'd1};push=1;
  @(posedge clk);@(negedge clk);push=0;s_bready=1;@(posedge clk);@(negedge clk);s_bready=0;
  if(level!=8 || drop!=0) $fatal(1,"full simultaneous pop push");
  repeat(8) consume_head;
  producer_enable=1;
  while(!producer_done || rv) begin if(rv) consume_head;else ticks(1);end
  if(rejected==0 || drop!=rejected || admitted!=consumed || produced!=admitted+rejected) $fatal(1,"stress accounting");
  $display("STRESS produced=%0d admitted=%0d consumed=%0d dropped=%0d",produced,admitted,consumed,rejected);
  // Pending read crosses local reset, response held; old bitmap must not return.
  put(500,0,8'h3a);wr(`RG_REG_CAPTURE,1,15,0);rd(`RG_REG_CAPTURE_ID,0,oldid);
  ticks(1);s_araddr={1'b0,`RG_BASE}+`RG_REG_WORD0;s_arvalid=1;
  @(posedge clk);@(negedge clk);s_arvalid=0;wait(s_rvalid);v=s_rdata;
  wr(`RG_REG_LOCAL_RESET,1,15,0);ticks(3);
  if(!s_rvalid || s_rdata!==v || s_rresp!=0) $fatal(1,"reset canceled old AXI read response");
  s_rready=1;@(posedge clk);@(negedge clk);s_rready=0;
  eq(`RG_REG_CAPTURE_STATUS,0);eq(`RG_REG_GENERATION,1);wr(`RG_REG_CONSUME_ID,oldid,15,2);
  // Commit with stalled B while independent R reads updated generation.
  ticks(1);write_address({1'b0,`RG_BASE}+`RG_REG_LOCAL_RESET);write_data(1,15);
  wait(s_bvalid);rd(`RG_REG_GENERATION,0,v);if(v!=2 || !s_bvalid || s_bresp!=0) $fatal(1,"independent R/B ownership");
  s_bready=1;@(posedge clk);@(negedge clk);s_bready=0;eq(`RG_REG_GENERATION,2);
  $display("PASS GP stress full exchange, seeded producer/slow GP, reset with R/B backpressure");$finish;
 end
 initial begin #3000000;$fatal(1,"stress watchdog");end
endmodule
