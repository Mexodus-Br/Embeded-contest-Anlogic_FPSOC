`timescale 1ns/1ps
`include "generated/interface_defs.vh"
module tb_motion_service;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,dma_reset_released=1;reg [3:0] fault=0;
reg [32:0] s_awaddr=0,s_araddr=0;reg [31:0] s_wdata=0;reg [3:0] s_wstrb=15;
reg s_awvalid=0,s_wvalid=0,s_bready=0,s_arvalid=0,s_rready=0;
wire s_awready,s_wready,s_arready,s_bvalid,s_rvalid;wire [1:0] s_bresp,s_rresp;wire [31:0] s_rdata;
reg [63:0] stream_data=0;reg [7:0] stream_keep=255;reg stream_last=0,stream_valid=0;
wire stream_ready,irq;wire [3:0] step,dir,en,position_valid,pulse_event;
wire [255:0] position,pulses;wire running,paused,core_busy,session_valid;wire [63:0] session_id,slot_id;
wire [31:0] fifo_level,prepared_level,buffered_points;wire point_start,point_done,stopped,slot_event;
motion_service #(.FIFO_DEPTH(3),.PLAN_DEPTH(2),.START_MIN_POINTS(2),
 .STEP_HIGH_CYCLES({4{64'd3}}),.STEP_LOW_CYCLES({4{64'd2}}),.DIR_SETUP_CYCLES({4{64'd4}}),
 .DIR_HOLD_CYCLES({4{64'd7}}),.EN_SETUP_CYCLES({4{64'd5}}),.EN_DISABLE_CYCLES({4{64'd3}}),.MAX_STEP_HZ({4{64'd10000000}})) dut(
 .clk(clk),.rst_n(rst_n),.dma_reset_released(dma_reset_released),.dma_error(1'b0),.fault(fault),
 .s_awaddr(s_awaddr),.s_araddr(s_araddr),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_awvalid(s_awvalid),.s_wvalid(s_wvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_rready(s_rready),
 .s_awready(s_awready),.s_wready(s_wready),.s_arready(s_arready),.s_bvalid(s_bvalid),.s_rvalid(s_rvalid),.s_bresp(s_bresp),.s_rresp(s_rresp),.s_rdata(s_rdata),
 .stream_data(stream_data),.stream_keep(stream_keep),.stream_last(stream_last),.stream_valid(stream_valid),.stream_ready(stream_ready),.irq(irq),
 .step(step),.dir(dir),.en(en),.position_valid(position_valid),.position(position),.pulses(pulses),
 .running(running),.paused(paused),.core_busy(core_busy),.session_valid(session_valid),.session_id(session_id),
 .fifo_level(fifo_level),.prepared_level(prepared_level),.buffered_points(buffered_points),
 .point_start(point_start),.point_done(point_done),.stopped(stopped),.pulse_event(pulse_event),.slot_event(slot_event),.slot_id(slot_id));
localparam [32:0] BASE={1'b0,`PLI_MOTION_GP_MOTION_V1_BASE};
integer checks=0,cycle=0,starts=0,dones=0,aborts=0,backpressure=0,stales=0;
integer txid=0,genid=0,sess=0;
reg [3:0] old_step=0,old_dir=0;reg [255:0] ref_pos=0,ref_pulses=0;
reg blocked_record=0;reg [420:0] held_record;
integer rise[0:3],fall[0:3],change_dir[0:3],a;
task check;input ok;input [511:0] msg;begin checks=checks+1;if(!ok)begin $display("FAIL %0s cycle=%0d",msg,cycle);$fatal(1);end end endtask
always @(posedge clk)begin
 cycle=cycle+1;if(cycle>1000000)$fatal(1,"service watchdog");
 if(rst_n)begin
  if(blocked_record && !dut.cancel_transport)check(dut.rx_valid && {dut.rx_target,dut.rx_duration,dut.rx_session,dut.rx_sequence,dut.rx_end,dut.rx_mask}===held_record,"full record held stable under FIFO backpressure");
  blocked_record<=dut.rx_valid && !dut.rx_ready && !dut.cancel_transport;
  held_record<={dut.rx_target,dut.rx_duration,dut.rx_session,dut.rx_sequence,dut.rx_end,dut.rx_mask};
  if(dut.stop_kernel)begin #1;check((step & ~old_step)==0,"STOP/error detecting edge forbids STEP");end
 end else blocked_record<=0;
end
always @(negedge clk)begin
 if(!rst_n)begin old_step=0;old_dir=0;ref_pos=0;ref_pulses=0;for(a=0;a<4;a=a+1)begin rise[a]=-100;fall[a]=-100;change_dir[a]=-100;end end
 else begin
  for(a=0;a<4;a=a+1)begin
   if(dir[a]!=old_dir[a])begin check(cycle-rise[a]>=7,"DIR hold");change_dir[a]=cycle;end
   if(step[a] && !old_step[a])begin
    check(cycle-fall[a]>=2 && cycle-change_dir[a]>=4,"STEP L/DIR setup");rise[a]=cycle;
    ref_pos[a*64+:64]=$signed(ref_pos[a*64+:64])+(dir[a] ? 64'sd1:-64'sd1);
    ref_pulses[a*64+:64]=ref_pulses[a*64+:64]+1;
    check(slot_event,"real STEP is a corresponding master slot");
   end
   if(!step[a] && old_step[a])begin check(cycle-rise[a]==3,"full high pulse during cancellation");fall[a]=cycle;end
  end
  old_step=step;old_dir=dir;
  check(position===ref_pos,"actual signed position from pin edges");check(pulses===ref_pulses,"pulse totals same epoch as position");
  if(point_start)starts=starts+1;if(point_done)dones=dones+1;if(dut.cancelled)aborts=aborts+1;if(dut.stale)stales=stales+1;
  if(stream_valid && !stream_ready)backpressure=backpressure+1;
 end
end
task wr;input [31:0] off,val;input [1:0] resp;begin
 @(negedge clk);s_awaddr=BASE+off;s_wdata=val;s_awvalid=1;
 @(posedge clk);while(!s_awready)@(posedge clk);@(negedge clk);s_awvalid=0;
 // W delayed deliberately; standalone STOP must work after ownership pairing.
 repeat(2)@(negedge clk);s_wvalid=1;@(posedge clk);while(!s_wready)@(posedge clk);@(negedge clk);s_wvalid=0;
 while(!s_bvalid)@(negedge clk);repeat(2)begin check(s_bresp==resp && s_bvalid,"write response held");@(negedge clk);end
 s_bready=1;@(negedge clk);s_bready=0;
end endtask
task rd;input [31:0] off;output [31:0] val;begin
 @(negedge clk);s_araddr=BASE+off;s_arvalid=1;@(posedge clk);while(!s_arready)@(posedge clk);@(negedge clk);s_arvalid=0;
 while(!s_rvalid)@(negedge clk);val=s_rdata;repeat(2)begin check(s_rresp==0 && s_rvalid && s_rdata==val,"read response held");@(negedge clk);end
 s_rready=1;@(negedge clk);s_rready=0;
end endtask
task cmd;input [31:0] op,av;input good;reg [31:0] v;begin
 txid=txid+1;wr(`PLI_MOTION_GP_MOTION_V1_REG_OPCODE,op,0);wr(`PLI_MOTION_GP_MOTION_V1_REG_ARG,av,0);wr(`PLI_MOTION_GP_MOTION_V1_REG_TXN,txid,0);wr(`PLI_MOTION_GP_MOTION_V1_REG_SUBMIT,1,0);
 rd(`PLI_MOTION_GP_MOTION_V1_REG_ACK_STATUS,v);check(v[0] && v[1]==good,"command accepted result");
end endtask
task wait_idle;begin while(core_busy)@(negedge clk);repeat(5)@(negedge clk);end endtask
task recover;begin
 wait_idle;genid=genid+1;wr(`PLI_MOTION_GP_MOTION_V1_REG_RECOVER_GEN,genid,0);cmd(`PLI_CMD_LINK_RECOVER,0,1);check(dut.link_ready,"explicit recover only");cmd(`PLI_CMD_CLEAR_FAULT,0,1);
end endtask
task open_session;begin sess=sess+1;wr(`PLI_MOTION_GP_MOTION_V1_REG_SESSION_LO,sess,0);cmd(`PLI_CMD_OPEN_SESSION,0,1);check(session_valid,"OPEN accepted");end endtask
reg [575:0] rec;reg [31:0] cc;integer k,b,n;
function [31:0] crc_byte;input [31:0] c;input [7:0] v;integer j;reg [31:0] x;begin x=c^v;for(j=0;j<8;j=j+1)x=x[0] ? (x>>1)^32'hedb88320:x>>1;crc_byte=x;end endfunction
task make_record;input [63:0] sid;input [31:0] seq;input end_flag;input [63:0] duration;input signed [63:0] target;begin
 rec=0;rec[0+:32]=32'h32544f4d;rec[32+:16]=2;rec[48+:16]=72;rec[64+:64]=sid;rec[128+:32]=seq;rec[160]=end_flag;rec[176+:16]=15;rec[192+:64]=duration;
 rec[256+:64]=target;rec[320+:64]=-target;rec[384+:64]=target;rec[448+:64]=-target;
 cc=32'hffffffff;for(k=0;k<68;k=k+1)cc=crc_byte(cc,rec[k*8+:8]);rec[544+:32]=~cc;
end endtask
task send_beat;input integer index;input last;input [7:0] keep;begin
 @(negedge clk);stream_data=rec[index*64+:64];stream_last=last;stream_keep=keep;stream_valid=1;
 @(posedge clk);while(!stream_ready)@(posedge clk);@(negedge clk);stream_valid=0;
end endtask
task send_record;input final;begin for(b=0;b<9;b=b+1)send_beat(b,final && b==8,255);end endtask
task stop_gp;begin wr(`PLI_MOTION_GP_MOTION_V1_REG_STOP,1,0);wait_idle;check(!session_valid && buffered_points==0 && dut.partial_empty && !dut.link_ready,"STOP clears all ownership");end endtask
reg [31:0] v,v2;reg [63:0] saved_time;reg [255:0] saved_pos;integer before_start;
initial begin
 repeat(5)@(negedge clk);rst_n=1;repeat(12)@(negedge clk);
 check(!dut.link_ready && en==0 && position_valid==0,"boot closed disabled invalid");
 recover;wr(`PLI_MOTION_GP_MOTION_V1_REG_MAINT,1,0);cmd(`PLI_CMD_REBASE,15,1);cmd(`PLI_CMD_ENABLE,15,1);
 open_session;wr(`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,3,0);
 make_record(sess,0,0,10,3);send_record(0);make_record(sess,1,0,10,7);send_record(0);make_record(sess,2,1,10,2);send_record(1);
 while(!dut.start_ready)@(negedge clk);cmd(`PLI_CMD_START,0,1);
 wr(`PLI_MOTION_GP_MOTION_V1_REG_SNAP_REQ,1,0);
 for(n=0;n<4;n=n+1)begin
  rd(`PLI_MOTION_GP_MOTION_V1_REG_SNAP_16+n*16,v);rd(`PLI_MOTION_GP_MOTION_V1_REG_SNAP_18+n*16,v2);
  check(n%2==0 ? v==v2 : $signed(v)==-$signed(v2),"moving snapshot signed position/pulse atomicity");
 end
 cmd(`PLI_CMD_PAUSE,0,1);while(!paused && session_valid)@(negedge clk);check(paused,"boundary PAUSE");
 saved_pos=position;repeat(100)@(negedge clk);check(position==saved_pos && buffered_points>0,"PAUSE retains next point");
 wr(`PLI_MOTION_GP_MOTION_V1_REG_SNAP_REQ,1,0);rd(`PLI_MOTION_GP_MOTION_V1_REG_SNAP_ID,v);check(v==1,"duplicate snapshot stable");
 cmd(`PLI_CMD_RESUME,0,1);wait_idle;check(position[0+:64]==2 && position[64+:64]==-64'sd2 && dones==3 && !session_valid,"END precise four-axis trajectory");
 check(pulses[0+:64]==12 && pulses[64+:64]==12,"absolute targets exact independent pulse counts");
 // Distinct Ni and mixed directions, including a zero-delta axis. The
 // independent pin monitor checks common slot tagging and each signed sum.
 recover;open_session;wr(`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,2,0);
 make_record(sess,0,0,10,7);rec[320+:64]=-64'sd9;rec[384+:64]=2;rec[448+:64]=-64'sd4;
 cc=32'hffffffff;for(k=0;k<68;k=k+1)cc=crc_byte(cc,rec[k*8+:8]);rec[544+:32]=~cc;send_record(0);
 make_record(sess,1,1,10,3);rec[384+:64]=-64'sd1;rec[448+:64]=2;
 cc=32'hffffffff;for(k=0;k<68;k=k+1)cc=crc_byte(cc,rec[k*8+:8]);rec[544+:32]=~cc;send_record(1);
 while(!dut.start_ready)@(negedge clk);cmd(`PLI_CMD_START,0,1);wait_idle;
 check(position=={64'sd2,-64'sd1,-64'sd3,64'sd3} && pulses=={64'd20,64'd15,64'd25,64'd21},"mixed four-axis exact counts and direction");
 // A complete stale record never mutates acceptance of the new session.
 recover;open_session;wr(`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,2,0);
 make_record(sess-1,0,0,20,20);send_record(0);make_record(sess,0,1,20,5);send_record(1);repeat(100)@(negedge clk);
 check(stales==1 && buffered_points==1 && dut.accepted_sequence==0,"old session isolated");stop_gp;
 // CRC, KEEP, missing/early TLAST, version, length, flags and zero duration.
 for(n=0;n<12;n=n+1)begin
  recover;open_session;wr(`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,1,0);make_record(sess,0,1,10,10);
  case(n)
   0:rec[280]=~rec[280];1:rec[32+:16]=1;2:rec[48+:16]=80;3:rec[161]=1;4:rec[192+:64]=0;
   8:rec[512]=1;9:rec[176+:16]=16;10:rec[64+:64]=0;11:rec[0+:32]=0;
  endcase
  if((n>0 && n<5) || n>=8)begin cc=32'hffffffff;for(k=0;k<68;k=k+1)cc=crc_byte(cc,rec[k*8+:8]);rec[544+:32]=~cc;end
  if(n<5 || n>=8)begin send_record(1);repeat(20)@(negedge clk);end
  else if(n==5)send_beat(0,0,127);
  else if(n==6)send_beat(0,1,255);
  else begin for(b=0;b<9;b=b+1)send_beat(b,0,255);end
  wait_idle;check(!dut.link_ready && !session_valid && buffered_points==0 && dut.error_code==`PLI_ERR_BAD_RECORD,"malformed record cancels no partial commit");
 end
 // Half-record cancellation at every beat; DMA-only reset keeps position/time.
 for(n=0;n<9;n=n+1)begin
  recover;open_session;wr(`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,1,0);make_record(sess,0,1,10,5);
  for(b=0;b<n;b=b+1)send_beat(b,0,255);
  saved_time=dut.timestamp;saved_pos=position;
  @(negedge clk);dma_reset_released=0;repeat(6)@(negedge clk);dma_reset_released=1;wait_idle;repeat(100)@(negedge clk);
  check(position==saved_pos && dut.timestamp>saved_time && !dut.link_ready && dut.partial_empty,"DMA reset maintains position/time and closes ingress");
 end
 // Fill the raw/plan caches, then release by START rather than waiting for IOC.
 recover;open_session;wr(`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,16,0);before_start=backpressure;
 fork
  begin for(n=0;n<16;n=n+1)begin make_record(sess,n,n==15,10,n+6);send_record(n==15);end end
  begin repeat(2200)@(negedge clk);check(buffered_points==6,"full raw/plan/planner capacity");cmd(`PLI_CMD_START,0,1);end
 join
 wait_idle;check(backpressure>before_start && position[0+:64]==21,"FIFO held then drained without lost records");
 // STOP at every execution phase offset; GP also cancels a waiting PAUSE.
 for(n=0;n<60;n=n+1)begin
  recover;open_session;wr(`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,1,0);make_record(sess,0,1,10,position[0+:64]+20);send_record(1);
  while(!dut.start_ready)@(negedge clk);cmd(`PLI_CMD_START,0,1);repeat(n)@(negedge clk);stop_gp;
 end
 // Ordinary fault has the same detecting-edge priority; no automatic EN.
 for(n=0;n<30;n=n+1)begin
  recover;open_session;wr(`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,1,0);make_record(sess,0,1,10,position[0+:64]+20);send_record(1);
  while(!dut.start_ready)@(negedge clk);cmd(`PLI_CMD_START,0,1);repeat(n)@(negedge clk);
  @(negedge clk);fault=1;repeat(20)@(negedge clk);fault=0;wait_idle;
  check(!session_valid && buffered_points==0 && en==15 && dut.error_code==`PLI_ERR_INTERLOCK,"fault drains and preserves EN");
 end
 // A long PAUSE transaction cannot lock out STOP or independent SNAP_REQ.
 recover;open_session;wr(`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,1,0);make_record(sess,0,0,30,position[0+:64]+20);send_record(1);
 // Non-END short trajectory needs the threshold: add the second point.
 while(!dut.rx_arm_ready)@(negedge clk);
 wr(`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,1,0);make_record(sess,1,0,30,position[0+:64]+30);send_record(1);
 while(!dut.start_ready)@(negedge clk);cmd(`PLI_CMD_START,0,1);cmd(`PLI_CMD_PAUSE,0,1);
 check(dut.command_busy,"PAUSE awaiting boundary holds mailbox");wr(`PLI_MOTION_GP_MOTION_V1_REG_SNAP_REQ,2,0);stop_gp;
 check(!dut.command_busy && dut.ack_completed && dut.ack_error==`PLI_ERR_LINK_RESET && dut.snap_id==2,"STOP cancels busy PAUSE, snapshot independent");
 recover;open_session;wr(`PLI_MOTION_GP_MOTION_V1_REG_PACKET_ARM,2,0);make_record(sess,0,0,2,position[0+:64]+3);send_record(0);
 make_record(sess,1,0,2,position[0+:64]+6);send_record(1);
 while(!dut.start_ready)@(negedge clk);cmd(`PLI_CMD_START,0,1);wait_idle;
 check(dut.error_code==`PLI_ERR_UNDERRUN && !session_valid && buffered_points==0,"underflow closes and flushes");
 $display("PASS motion_service checks=%0d starts=%0d dones=%0d aborts=%0d stale=%0d backpressure=%0d",checks,starts,dones,aborts,stales,backpressure);$finish;
end
endmodule
