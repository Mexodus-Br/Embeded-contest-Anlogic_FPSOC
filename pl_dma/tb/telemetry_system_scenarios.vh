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
  tw(`RT_REG_CANCEL,1);write_reg(DB+48,4,15,0,0);stall_hp1=0;polls=0;status_value=4;
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
