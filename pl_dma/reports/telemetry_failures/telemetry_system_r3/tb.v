`timescale 1ns/1ps
module tb_telemetry_system;
`include "generated/interface_defs.vh"
`include "telem_defs.vh"
`include "gp_defs.vh"
`include "dut_bindings.vh"
wire [31:0] loop_occupancy=dut.core.fabric.dma_core.loop_occupancy;
always #5 clk_100m=~clk_100m;
reg [7:0] memory[0:262143];
integer cycle=0,checks=0,transfers=0,streams=0,lasts=0;
integer read_beats=0,write_beats=0,stream_bytes=0,stream_expected=0;
integer max_occ=0;reg stall_all=0,stall_writes=0,monitor_packet=0;
reg rd_active=0,wr_active=0,b_pending=0;integer b_delay=0;
reg [32:0] rd_addr,wr_addr;reg [4:0] rd_left,wr_left;
reg [5:0] wr_id;integer j;
assign hp_arready=control_rst_n && !rd_active && !hp_rvalid && !stall_all && cycle%5!=0;
assign hp_awready=control_rst_n && !wr_active && !b_pending && !hp_bvalid && !stall_all && !stall_writes && cycle%7!=0;
assign hp_wready=control_rst_n && wr_active && !stall_all && !stall_writes && cycle%4!=0;
assign hp_bresp=0;assign hp_rresp=0;
function [63:0] word_at;input [32:0] a;integer k;
 begin for(k=0;k<8;k=k+1) word_at[8*k+:8]=memory[a+k];end
endfunction
task check;input condition;input [255:0] message;
 begin checks=checks+1;if(!condition) begin $display("FAIL %0s cycle=%0d",message,cycle);$fatal(1);end end
endtask
always @(posedge clk_100m) begin
 cycle<=cycle+1;
 if(cycle>20000000) $fatal(1,"watchdog");
 if(!control_rst_n) begin rd_active<=0;wr_active<=0;b_pending<=0;b_delay<=0;hp_rvalid<=0;hp_bvalid<=0;hp_rlast<=0;end
 else begin
  if(hp_arvalid && hp_arready) begin
   check(hp_araddr<262136 && hp_araddr[2:0]==0,"HP read address");
   check(hp_arlen<=15 && hp_arsize==3 && hp_arburst==1 && hp_arid==0,"HP read geometry");
   check(hp_arqos==0,"HP read QoS");
   check(dut.core.fabric.dma_core.bridge_arsize[2]==0 && dut.core.fabric.dma_core.bridge_arlock==0,"HP read no truncation");
   rd_active<=1;rd_addr<=hp_araddr;rd_left<=hp_arlen+1'b1;hp_rid<=hp_arid;
  end
  if(rd_active && !hp_rvalid && !stall_all && cycle%3!=0) begin
   hp_rdata<=word_at(rd_addr);hp_rvalid<=1;hp_rlast<=rd_left==1;
  end
  if(hp_rvalid && hp_rready) begin
   read_beats=read_beats+1;hp_rvalid<=0;rd_addr<=rd_addr+8;rd_left<=rd_left-1'b1;
   if(rd_left==1) rd_active<=0;
  end
  if(hp_awvalid && hp_awready) begin
   check(hp_awaddr<262136 && hp_awaddr[2:0]==0,"HP write address");
   check(hp_awlen<=15 && hp_awsize==3 && hp_awburst==1 && hp_awid==0,"HP write geometry");
   check(hp_awqos==0,"HP write QoS");
   check(dut.core.fabric.dma_core.bridge_awsize[2]==0 && dut.core.fabric.dma_core.bridge_awlock==0,"HP write no truncation");
   wr_active<=1;wr_addr<=hp_awaddr;wr_left<=hp_awlen+1'b1;wr_id<=hp_awid;
  end
  if(hp_wvalid && hp_wready) begin
   check(hp_wlast==(wr_left==1),"HP WLAST burst");write_beats=write_beats+1;
   for(j=0;j<8;j=j+1) if(hp_wstrb[j]) memory[wr_addr+j]<=hp_wdata[8*j+:8];
   wr_addr<=wr_addr+8;wr_left<=wr_left-1'b1;
   if(wr_left==1) begin wr_active<=0;b_pending<=1;b_delay<=5;end
  end
  // BVALID must disappear immediately after handshake, never resend B.
  if(b_pending && !hp_bvalid) begin
   if(b_delay!=0) b_delay<=b_delay-1;
   else begin hp_bvalid<=1;hp_bid<=wr_id;end
  end
  if(hp_bvalid && hp_bready) begin hp_bvalid<=0;b_pending<=0;end
  if(loop_occupancy>max_occ) max_occ=loop_occupancy;
  if(monitor_packet && dut.core.fabric.dma_core.d_m_axis_mm2s_tvalid && dut.core.fabric.dma_core.d_m_axis_mm2s_tready) begin
   streams=streams+1;
   for(j=0;j<8;j=j+1) if(dut.core.fabric.dma_core.d_m_axis_mm2s_tkeep[j]) stream_bytes=stream_bytes+1;
   if(dut.core.fabric.dma_core.d_m_axis_mm2s_tlast) begin
    lasts=lasts+1;check(stream_bytes==stream_expected,"MM2S byte count/TLAST");
   end else check(dut.core.fabric.dma_core.d_m_axis_mm2s_tkeep==255,"full nonfinal TKEEP");
  end
 end
end
// AXI payload stability under deterministic memory backpressure.
reg rb=0,wb=0,ab=0,arb=0;reg [64:0] old_r;reg [72:0] old_w;
reg [42:0] old_aw,old_ar;
always @(posedge clk_100m) begin
 if(!control_rst_n) begin rb<=0;wb<=0;ab<=0;arb<=0;end
 else begin
  if(rb) check(hp_rvalid && {hp_rlast,hp_rdata}===old_r,"R blocked stable");
  if(wb) check(hp_wvalid && {hp_wlast,hp_wstrb,hp_wdata}===old_w,"W blocked stable");
  if(ab) check(hp_awvalid && {hp_awaddr,hp_awlen,hp_awsize,hp_awburst}===old_aw,"AW blocked stable");
  if(arb) check(hp_arvalid && {hp_araddr,hp_arlen,hp_arsize,hp_arburst}===old_ar,"AR blocked stable");
  rb<=hp_rvalid&&!hp_rready;wb<=hp_wvalid&&!hp_wready;ab<=hp_awvalid&&!hp_awready;arb<=hp_arvalid&&!hp_arready;
  old_r<={hp_rlast,hp_rdata};old_w<={hp_wlast,hp_wstrb,hp_wdata};
  old_aw<={hp_awaddr,hp_awlen,hp_awsize,hp_awburst};old_ar<={hp_araddr,hp_arlen,hp_arsize,hp_arburst};
 end
end
task write_reg;input [32:0] addr;input [31:0] value;input [3:0] strobe;input [1:0] response;input integer order;
 begin
  fork
   begin repeat(order==1 ? 3 : 0) @(negedge clk_100m);gp_awaddr=addr;gp_awvalid=1;
    @(posedge clk_100m);while(!gp_awready) @(posedge clk_100m);@(negedge clk_100m);gp_awvalid=0;end
   begin repeat(order==2 ? 3 : 0) @(negedge clk_100m);gp_wdata=value;gp_wstrb=strobe;gp_wvalid=1;
    @(posedge clk_100m);while(!gp_wready) @(posedge clk_100m);@(negedge clk_100m);gp_wvalid=0;end
  join
  while(!gp_bvalid) @(negedge clk_100m);
  repeat(3) begin check(gp_bvalid && gp_bresp==response,"Lite B hold/response");@(negedge clk_100m);end
  gp_bready=1;@(negedge clk_100m);gp_bready=0;
 end
endtask
task read_reg;input [32:0] addr;input [1:0] response;output [31:0] value;
 begin
  @(negedge clk_100m);gp_araddr=addr;gp_arvalid=1;
  @(posedge clk_100m);while(!gp_arready) @(posedge clk_100m);@(negedge clk_100m);gp_arvalid=0;
  while(!gp_rvalid) @(negedge clk_100m);value=gp_rdata;
  repeat(2) begin check(gp_rvalid && gp_rresp==response && gp_rdata===value,"Lite R hold/response");@(negedge clk_100m);end
  gp_rready=1;@(negedge clk_100m);gp_rready=0;
 end
endtask
localparam [32:0] BASE=33'h080500000;
reg [31:0] status_value;integer n,pattern,k,polls,initial_lasts;
task reset_design;
 begin
  @(negedge clk_100m);arst_n=0;monitor_packet=0;
  repeat(6) @(negedge clk_100m);arst_n=1;repeat(25) @(negedge clk_100m);
  check(loop_occupancy==0,"reset FIFO empty");
 end
endtask
task reset_dma;
 begin
  write_reg(BASE,4,15,0,0);write_reg(BASE+48,4,15,0,1);
  polls=0;status_value=4;
  while(status_value[2] && polls<1000) begin read_reg(BASE,0,status_value);polls=polls+1;end
  check(!status_value[2],"DMA reset completes");repeat(15) @(negedge clk_100m);
  check(loop_occupancy==0,"DMA primary reset flush");
 end
endtask
// Included by the generated real-PS-boundary bench with the existing HP BFM.
`define MOTION dut.core.fabric.dma_core.motion
localparam [32:0] MB={1'b0,`PLI_MOTION_GP_MOTION_V1_BASE};
integer motion_txn=0,motion_gen=0,motion_session=0,motor_starts=0,motor_dones=0;
reg [3:0] old_step=0;reg [255:0] motor_pos=0,motor_pulses=0;integer axis;
always @(negedge clk_100m)if(control_rst_n)begin
 for(axis=0;axis<4;axis=axis+1)if(`MOTION.step[axis] && !old_step[axis])begin
  motor_pos[axis*64+:64]=$signed(motor_pos[axis*64+:64])+(`MOTION.dir[axis] ? 64'sd1:-64'sd1);
  motor_pulses[axis*64+:64]=motor_pulses[axis*64+:64]+1;
  check(`MOTION.slot_event,"corresponding STEP is in common slot");
 end
 old_step=`MOTION.step;
 check(`MOTION.position===motor_pos,"real DMA motion exact position");
 check(`MOTION.pulses===motor_pulses,"real DMA totals aligned");
 check(`MOTION.timestamp===dut.core.fabric.registers.timestamp,"motion snapshot tick is probe epoch/timebase");
 check(!dut.core.fabric.dma_core.d_s_axis_s2mm_tvalid && write_beats==0,"S2MM is not loopback or required");
 if(`MOTION.point_start)motor_starts=motor_starts+1;if(`MOTION.point_done)motor_dones=motor_dones+1;
end
task motion_command;input [31:0] op,av;begin
 motion_txn=motion_txn+1;
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_OPCODE,op,15,0,1);
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_ARG,av,15,0,2);
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_TXN,motion_txn,15,0,0);
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_SUBMIT,1,15,0,1);
 read_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_ACK_ERROR,0,status_value);check(status_value==0,"motion GP command ACK");
end endtask
task motion_recover;begin
 while(`MOTION.core_busy)@(negedge clk_100m);
 motion_gen=motion_gen+1;write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_RECOVER_GEN,motion_gen,15,0,0);
 motion_command(`PLI_CMD_LINK_RECOVER,0);motion_command(`PLI_CMD_CLEAR_FAULT,0);
 check(`MOTION.link_ready,"GP explicit recovery");
end endtask
task motion_open;begin
 motion_session=motion_session+1;write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_SESSION_LO,motion_session,15,0,0);
 motion_command(`PLI_CMD_OPEN_SESSION,0);
end endtask
function [31:0] motion_crc;input [31:0] c;input [7:0] v;integer j;reg [31:0] x;begin x=c^v;for(j=0;j<8;j=j+1)x=x[0] ? (x>>1)^32'hedb88320:x>>1;motion_crc=x;end endfunction
task fill_motion;input integer count,sid,seq_first;input end_flag;input [63:0] duration;input signed [63:0] first_target;
 reg [575:0] r;reg [31:0] c;integer x,y;reg signed [63:0] target;
 begin
 for(x=0;x<count;x=x+1)begin
  target=first_target+x;r=0;r[0+:32]=32'h32544f4d;r[32+:16]=2;r[48+:16]=72;r[64+:64]=sid;r[128+:32]=seq_first+x;
  r[160]=end_flag && x==count-1;r[176+:16]=15;r[192+:64]=duration;
  r[256+:64]=target;r[320+:64]=-target;r[384+:64]=target;r[448+:64]=-target;
  c=32'hffffffff;for(y=0;y<68;y=y+1)c=motion_crc(c,r[y*8+:8]);r[544+:32]=~c;
  for(y=0;y<72;y=y+1)memory[4096+x*72+y]=r[y*8+:8];
 end
 end
endtask
task issue_motion;input integer count;begin
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,count,15,0,0);
 write_reg(BASE+4,32'h7000,15,0,0);write_reg(BASE,32'h5001,15,0,0);write_reg(BASE+24,4096,15,0,0);
 stream_bytes=0;stream_expected=count*72;initial_lasts=lasts;monitor_packet=1;
 write_reg(BASE+40,count*72,15,0,0);
