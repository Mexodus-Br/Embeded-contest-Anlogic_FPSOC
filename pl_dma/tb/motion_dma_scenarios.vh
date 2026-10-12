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
initial begin
 clk_100m=0;arst_n=0;gp_awid=0;gp_arid=0;gp_awlen=0;gp_arlen=0;gp_awsize=2;gp_arsize=2;gp_awburst=1;gp_arburst=1;gp_awlock=0;gp_arlock=0;gp_awcache=0;gp_arcache=0;gp_awprot=0;gp_arprot=0;gp_wlast=1;
 gp_awaddr=0;gp_awvalid=0;gp_wdata=0;gp_wstrb=0;gp_wvalid=0;gp_bready=0;gp_araddr=0;gp_arvalid=0;gp_rready=0;
 hp_rdata=0;hp_rvalid=0;hp_rlast=0;hp_rid=0;hp_bvalid=0;hp_bid=0;
 reset_design;
 // Probe and new profile occupy independent, fully decoded windows.
 read_reg(33'h080400000,0,status_value);check(status_value==1,"original GP VERSION");
 write_reg(33'h08040006c,32'h1234abcd,15,0,1);read_reg(33'h08040006c,0,status_value);check(status_value==32'h1234abcd,"probe scratch untouched");
 read_reg(MB,0,status_value);check(status_value==1,"separate motion VERSION");
 read_reg(MB+33'h100000000,3,status_value);write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_STOP,1,7,2,0);
 motion_recover;write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_MAINT,1,15,0,0);motion_command(`PLI_CMD_REBASE,15);motion_command(`PLI_CMD_ENABLE,15);
 motion_open;fill_motion(16,motion_session,0,1,10,1);issue_motion(16);await_dma;repeat(20)@(negedge clk_100m);
 check(motor_starts==0 && `MOTION.buffered_points==16,"DMA complete is only record reception");
 motion_command(`PLI_CMD_START,0);while(`MOTION.core_busy)@(negedge clk_100m);repeat(10)@(negedge clk_100m);
 check(motor_dones==16 && motor_pos[0+:64]==16 && motor_pulses[0+:64]==16,"real DMA batch END exact output");
 // Full cache: DMA cannot finish before START frees credit.
 motion_recover;motion_open;fill_motion(96,motion_session,0,1,2,17);issue_motion(96);
 repeat(11000)@(negedge clk_100m);check(loop_occupancy==73,"64 raw + 8 prepared + 1 planner");
 read_reg(BASE+4,0,status_value);check(!status_value[12],"DMA backpressured, no premature IOC");
 motion_command(`PLI_CMD_START,0);await_dma;while(`MOTION.core_busy)@(negedge clk_100m);repeat(10)@(negedge clk_100m);
 check(motor_pos[0+:64]==112 && motor_dones==112,"backpressured 96 records exact sequence");
 // Accepted validation envelope: 100us points, 32-point startup threshold,
 // a 2ms successful-supply gap, then a separate packet while running.
 motion_recover;motion_open;fill_motion(32,motion_session,0,0,100,113);issue_motion(32);await_dma;repeat(20)@(negedge clk_100m);
 check(`MOTION.buffered_points==32,"validation prebuffer threshold");motion_command(`PLI_CMD_START,0);
 repeat(200000)@(negedge clk_100m);
 fill_motion(16,motion_session,32,1,100,145);issue_motion(16);await_dma;
 while(`MOTION.core_busy)@(negedge clk_100m);repeat(10)@(negedge clk_100m);
 check(motor_pos[0+:64]==160 && motor_dones==160,"100us/2ms supply envelope no underrun");
 // A damaged real DMA record cannot enter the kernel.
 motion_recover;motion_open;fill_motion(1,motion_session,0,1,10,113);memory[4096+35]=memory[4096+35]^8'h80;issue_motion(1);await_dma;
 repeat(50)@(negedge clk_100m);check(!`MOTION.session_valid && `MOTION.buffered_points==0 && `MOTION.error_code==`PLI_ERR_BAD_RECORD,"real CRC failure closes session");
 // Cancel in-flight stream via GP; then controller reset, explicit recovery.
 // The HP BFM's read ownership survives DMA reset (not reset with PL).
 motion_recover;motion_open;fill_motion(32,motion_session,0,1,10,113);issue_motion(32);repeat(30)@(negedge clk_100m);
 motion_time=`MOTION.timestamp;motion_saved_pos=`MOTION.position;
 write_reg(MB+`PLI_MOTION_GP_MOTION_V1_REG_STOP,1,15,0,0);
 check(!`MOTION.link_ready,"STOP independent of pending DMA");
 reset_dma;repeat(100)@(negedge clk_100m);
 check(`MOTION.position==motion_saved_pos && `MOTION.timestamp>motion_time && !`MOTION.link_ready,"DMA-only reset preserves position/time, no autorecovery");
 monitor_packet=0;
 // BFM completed accepted DDR beats during reset; no hard-PS quiescence claim.
 while(rd_active || hp_rvalid)@(negedge clk_100m);
 motion_recover;motion_open;fill_motion(2,motion_session-1,0,1,10,500);issue_motion(2);await_dma;repeat(30)@(negedge clk_100m);
 check(`MOTION.buffered_points==0 && `MOTION.session_valid,"old DMA session discarded without cancelling new");
 fill_motion(2,motion_session,0,1,10,161);issue_motion(2);await_dma;motion_command(`PLI_CMD_START,0);
 while(`MOTION.core_busy)@(negedge clk_100m);repeat(10)@(negedge clk_100m);check(motor_pos[0+:64]==162,"new session explicit resumed from actual position");
 // The real DMA's failed HP read is independently observed by PL; it may
 // not become an implicit motion-domain reset or wait for the DMA handler.
 motion_recover;motion_open;fill_motion(16,motion_session,0,1,10,163);motion_saved_pos=`MOTION.position;
 hp_read_error=1;issue_motion(16);repeat(80)@(negedge clk_100m);hp_read_error=0;
 check(!`MOTION.link_ready && !`MOTION.session_valid && `MOTION.error_code==`PLI_ERR_DMA && `MOTION.position==motion_saved_pos,"real HP error cancels motion atomically");
 monitor_packet=0;reset_dma;while(rd_active || hp_rvalid)@(negedge clk_100m);motion_recover;
 check(read_beats>0 && write_beats==0 && max_occ==73,"real HP read path only and full cache");
 $display("PASS motion_dma_real_ip checks=%0d transfers=%0d read_beats=%0d starts=%0d dones=%0d max_occ=%0d",checks,transfers,read_beats,motor_starts,motor_dones,max_occ);$finish;
end
