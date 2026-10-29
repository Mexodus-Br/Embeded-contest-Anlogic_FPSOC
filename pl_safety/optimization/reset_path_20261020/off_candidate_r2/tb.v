`timescale 1ns/1ps
module tb_interlock_rs485;
`include "interlock_gp_defs.vh"
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
 reg safe_idle=1,safe_off=1;
 wire effective_run,stop_commit,local_reset,pending_config,applied_config;
 rs485_gp_regs #(.INTERLOCK_SUPPORT(1)) dut(
 .interlock_idle(safe_idle),.interlock_idle_off(safe_off),.interlock_run(effective_run),.interlock_stop_commit(stop_commit),
 .interlock_reset(local_reset),.interlock_config_pending(pending_config),.interlock_config_change(applied_config),.clk(clk),.rst_n(rst_n),.time_us(time_us),
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

 integer si,vi;reg [31:0] trial,lane_mask,expected_word;
 always @(posedge clk)if(rst_n && dut.write_fire && dut.wa[11:0]==`RG_REG_RUN &&
   dut.effective_run_write>1)begin
  if(effective_run!==run || stop_commit)$fatal(1,"rejected RUN write must not suspend/restart monitor");
 end
 // Differential oracle for the original full address/merge predicate. This
 // verifies predecoding across independent AW/W capture and all WSTRB masks.
 always @(posedge clk)if(rst_n && dut.write_fire)begin
  if(effective_run!==run)$fatal(1,"monitor RUN must equal actual collector RUN");
  if((effective_run && !stop_commit) !== (run && !(dut.wa=={1'b0,`RG_BASE}+`RG_REG_RUN &&
       dut.ws!=0 && dut.effective_run_write==0 && dut.reset_count==0 && safe_idle)))
   $fatal(1,"RUN clear must take effect on the original accepted write edge");
 end
 initial begin
  ticks(5);rst_n=1;ticks(3);
  eq(`RG_REG_PROFILE,`RGI_PROFILE);eq(`RG_REG_VERSION,2);eq(`RG_REG_CAPS,63);
  wr(`RG_REG_RUN,1,15,2);eq(`RG_REG_RUN,0);
  ap={32'd1000000,128'd0};am=16;
  busy=1;wr(`RG_REG_RUN,1,15,2);eq(`RG_REG_RUN,0);busy=0;
  wr(`RG_REG_RUN,1,15,0);eq(`RG_REG_RUN,1);
  wr(`RG_REG_RUN,2,15,2);eq(`RG_REG_RUN,1);
  wr(`RG_REG_RUN,256,2,2);eq(`RG_REG_RUN,1);
  wr(`RG_REG_RUN,0,0,0);eq(`RG_REG_RUN,1);
  for(si=0;si<16;si=si+1)for(vi=0;vi<8;vi=vi+1)begin
   wr(`RG_REG_RUN,1,15,0);
   case(vi)
    0:trial=0;1:trial=1;2:trial=2;3:trial=32'h100;
    4:trial=32'h10000;5:trial=32'h1000000;6:trial=32'hffffffff;7:trial=32'h80000001;
   endcase
   lane_mask={{8{si[3]}},{8{si[2]}},{8{si[1]}},{8{si[0]}}};
   expected_word=(trial & lane_mask) | (32'd1 & ~lane_mask);
   wr(`RG_REG_RUN,trial,si[3:0],expected_word>1 ? 2:0);
   eq(`RG_REG_RUN,expected_word>1 ? 1:expected_word);
  end
  safe_idle=0;safe_off=0;
  wr(`RG_REG_RUN,0,15,2);eq(`RG_REG_RUN,1);
  wr(`RG_REG_LOCAL_RESET,1,15,2);
  wr(`RG_REG_SHADOW_PERIOD4,1000000,15,0);wr(`RG_REG_SHADOW_MASK,16,15,0);
  wr(`RG_REG_TXN_ID,1,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,2);
  if(configs!=0)$fatal(1,"motion-busy config bypass");
  safe_idle=1;
  wr(`RG_REG_RUN,0,15,0);wr(`RG_REG_LOCAL_RESET,1,15,2);
  wr(`RG_REG_SHADOW_MASK,0,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,2);
  wr(`RG_REG_SHADOW_MASK,16,15,0);wr(`RG_REG_SHADOW_PERIOD4,0,15,0);
  wr(`RG_REG_CFG_SUBMIT,1,15,2);
  wr(`RG_REG_SHADOW_PERIOD4,1000000,15,0);wr(`RG_REG_CFG_SUBMIT,1,15,0);
  if(configs!=1 || captured_mask!=16 || captured[128+:32]!=1000000)$fatal(1,"atomic guarded config capture");
  if(!pending_config)$fatal(1,"pending application must block motion qualification");
  apply(0,0);if(pending_config)$fatal(1,"application pending did not retire");
  safe_off=1;wr(`RG_REG_LOCAL_RESET,1,15,0);ticks(5);
  if(run || dut.generation!=1)$fatal(1,"local reset retains RUN off and new generation");

 // Repeated OFF commands, idle qualification changes and independent AW/W
 // capture across all strobes retain their existing commit and response edge.
 for(si=0;si<16;si=si+1)begin
  safe_idle=1;safe_off=1;wr(`RG_REG_LOCAL_RESET,1,15,0);ticks(4);
  ap={32'd1000000,128'd0};am=16;cr=1;
  wr(`RG_REG_RUN,1,15,0);safe_idle=0;wr(`RG_REG_RUN,0,si[3:0],si==0 ? 0:2);
  safe_idle=1;wr(`RG_REG_RUN,0,15,0);ticks(2);
 end
 // Inductive boundary proof: arbitrary mailbox/reset states with consistent
 // captured addresses and data, then let the real RTL execute one edge.
 // Only the induction start is injected; the projection is never repaired
 // after the edge being checked. Covers B stalls, reset countdown and new
 // independent AW/W captures, including LOCAL_RESET commit priority.
 for(si=0;si<65536;si=si+1)begin
  @(negedge clk);
  dut.ah=si[0];reference.ah=si[0];dut.wh=si[1];reference.wh=si[1];
  dut.s_bvalid=si[2];reference.s_bvalid=si[2];
  dut.reset_count=si[4:3];reference.reset_count=si[4:3];
  dut.aw_run=si[5];reference.aw_run=si[5];
  dut.aw_reset=!si[5];reference.aw_reset=!si[5];
  dut.wa={1'b0,`RG_BASE}+(si[5] ? `RG_REG_RUN:`RG_REG_LOCAL_RESET);reference.wa=dut.wa;
  dut.wd=si[6] ? 0:1;reference.wd=dut.wd;dut.ws=15;reference.ws=15;
  dut.w_run_clear=si[6];reference.w_run_clear=si[6];
  dut.w_reset=!si[6];reference.w_reset=!si[6];
  safe_idle=si[7];safe_off=si[8];s_awvalid=si[9];s_wvalid=si[10];s_bready=si[11];
  s_awaddr={1'b0,`RG_BASE}+(si[12] ? `RG_REG_RUN:`RG_REG_LOCAL_RESET);
  s_wdata=si[13] ? 0:1;s_wstrb=si[15:14]==0 ? 0:15;
  #1;dut.off_request_q=dut.write_fire && dut.aw_run && dut.w_run_clear && dut.reset_count==0;
  @(posedge clk);#2;
 end
 @(negedge clk);s_awvalid=0;s_wvalid=0;s_bready=0;
  $display("PASS interlock_rs485_guard checks=%0d",checks);$display("PROJECTION_CHECKS %0d",projection_checks);$finish;
 end
 initial begin #1000000;$fatal(1,"guard test timeout");end
wire  effective_run_ref;
wire  stop_commit_ref;
wire  local_reset_ref;
wire  pending_config_ref;
wire  applied_config_ref;
wire  s_awready_ref;
wire  s_wready_ref;
wire  s_bvalid_ref;
wire  s_arready_ref;
wire  s_rvalid_ref;
wire [1:0] s_bresp_ref;
wire [1:0] s_rresp_ref;
wire [31:0] s_rdata_ref;
wire  irq_ref;
wire  run_ref;
wire  collector_rst_n_ref;
wire  cv_ref;
wire [159:0] cp_ref;
wire [4:0] cm_ref;
wire  rr_ref;
ref_rs485_gp_regs #(.INTERLOCK_SUPPORT(1)) reference(
 .interlock_idle(safe_idle),.interlock_idle_off(safe_off),.interlock_run(effective_run_ref),.interlock_stop_commit(stop_commit_ref),
 .interlock_reset(local_reset_ref),.interlock_config_pending(pending_config_ref),.interlock_config_change(applied_config_ref),.clk(clk),.rst_n(rst_n),.time_us(time_us),
 .s_awaddr(s_awaddr),.s_araddr(s_araddr),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
 .s_awvalid(s_awvalid),.s_wvalid(s_wvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_rready(s_rready),
 .s_awready(s_awready_ref),.s_wready(s_wready_ref),.s_bvalid(s_bvalid_ref),.s_arready(s_arready_ref),.s_rvalid(s_rvalid_ref),.s_bresp(s_bresp_ref),.s_rresp(s_rresp_ref),.s_rdata(s_rdata_ref),.irq(irq_ref),
 .run(run_ref),.collector_rst_n(collector_rst_n_ref),.cfg_valid(cv_ref),.cfg_ready(cr),.cfg_applied(ca),.cfg_rejected(ce),.cfg_error(cerr),.cfg_period_us(cp_ref),.cfg_mask(cm_ref),
 .active_period_us(ap),.active_mask(am),.cfg_revision(rev),.cfg_apply_sequence(seq),.config_load_ppm(load),.busy(busy),
 .record_valid(rv),.record_data(data),.record_ready(rr_ref),.fifo_level(level),.dropped(drop),.accepted(ok),.errors(err),.ignored_rx(ignored),.bus_busy_events(be),.node_offline(offline),
 .observe_push(push),.observe_data(push_data),.observe_tasks(tasks),.observe_nodes(nodes));
integer projection_checks=0;
always @(posedge clk)begin #1;if(rst_n)begin
 projection_checks=projection_checks+1;
 if(dut.off_request_q !== (dut.write_fire && dut.aw_run && dut.w_run_clear && dut.reset_count==0))
  $fatal(1,"OFF projection not exact current state");
if(effective_run !== effective_run_ref)$fatal(1,"GP OFF full output effective_run");
if(stop_commit !== stop_commit_ref)$fatal(1,"GP OFF full output stop_commit");
if(local_reset !== local_reset_ref)$fatal(1,"GP OFF full output local_reset");
if(pending_config !== pending_config_ref)$fatal(1,"GP OFF full output pending_config");
if(applied_config !== applied_config_ref)$fatal(1,"GP OFF full output applied_config");
if(s_awready !== s_awready_ref)$fatal(1,"GP OFF full output s_awready");
if(s_wready !== s_wready_ref)$fatal(1,"GP OFF full output s_wready");
if(s_bvalid !== s_bvalid_ref)$fatal(1,"GP OFF full output s_bvalid");
if(s_arready !== s_arready_ref)$fatal(1,"GP OFF full output s_arready");
if(s_rvalid !== s_rvalid_ref)$fatal(1,"GP OFF full output s_rvalid");
if(s_bresp !== s_bresp_ref)$fatal(1,"GP OFF full output s_bresp");
if(s_rresp !== s_rresp_ref)$fatal(1,"GP OFF full output s_rresp");
if(s_rdata !== s_rdata_ref)$fatal(1,"GP OFF full output s_rdata");
if(irq !== irq_ref)$fatal(1,"GP OFF full output irq");
if(run !== run_ref)$fatal(1,"GP OFF full output run");
if(collector_rst_n !== collector_rst_n_ref)$fatal(1,"GP OFF full output collector_rst_n");
if(cv !== cv_ref)$fatal(1,"GP OFF full output cv");
if(cp !== cp_ref)$fatal(1,"GP OFF full output cp");
if(cm !== cm_ref)$fatal(1,"GP OFF full output cm");
if(rr !== rr_ref)$fatal(1,"GP OFF full output rr");
end end

endmodule