end endtask
task await_dma;begin
 polls=0;status_value=0;while(!status_value[12] && polls<60000)begin read_reg(BASE+4,0,status_value);polls=polls+1;end
 check(status_value[12] && (status_value&32'h770)==0,"MM2S IOC with no error");
 // The vendor may publish IOC after fetching into its own buffers, before
 // the application consumes the final stream beat. Wait separately.
 polls=0;while(lasts==initial_lasts && polls<60000)begin @(negedge clk_100m);polls=polls+1;end
 check(lasts==initial_lasts+1 && stream_bytes==stream_expected,"batch packet bytes/TLAST");
 check(f2p_irq[1] && !f2p_irq[2],"DMA IRQ independent of idle S2MM");
 monitor_packet=0;transfers=transfers+1;
end endtask
reg [63:0] motion_time;reg [255:0] motion_saved_pos;
reg stall_hp1=0,hp1_active=0,hp1_pending=0;integer hp1_left=0,hp1_delay=0,hp1_writes=0;reg [32:0] hp1_address;reg [5:0] hp1_id;
assign hp1_arready=control_rst_n;assign hp1_rdata=0;assign hp1_rid=0;assign hp1_rlast=0;assign hp1_rvalid=0;assign hp1_rresp=0;
assign hp1_awready=control_rst_n && !hp1_active && !hp1_pending && !hp1_bvalid && !stall_hp1;
assign hp1_wready=control_rst_n && hp1_active && !stall_hp1 && cycle%3!=0;assign hp1_bresp=0;
integer h;
always @(posedge clk_100m) begin
 if(!control_rst_n) begin hp1_active<=0;hp1_pending<=0;hp1_bvalid<=0;end
 else begin
  check(!hp1_arvalid,"independent S2MM no HP1 read");
  if(hp1_awvalid && hp1_awready) begin check(hp1_awsize==3 && hp1_awlen<16 && hp1_awaddr>=196608 && hp1_awaddr<262144,"HP1 write geometry");hp1_active<=1;hp1_left<=hp1_awlen+1;hp1_address<=hp1_awaddr;hp1_id<=hp1_awid;end
  if(hp1_wvalid && hp1_wready) begin
   check(hp1_wlast==(hp1_left==1),"HP1 WLAST");hp1_writes=hp1_writes+1;
   for(h=0;h<8;h=h+1) if(hp1_wstrb[h]) memory[hp1_address+h]<=hp1_wdata[h*8+:8];
   hp1_address<=hp1_address+8;hp1_left<=hp1_left-1;
   if(hp1_left==1) begin hp1_active<=0;hp1_pending<=1;hp1_delay<=5;end
  end
  if(hp1_pending && !hp1_bvalid) begin if(hp1_delay>0) hp1_delay<=hp1_delay-1;else begin hp1_bvalid<=1;hp1_bid<=hp1_id;end end
  if(hp1_bvalid && hp1_bready) begin hp1_bvalid<=0;hp1_pending<=0;end
 end
end
always @(negedge clk_100m) if(control_rst_n) begin
 check(motion_step===ref_motion_step && motion_dir===ref_motion_dir && motion_en===ref_motion_en,"STEP/DIR/EN differential against unchanged motion controller");
 check(hp_arvalid===ref_hp_arvalid && hp_rready===ref_hp_rready,"HP0 controller unaffected");
end
localparam [32:0] CB=33'h080800000,DB=33'h080900000,RB=33'h080700000;
reg [7:0] ua,uq,uc,ub,sum;integer uj,ulen,urise=0;
always @(posedge rs485_de) urise=cycle;
task uart_ticks;input integer n;begin repeat(n) @(negedge clk_100m);end endtask
task uart_read;output [7:0] b;integer z;begin uart_ticks(1302);for(z=0;z<8;z=z+1) begin b[z]=rs485_tx;uart_ticks(868);end check(rs485_tx,"UART stop");uart_ticks(434);end endtask
task uart_send;input [7:0] b;integer z;begin check(!rs485_de,"half duplex");rs485_rx=0;uart_ticks(868);for(z=0;z<8;z=z+1) begin rs485_rx=b[z];uart_ticks(868);end rs485_rx=1;uart_ticks(868);end endtask
initial forever begin
 @(negedge rs485_tx);check(cycle-urise>=1000,"DE pre");uart_read(ua);@(negedge rs485_tx);uart_read(uq);@(negedge rs485_tx);uart_read(uc);
 check(uc==((ua+uq)&255) && uq==8'h3a && ua>=8'he0 && ua<=8'he2,"request checksum/address/whitelist");
 @(negedge rs485_de);uart_ticks(2000);uart_send(ua);uart_send(8'd2);uart_send(ua+8'd2);
end
reg [255:0] raw_events[0:255];reg [31:0] event_revisions[0:255];integer event_count=0;
always @(posedge clk_100m) if(dut.core.fabric.completed_valid) begin
 raw_events[event_count]=dut.core.fabric.completed_raw;event_revisions[event_count]=dut.core.fabric.revision;event_count=event_count+1;
end
task tw;input [31:0] off,value;begin write_reg(CB+off,value,15,0,0);end endtask
task ready_packet;output [31:0] id,bytes;
 begin
  status_value=0;polls=0;
  while(!(status_value&`RT_STATUS_PACKET_READY) && polls<400000) begin read_reg(CB+`RT_REG_STATUS,0,status_value);polls=polls+1;end
  if(!(status_value&`RT_STATUS_PACKET_READY)) $display("READY_DEBUG status=%h events=%0d time=%0d fifo=%0d",status_value,event_count,dut.core.fabric.system_time_us,dut.core.fabric.telemetry.fifo_level);
  check((status_value&`RT_STATUS_PACKET_READY)!=0,"bounded flush packet ready");read_reg(CB+`RT_REG_PACKET_ID,0,id);read_reg(CB+`RT_REG_PACKET_BYTES,0,bytes);
 end
endtask
task issue_rx;input [31:0] id,gen,bytes;
 begin
  write_reg(DB+48,32'h5001,15,0,0);write_reg(DB+72,196608,15,0,0);write_reg(DB+88,bytes,15,0,0);
  tw(`RT_REG_ARM_ID,id);tw(`RT_REG_ARM_GEN,gen);tw(`RT_REG_ARM_BYTES,bytes);tw(`RT_REG_ARM,1);
 end
endtask
task reset_telemetry;
 begin
  tw(`RT_REG_CANCEL,1);write_reg(DB+48,4,15,0,0);polls=0;status_value=4;
  while(status_value[2] && polls<1000) begin read_reg(DB+48,0,status_value);polls=polls+1;end
  check(!status_value[2],"new controller reset complete");
  stall_hp1=0;while(!dut.core.fabric.hp1_idle) @(negedge clk_100m);
  repeat(30) @(negedge clk_100m);
 end
endtask
reg [31:0] packet,bytes,capture_id;reg [511:0] decoded_frame;reg [31:0] ccrc;integer xx,yy,serial;
initial begin
 clk_100m=0;arst_n=0;rs485_rx=1;gp_awid=0;gp_arid=0;gp_awlen=0;gp_arlen=0;gp_awsize=2;gp_arsize=2;gp_awburst=1;gp_arburst=1;gp_awlock=0;gp_arlock=0;gp_awcache=0;gp_arcache=0;gp_awprot=0;gp_arprot=0;gp_wlast=1;
 gp_awaddr=0;gp_awvalid=0;gp_wdata=0;gp_wstrb=0;gp_wvalid=0;gp_bready=0;gp_araddr=0;gp_arvalid=0;gp_rready=0;
 hp_rdata=0;hp_rvalid=0;hp_rlast=0;hp_rid=0;hp_bvalid=0;hp_bid=0;hp1_bvalid=0;hp1_bid=0;
 reset_design;
 motion_recover;write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_MAINT,1,15,0,0);motion_command(`PLI_CMD_REBASE,15);motion_command(`PLI_CMD_ENABLE,15);
 motion_open;fill_motion(32,motion_session,0,1,1000,1);issue_motion(32);await_dma;motion_command(`PLI_CMD_START,0);
 tw(`RT_REG_RECOVER_GEN,1);tw(`RT_REG_RECOVER,1);tw(`RT_REG_ENABLE,1);
 for(xx=0;xx<5;xx=xx+1) write_reg(RB+`RG_REG_SHADOW_PERIOD0+xx*4,0,15,0,0);
 write_reg(RB+`RG_REG_SHADOW_PERIOD3,125000,15,0,0);write_reg(RB+`RG_REG_SHADOW_MASK,8,15,0,0);write_reg(RB+`RG_REG_TXN_ID,1,15,0,0);write_reg(RB+`RG_REG_CFG_SUBMIT,1,15,0,0);
 status_value=3;while(status_value==3) read_reg(RB+`RG_REG_CFG_STATE,0,status_value);check(status_value==5,"real collector config applied");write_reg(RB+`RG_REG_RUN,1,15,0,0);
 ready_packet(packet,bytes);check(bytes==64,"low rate flush produces one-record short batch");
 // Old GP owns a different FIFO: capture its record while DMA is independent.
 write_reg(RB+`RG_REG_CAPTURE,1,15,0,0);read_reg(RB+`RG_REG_CAPTURE_ID,0,capture_id);
 for(xx=0;xx<8;xx=xx+1) read_reg(RB+`RG_REG_WORD0+xx*4,0,status_value);
 issue_rx(packet,1,bytes);status_value=0;while(!status_value[12]) read_reg(DB+52,0,status_value);
 check((status_value&32'h770)==0,"real HP1 IOC without error");read_reg(DB+88,0,status_value);check(status_value==bytes,"actual received length");
 for(xx=0;xx<bytes/64;xx=xx+1) begin
  for(yy=0;yy<64;yy=yy+1) decoded_frame[yy*8+:8]=memory[196608+xx*64+yy];
  ccrc=32'hffffffff;for(yy=0;yy<60;yy=yy+1) ccrc=motion_crc(ccrc,decoded_frame[yy*8+:8]);
  serial=decoded_frame[223:160];check(decoded_frame[511:480]==~ccrc && decoded_frame[31:0]==`RT_RECORD_MAGIC,"actual DDR CRC/header");
  check(decoded_frame[159:128]==1 && decoded_frame[127:96]==event_revisions[serial] && decoded_frame[479:224]===raw_events[serial],"actual DDR immutable source metadata/raw");
 end
 write_reg(RB+`RG_REG_CONSUME_ID,capture_id,15,0,0);tw(`RT_REG_COMPLETE_ID,packet);tw(`RT_REG_COMPLETE_GEN,1);tw(`RT_REG_COMPLETE_RESULT,0);tw(`RT_REG_COMPLETE,1);
 // A second RX packet can reach STREAM_DONE before DDR when HP1 stalls.
 ready_packet(packet,bytes);stall_hp1=1;issue_rx(packet,1,bytes);repeat(2000) @(negedge clk_100m);
 check(`MOTION.session_valid && `MOTION.running,"motion still executing during HP1 backpressure");
 reset_telemetry;check(`MOTION.session_valid && `MOTION.link_ready,"HP1/controller reset does not cancel HP0 motion");
 tw(`RT_REG_RECOVER_GEN,2);tw(`RT_REG_RECOVER,1);tw(`RT_REG_ENABLE,1);
 tw(`RT_REG_SNAP_REQ_ID,1);tw(`RT_REG_SNAP_SUBMIT,1);read_reg(CB+`RT_ROW_BASE+3*`RT_ROW_STRIDE+`RT_ROW_FLAGS,0,status_value);check(status_value&1,"cache preserved across DMA reset");
 while(`MOTION.core_busy) @(negedge clk_100m);check(motor_dones==32 && motor_pos[63:0]==32,"complete STEP reference after isolated reset");
 check(event_count>=2 && hp1_writes>0 && read_beats>0,"both physical HP paths exercised");
 $display("PASS telemetry_system_real checks=%0d events=%0d hp0_reads=%0d hp1_writes=%0d STEP_dones=%0d",checks,event_count,read_beats,hp1_writes,motor_dones);$finish;
end

endmodule
